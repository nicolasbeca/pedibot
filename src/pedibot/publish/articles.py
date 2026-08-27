"""Generate a grounded article for a topic from the index, verify citations, write Markdown.

Output: web/content/<lang>/<slug>.md with YAML frontmatter (Astro content collection later) and
publish/queue/x/<slug>.txt with a hand-postable social text (no X API — operator decision).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pedibot.bot.answer import verify
from pedibot.bot.llm import LLMProvider, LLMResult
from pedibot.bot.retrieval import detect_lang
from pedibot.index.store import Hit, Index
from pedibot.ingest.pipeline import slug as make_slug

PROMPTS_DIR = Path(__file__).parent / "prompts"
_CIT = re.compile(r"\[(\d{1,2})\]")

# Topic → (leaflet doc_ids to draw from, search query). Curated so every article is anchored on
# parent-facing leaflets first; clinical references only add depth.
TOPIC_PLAN: dict[str, dict[str, object]] = {
    "fiebre": {
        "docs": ["seup_fiebre", "seup_acudir_urgencias"],
        "query": "fiebre niño qué hacer cuándo consultar",
    },
    "laringitis": {"docs": ["seup_laringitis"], "query": "laringitis crup tos perruna"},
    "bronquiolitis": {
        "docs": ["seup_bronquiolitis"],
        "query": "bronquiolitis lactante dificultad respiratoria",
    },
    "gastroenteritis": {
        "docs": ["seup_gastroenteritis", "seup_vomitos"],
        "query": "gastroenteritis diarrea vómitos rehidratación",
    },
    "vomitos": {"docs": ["seup_vomitos"], "query": "vómitos niño qué hacer"},
    "otitis": {"docs": ["seup_otitis"], "query": "otitis media dolor de oído"},
    "catarro": {"docs": ["seup_catarro"], "query": "catarro vías altas mocos tos"},
    "traumatismo_craneal": {
        "docs": ["seup_tce"],
        "query": "traumatismo craneal golpe cabeza vigilar",
    },
    "convulsion_febril": {
        "docs": ["seup_convulsion_febril"],
        "query": "convulsión febril qué hacer",
    },
    "intoxicaciones": {
        "docs": ["seup_intoxicaciones", "seup_toxicos_8_no"],
        "query": "intoxicación ingesta tóxico qué no hacer",
    },
    "anafilaxia": {
        "docs": ["seup_anafilaxia"],
        "query": "anafilaxia reacción alérgica grave adrenalina",
    },
    "urticaria": {"docs": ["seup_urticaria"], "query": "urticaria ronchas habones"},
    "dolor_abdominal": {
        "docs": ["seup_dolor_abdominal"],
        "query": "dolor abdominal barriga cuándo consultar",
    },
    "estrenimiento": {"docs": ["seup_estrenimiento"], "query": "estreñimiento niño"},
    "colico_lactante": {"docs": ["seup_colico"], "query": "cólico del lactante llanto"},
    "golpe_calor": {"docs": ["seup_golpe_calor"], "query": "golpe de calor niño prevención"},
    "cefalea": {"docs": ["seup_cefalea"], "query": "cefalea dolor de cabeza niño"},
    "sincope": {"docs": ["seup_sincope"], "query": "síncope desmayo"},
    "espasmos_sollozo": {"docs": ["seup_espasmos_sollozo"], "query": "espasmos del sollozo"},
    "crisis_asma": {"docs": ["seup_crisis_asma"], "query": "crisis asmática inhalador"},
    "neumonia": {"docs": ["seup_neumonia"], "query": "neumonía niño síntomas"},
    "alimentacion_complementaria": {
        "docs": ["aep_alimentacion_complementaria", "who_complementary_feeding"],
        "query": "alimentación complementaria cuándo empezar",
    },
    "vacunas": {
        "docs": ["msan_calendario_vacunacion_2025"],
        "query": "calendario vacunación infantil",
    },
    "recien_nacido": {
        "docs": ["aep_cuidados_recien_nacido", "andalucia_cuidame_comienzo_vida"],
        "query": "cuidados recién nacido cordón baño",
    },
    "sueno_pantallas": {
        "docs": ["who_physical_activity_under5"],
        "query": "sleep screen time physical activity under 5",
    },
    "ansiedad": {"docs": ["seup_ansiedad"], "query": "ansiedad niños adolescentes"},
    "autolesion": {
        "docs": ["seup_autolesion", "seup_conducta_suicida"],
        "query": "conducta autolesiva adolescente",
    },
    "tca": {"docs": ["seup_tca"], "query": "trastorno conducta alimentaria adolescente"},
    # ---- added 25-ago with the international public sources ----
    "chickenpox": {
        "docs": ["nhs_en_chickenpox", "mlp_en_chickenpox", "cdc_en_chickenpox_about_index"],
        "query": "chickenpox varicella symptoms itching when to see doctor",
    },
    "hand_foot_mouth": {
        "docs": ["nhs_en_hand_foot_mouth_disease", "cdc_en_hand_foot_mouth_about_index"],
        "query": "hand foot and mouth disease children",
    },
    "scarlet_fever": {
        "docs": ["nhs_en_scarlet_fever"],
        "query": "scarlet fever rash strawberry tongue",
    },
    "meningitis_signs": {
        "docs": ["nhs_en_meningitis", "mlp_en_meningitis", "nhs_en_sepsis"],
        "query": "meningitis sepsis signs rash glass test children",
    },
    "teething": {"docs": ["nhs_en_baby_teething_symptoms"], "query": "teething symptoms baby"},
    "reflux": {"docs": ["nhs_en_reflux_in_babies"], "query": "reflux babies bringing up milk"},
    "constipation": {
        "docs": ["nhs_en_constipation", "mlp_en_constipation", "seup_estrenimiento"],
        "query": "constipation children hard stools",
    },
    "ear_infection": {
        "docs": ["nhs_en_ear_infections", "mlp_en_earinfections", "cdc_en_ear_infection"],
        "query": "ear infection children earache antibiotics",
    },
    "sore_throat": {
        "docs": ["nhs_en_sore_throat", "nhs_en_tonsillitis", "mlp_en_sorethroat"],
        "query": "sore throat tonsillitis children",
    },
    "common_cold": {
        "docs": ["mlp_en_commoncold", "cdc_en_colds", "seup_catarro"],
        "query": "common cold children runny nose antibiotics",
    },
    "flu": {
        "docs": ["nhs_en_flu", "cdc_en_children"],
        "query": "flu influenza children symptoms high risk",
    },
    "rsv": {
        "docs": [
            "nhs_en_respiratory_syncytial_virus_rsv",
            "cdc_en_rsv_infants_young_children_index",
            "cdc_en_rsv_about_index",
        ],
        "query": "RSV infants bronchiolitis symptoms",
    },
    "whooping_cough": {
        "docs": ["nhs_en_whooping_cough", "mlp_en_whoopingcough", "cdc_en_pertussis_about_index"],
        "query": "whooping cough pertussis babies vaccine",
    },
    "measles": {
        "docs": ["nhs_en_measles", "mlp_en_measles", "who_en_measles"],
        "query": "measles symptoms rash vaccine",
    },
    "head_injury_en": {
        "docs": [
            "nhs_en_head_injury_and_concussion",
            "mlp_en_headinjuries",
            "cdc_en_heads_up_signs_symptoms_index",
        ],
        "query": "head injury concussion children signs",
    },
    "febrile_seizure": {
        "docs": ["nhs_en_febrile_seizures", "seup_convulsion_febril"],
        "query": "febrile seizure what to do",
    },
    "diarrhoea_vomiting": {
        "docs": ["nhs_en_diarrhoea_and_vomiting", "mlp_en_gastroenteritis", "nhs_en_dehydration"],
        "query": "diarrhoea vomiting children fluids dehydration",
    },
    "burns": {
        "docs": ["nhs_en_burns_and_scalds", "mlp_en_burns"],
        "query": "burns scalds first aid children cool water",
    },
    "poisoning_en": {
        "docs": ["nhs_en_poisoning", "mlp_en_poisoning"],
        "query": "poisoning children swallowed what to do",
    },
    "choking": {
        "docs": ["mlp_en_choking", "mlp_es_choking", "andalucia_cuidame_guia"],
        "query": "choking baby child first aid",
    },
    "anaphylaxis_en": {
        "docs": ["nhs_en_anaphylaxis", "nhs_en_food_allergy", "seup_anafilaxia"],
        "query": "anaphylaxis food allergy adrenaline auto-injector",
    },
    "hives": {"docs": ["nhs_en_hives", "seup_urticaria"], "query": "hives urticaria children"},
    "rashes": {
        "docs": ["nhs_en_rashes_babies_and_children", "mlp_en_rashes"],
        "query": "rashes babies children spots",
    },
    "heat": {
        "docs": ["nhs_en_heat_exhaustion_heatstroke", "mlp_en_heatillness", "seup_golpe_calor"],
        "query": "heat exhaustion heatstroke children",
    },
    "sunburn": {"docs": ["nhs_en_sunburn"], "query": "sunburn children sun protection"},
    "insect_bites": {
        "docs": ["nhs_en_insect_bites_and_stings", "mlp_en_insectbitesandstings"],
        "query": "insect bites stings children",
    },
    "head_lice": {
        "docs": ["nhs_en_head_lice_and_nits", "cdc_en_lice_about_index"],
        "query": "head lice nits treatment",
    },
    "threadworms": {
        "docs": ["nhs_en_threadworms", "mlp_en_pinworms"],
        "query": "threadworms pinworms children",
    },
    "uti": {
        "docs": ["nhs_en_urinary_tract_infections_utis", "mlp_en_urinarytractinfections"],
        "query": "urinary tract infection children symptoms",
    },
    "conjunctivitis": {
        "docs": ["nhs_en_conjunctivitis", "mlp_en_pinkeye"],
        "query": "conjunctivitis pink eye children",
    },
    "nosebleed": {"docs": ["nhs_en_nosebleed"], "query": "nosebleed children how to stop"},
    "headache_en": {
        "docs": ["nhs_en_headaches_in_children", "mlp_en_headache", "seup_cefalea"],
        "query": "headaches children when to worry",
    },
    "bedwetting": {
        "docs": ["nhs_en_bedwetting", "mlp_en_bedwetting"],
        "query": "bedwetting children",
    },
    "growing_pains": {"docs": ["nhs_en_growing_pains"], "query": "growing pains legs night"},
    "cradle_cap": {"docs": ["nhs_en_cradle_cap"], "query": "cradle cap baby scalp"},
    "newborn_care_en": {
        "docs": ["nhs_en_caring_for_a_newborn", "mlp_en_infantandnewborncare"],
        "query": "caring for a newborn first weeks",
    },
    "weaning_en": {
        "docs": [
            "nhs_en_babys_first_solid_foods",
            "who_en_infant_and_young_child_feeding",
            "cdc_en_infant_toddler_nutrition_index",
        ],
        "query": "baby first solid foods weaning 6 months",
    },
    "breastfeeding": {
        "docs": ["mlp_en_breastfeeding", "who_en_infant_and_young_child_feeding"],
        "query": "breastfeeding how often benefits",
    },
    "vaccines_en": {
        "docs": [
            "nhs_en_nhs_vaccinations_and_when_to_have_them",
            "cdc_en_child_easyread",
            "mlp_en_childhoodimmunization",
        ],
        "query": "childhood vaccination schedule when",
    },
    "milestones": {
        "docs": ["cdc_en_act_early_milestones_index", "mlp_en_childdevelopment"],
        "query": "developmental milestones baby toddler",
    },
    "screen_sleep": {
        "docs": [
            "who_physical_activity_under5",
            "cdc_en_child_development_positive_parenting_tips_index",
        ],
        "query": "screen time sleep physical activity under 5",
    },
    "asthma_en": {
        "docs": ["nhs_en_asthma", "mlp_en_asthmainchildren", "seup_crisis_asma"],
        "query": "asthma children inhaler attack",
    },
    "paracetamol_en": {
        "docs": ["nhs_en_paracetamol_for_children"],
        "query": "paracetamol for children how to give",
    },
    "ibuprofen_en": {
        "docs": ["nhs_en_ibuprofen_for_children"],
        "query": "ibuprofen for children how to give",
    },
    # ---- comparison guides (idea 5): several organisations on one practical question ----
    "compare_fever_threshold": {
        "compare": True,
        "docs": ["seup_fiebre", "nhs_en_fever_in_children", "mlp_en_fever"],
        "query": "what is a fever temperature threshold 38 when to treat",
    },
    "compare_start_solids": {
        "compare": True,
        "docs": [
            "aep_alimentacion_complementaria",
            "who_en_infant_and_young_child_feeding",
            "nhs_en_babys_first_solid_foods",
            "cdc_en_infant_toddler_nutrition_index",
        ],
        "query": "when to start solid foods 6 months signs of readiness",
    },
    "compare_cough_medicines": {
        "compare": True,
        "docs": ["seup_catarro", "mlp_en_commoncold", "cdc_en_colds", "nhs_en_croup"],
        "query": "cough medicines children not recommended honey",
    },
    "compare_fever_medicine": {
        "compare": True,
        "docs": ["seup_fiebre", "nhs_en_paracetamol_for_children", "nhs_en_ibuprofen_for_children"],
        "query": "paracetamol ibuprofen fever when to give alternate",
    },
    "compare_head_injury_watch": {
        "compare": True,
        "docs": [
            "seup_tce",
            "nhs_en_head_injury_and_concussion",
            "cdc_en_heads_up_signs_symptoms_index",
        ],
        "query": "head injury what to watch for 48 hours",
    },
    "teen_mental_health": {
        "docs": ["mlp_en_teenmentalhealth", "who_en_adolescent_mental_health"],
        "query": "teen mental health anxiety depression signs",
    },
}


@dataclass
class Article:
    topic: str
    lang: str
    title: str
    summary: str
    body_md: str
    sources: list[str]
    chunk_ids: list[str]
    llm: LLMResult
    verification: str

    @property
    def slug(self) -> str:
        return make_slug(self.title, max_len=70)

    def frontmatter(self) -> str:
        today = dt.date.today().isoformat()
        srcs = "\n".join(f"  - {json.dumps(s, ensure_ascii=False)}" for s in self.sources)
        return (
            "---\n"
            f"title: {json.dumps(self.title, ensure_ascii=False)}\n"
            f"description: {json.dumps(self.summary, ensure_ascii=False)}\n"
            f"lang: {self.lang}\n"
            f"topic: {self.topic}\n"
            f"date: {today}\n"
            f"prompt_version: {'article_compare_v1' if TOPIC_PLAN.get(self.topic, {}).get('compare') else 'article_v1'}\n"
            f"model: {self.llm.model}\n"
            f"sources:\n{srcs}\n"
            "draft: false\n"
            "---\n"
        )

    def markdown(self) -> str:
        foot = "\n".join(f"{s}" for s in self.sources)
        disclaimer = (
            "*This guide summarises published paediatric guidelines. It is not medical advice and does not replace your paediatrician. In an emergency, call your local emergency number.*"
            if self.lang == "en"
            else "*Esta guía resume guías pediátricas publicadas. No es consejo médico y no sustituye a tu pediatra. En una emergencia, llama a tu número de emergencias.*"
        )
        return f"{self.frontmatter()}\n{self.body_md.strip()}\n\n## {'Sources' if self.lang == 'en' else 'Fuentes'}\n\n{foot}\n\n{disclaimer}\n"

    def public_url(self, site_url: str) -> str:
        """English is served from the root of the site; only Spanish carries a /es prefix."""
        prefix = "" if self.lang == "en" else f"/{self.lang}"
        return f"{site_url}{prefix}/guides/{self.slug}"

    def social_text(self, site_url: str) -> str:
        return f"{self.title}\n\n{self.summary}\n\n{self.public_url(site_url)}\n\nSources: {', '.join(sorted({s.split(' — ')[0].split('] ')[1] for s in self.sources}))}"


def load_prompt(version: str = "article_v1") -> str:
    return (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")


def gather_hits(index: Index, topic: str, max_chunks: int = 10) -> list[Hit]:
    plan = TOPIC_PLAN[topic]
    hits = index.search(str(plan["query"]), top_k=40, prefer_parent_leaflets=True)
    wanted: list[str] = list(plan["docs"])  # type: ignore[call-overload]
    anchored = [h for h in hits if h.chunk.doc_id in wanted and h.chunk.usage == "publico"]
    topics = {h.chunk.topic for h in anchored}
    others = [
        h
        for h in hits
        if h.chunk.doc_id not in wanted and h.chunk.usage == "publico" and h.chunk.topic in topics
    ]
    if plan.get("compare"):
        # one or two passages per organisation so the table has every voice
        per_org: dict[str, list[Hit]] = {}
        for h in anchored:
            per_org.setdefault(h.chunk.org, []).append(h)
        anchored = [h for hs in per_org.values() for h in hs[:2]]
    return (anchored + others)[:max_chunks]


def _format_sources(hits: list[Hit]) -> str:
    lines = []
    for i, h in enumerate(hits, start=1):
        c = h.chunk
        tag = " [DOSE TABLE]" if c.is_dose_table else ""
        tag += " [WARNING SIGNS]" if c.is_red_flag else ""
        lines.append(
            f"[{i}] {c.org} — {c.doc_title} — section: {c.section} (p. {', '.join(map(str, c.pages))}){tag}\n{c.text}"
        )
    return "\n\n".join(lines)


def parse_output(text: str) -> tuple[str, str, str]:
    m_t = re.search(r"TITLE:\s*(.+)", text)
    m_s = re.search(r"SUMMARY:\s*(.+)", text)
    m_b = re.search(r"BODY:\s*(.+)", text, re.S)
    if not (m_t and m_s and m_b):
        raise ValueError("article output missing TITLE/SUMMARY/BODY")
    return m_t.group(1).strip(), m_s.group(1).strip(), m_b.group(1).strip()


def _problems(title: str, body: str, hits: list[Hit], lang: str) -> list[str]:
    """Verification of the draft: citations and doses (shared with the answer engine) plus the
    language. A Spanish guide written into web/content/en carries `lang: en` in its frontmatter,
    which breaks canonical and hreflang as well as reading wrong."""
    problems = verify(body, hits)
    if detect_lang(f"{title} {body}") != lang:
        want = "English" if lang == "en" else "Spanish"
        problems.append(f"wrong_language (write the WHOLE article in {want})")
    return problems


def generate_article(index: Index, llm: LLMProvider, topic: str, lang: str = "en") -> Article:
    hits = gather_hits(index, topic)
    if not hits:
        raise ValueError(f"no sources for topic {topic}")
    system = load_prompt("article_compare_v1" if TOPIC_PLAN[topic].get("compare") else "article_v1")
    user = f"LANGUAGE: {'English' if lang == 'en' else 'Spanish'}\nTOPIC: {topic}\n\nSOURCES:\n{_format_sources(hits)}"
    result = llm.complete(system, user, temperature=0.3, max_tokens=1800)
    title, summary, body = parse_output(result.text)
    problems = _problems(title, body, hits, lang)
    verification = "ok"
    if problems:
        retry = llm.complete(
            system
            + "\n\nYour previous draft failed verification: "
            + ", ".join(problems)
            + ". Fix it.",
            user,
            temperature=0.0,
            max_tokens=1800,
        )
        title, summary, body = parse_output(retry.text)
        if _problems(title, body, hits, lang):
            raise ValueError(f"article for {topic} failed verification twice: {problems}")
        result, verification = retry, "regenerated"
    cited = sorted({int(n) for n in _CIT.findall(body)})
    sources = [
        f"[{n}] {hits[n - 1].chunk.citation()}"
        + (f" — {hits[n - 1].chunk.source_url}" if hits[n - 1].chunk.source_url else "")
        for n in cited
    ]
    return Article(
        topic,
        lang,
        title,
        summary,
        body,
        sources,
        [h.chunk.chunk_id for h in hits],
        result,
        verification,
    )


def write_article(
    a: Article, content_dir: Path, queue_dir: Path, site_url: str
) -> tuple[Path, Path]:
    out = content_dir / a.lang / f"{a.slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(a.markdown(), encoding="utf-8")
    q = queue_dir / "x" / f"{a.lang}-{a.slug}.txt"
    q.parent.mkdir(parents=True, exist_ok=True)
    q.write_text(a.social_text(site_url), encoding="utf-8")
    return out, q


def seasonal_first(
    topics: list[str], month: int | None = None, hemisphere: str = "north"
) -> list[str]:
    """Reorder pending topics so this month's seasonal ones (config/seasonal.yaml) come first."""
    import datetime as _dt

    import yaml

    from pedibot.settings import get_settings

    m = month or _dt.date.today().month
    if hemisphere == "south":
        m = (m + 6 - 1) % 12 + 1
    try:
        cal = yaml.safe_load(
            (get_settings().config_dir / "seasonal.yaml").read_text(encoding="utf-8")
        )
        first = [t for t in cal["north"].get(m, []) if t in topics]
    except Exception:  # noqa: BLE001
        first = []
    return first + [t for t in topics if t not in first]


