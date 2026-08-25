"""Generate a grounded article for a topic from the index, verify citations, write Markdown.

Output: web/content/<lang>/<slug>.md with YAML frontmatter (Astro content collection later) and
publish/queue/x/<slug>.txt with a hand-postable social text (no X API — operator decision).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

from pedibot.bot.answer import verify
from pedibot.bot.llm import LLMProvider, LLMResult
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
        srcs = "\n".join(f'  - "{s}"' for s in self.sources)
        return (
            "---\n"
            f'title: "{self.title.replace(chr(34), chr(39))}"\n'
            f'description: "{self.summary.replace(chr(34), chr(39))}"\n'
            f"lang: {self.lang}\n"
            f"topic: {self.topic}\n"
            f"date: {today}\n"
            f"prompt_version: article_v1\n"
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

    def social_text(self, site_url: str) -> str:
        return f"{self.title}\n\n{self.summary}\n\n{site_url}/{self.lang}/guides/{self.slug}\n\nSources: {', '.join(sorted({s.split(' — ')[0].split('] ')[1] for s in self.sources}))}"


def load_prompt(version: str = "article_v1") -> str:
    return (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")


def gather_hits(index: Index, topic: str, max_chunks: int = 10) -> list[Hit]:
    plan = TOPIC_PLAN[topic]
    hits = index.search(str(plan["query"]), top_k=40, prefer_parent_leaflets=True)
    wanted: list[str] = list(plan["docs"])  # type: ignore[call-overload]
    anchored = [h for h in hits if h.chunk.doc_id in wanted]
    others = [h for h in hits if h.chunk.doc_id not in wanted and h.chunk.usage == "publico"]
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


def generate_article(index: Index, llm: LLMProvider, topic: str, lang: str = "en") -> Article:
    hits = gather_hits(index, topic)
    if not hits:
        raise ValueError(f"no sources for topic {topic}")
    system = load_prompt()
    user = f"LANGUAGE: {'English' if lang == 'en' else 'Spanish'}\nTOPIC: {topic}\n\nSOURCES:\n{_format_sources(hits)}"
    result = llm.complete(system, user, temperature=0.3, max_tokens=1800)
    title, summary, body = parse_output(result.text)
    problems = verify(body, hits)
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
        if verify(body, hits):
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


def pending_topics(content_dir: Path, lang: str) -> list[str]:
    """Topics without an article yet in this language (by frontmatter `topic:`)."""
    done: set[str] = set()
    for f in (content_dir / lang).glob("*.md") if (content_dir / lang).exists() else []:
        m = re.search(r"^topic:\s*(\S+)", f.read_text(encoding="utf-8"), re.M)
        if m:
            done.add(m.group(1))
    return [t for t in TOPIC_PLAN if t not in done]