def pending_topics(content_dir: Path, lang: str) -> list[str]:
    """Topics without an article yet in this language (by frontmatter `topic:`)."""
    done: set[str] = set()
    for f in (content_dir / lang).glob("*.md") if (content_dir / lang).exists() else []:
        m = re.search(r"^topic:\s*(\S+)", f.read_text(encoding="utf-8"), re.M)
        if m:
            done.add(m.group(1))
    # a `_en` suffix means the topic is anchored on English-speaking material (the NHS and CDC
    # vaccination schedules, for instance): in Spanish it only produces a near-duplicate guide
    pending = [t for t in TOPIC_PLAN if t not in done and (lang == "en" or not t.endswith("_en"))]
    return seasonal_first([t for t in pending if not _already_covered(t, done)])


def _already_covered(topic: str, done: set[str]) -> bool:
    """True if a published guide already speaks about this subject.

    The plan carries two keys for several subjects, one Spanish and one English (golpe_calor/heat,
    urticaria/hives, cefalea/headache_en…), and publishing both gives two nearly identical guides
    in the same language. Two topics are the same subject when they share most of their anchor
    documents. The `compare_*` articles reuse sources deliberately and are exempt.
    """
    plan = TOPIC_PLAN[topic]
    if plan.get("compare"):
        return False
    docs: set[str] = set(plan["docs"])  # type: ignore[call-overload]
    for other in done:
        other_plan = TOPIC_PLAN.get(other)
        if not other_plan or other_plan.get("compare"):
            continue
        other_docs: set[str] = set(other_plan["docs"])  # type: ignore[call-overload]
        shared = docs & other_docs
        if shared and len(shared) / min(len(docs), len(other_docs)) >= 0.5:
            return True
    return False
