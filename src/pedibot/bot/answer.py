"""The answer pipeline (PRD §5.1): triage → retrieval → drafting → verification → assembly."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pedibot.bot.dose import DRUGS, calculate, format_result
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.llm import LLMProvider, LLMResult
from pedibot.bot.retrieval import Retriever, detect_lang
from pedibot.bot.triage import LEVEL_ORDER, Triage, TriageResult
from pedibot.bot.vaccines import Vaccines, format_answer, is_vaccine_question
from pedibot.index.store import Hit

PROMPTS_DIR = Path(__file__).parent / "prompts"
MAX_TURNS = 6  # PRD §5.4: short window
CHILD_MODE = (
    "MODE: EXPLAIN TO THE CHILD. The parent wants a version to read aloud to a child aged 5-10. "
    "Keep every rule (sources only, citations [n], no doses). Write 3-5 very short, warm sentences "
    "in second person to the child ('your body…'), no scary words, one simple comparison, and end "
    "with one thing the child can do (drink, rest, tell mum or dad if…). Keep the citations.\n"
)
_CIT = re.compile(r"\[(\d{1,2})\]")
_WEIGHT = re.compile(r"(\d{1,3}(?:[.,]\d)?)\s*(?:kg|kilos?|kilogramos?|kgs)\b", re.I)
_DRUG = re.compile(
    r"\b(paracetamol|acetaminophen|tylenol|apiretal|ibuprofen[oe]?|dalsy|advil|nurofen)\w*", re.I
)
_DRUG_ALIAS = {
    "tylenol": "paracetamol",
    "apiretal": "paracetamol",
    "acetaminophen": "paracetamol",
    "dalsy": "ibuprofen",
    "advil": "ibuprofen",
    "nurofen": "ibuprofen",
    "ibuprofene": "ibuprofen",
    "ibuprofeno": "ibuprofen",
}
_DOSE_NUM = re.compile(r"\b\d+([.,]\d+)?\s*(mg|ml)\b", re.I)


# A millilitre figure is a medication dose unless the words around it clearly say fluid: the
# rehydration volumes in the SEUP vómitos/gastroenteritis leaflets are not doses. Fails closed —
# an unexplained "5 ml" still counts as a dose. Milligrams are always a dose.
_FLUID_WORDS = re.compile(
    r"(suero|rehidrataci|sales de rehidrat|rehydration|\bors\b|agua\b|water\b|leche|milk|"
    r"pecho|breast|biber[oó]n|bottle|toma[s]?\b|feed|l[ií]quido|fluid|zumo|juice)",
    re.I,
)
_MEDICINE_WORDS = re.compile(
    r"(paracetamol|acetaminophen|ibuprofeno|ibuprofen|antibi[oó]tic|antibiotic|amoxicilin|"
    r"amoxicillin|jarabe|syrup|antihistam[ií]nic|antihistamine|medicamento|medicine|dosis|dose|"
    r"calpol|dalsy|apiretal|junifen|tylenol|nurofen)",
    re.I,
)
_DOSE_WINDOW = 90


def looks_like_medication_dose(text: str) -> bool:
    """True if the text states a medication dose (mg always; ml unless clearly a fluid)."""
    for m in _DOSE_NUM.finditer(text):
        if m.group(2).lower() == "mg":
            return True
        around = text[max(0, m.start() - _DOSE_WINDOW) : m.end() + _DOSE_WINDOW]
        if _MEDICINE_WORDS.search(around):
            return True
        if not _FLUID_WORDS.search(around):
            return True
    return False


# Every language the engine will answer in. Adding one here is not enough on its own: it needs
# its triage patterns in red_flags.yaml and its texts below, or the safety layer goes silent.
SUPPORTED_LANGS = ("es", "en", "fr", "de")

DISCLAIMER = {
    "en": "PediBot gives information from official paediatric guidelines. It is not medical advice and does not replace your paediatrician.",
    "es": "PediBot informa a partir de guías pediátricas oficiales. No es consejo médico y no sustituye a tu pediatra.",
    "fr": "PediBot informe à partir de recommandations pédiatriques officielles. Ce n'est pas un avis médical et cela ne remplace pas votre pédiatre.",
    "de": "PediBot gibt Informationen aus offiziellen kinderärztlichen Leitlinien wieder. Das ist keine medizinische Beratung und ersetzt nicht Ihre Kinderärztin oder Ihren Kinderarzt.",
}
NO_SOURCE = {
    "en": "I don't have reliable information on this in my sources, so I'd rather not guess. Please contact your paediatrician or a nurse line. If your child seems seriously unwell, go to the emergency department.",
    "es": "No tengo información fiable sobre esto en mis fuentes y prefiero no adivinar. Consulta con tu pediatra. Si tu hijo o hija parece estar grave, acude a urgencias.",
    "fr": "Je n'ai pas d'information fiable à ce sujet dans mes sources et je préfère ne pas deviner. Parlez-en à votre pédiatre. Si votre enfant semble aller très mal, allez aux urgences.",
    "de": "Dazu habe ich in meinen Quellen keine verlässliche Information, und raten möchte ich nicht. Sprechen Sie bitte mit Ihrer Kinderärztin oder Ihrem Kinderarzt. Wenn Ihr Kind schwer krank wirkt, fahren Sie in die Notaufnahme.",
}
CLARIFY = {
    "en": "I want to get this right. What's the main thing going on?",
    "es": "Quiero acertar. ¿Qué es lo principal que le pasa?",
    "fr": "Je veux bien comprendre. Quel est le principal problème ?",
    "de": "Ich möchte es richtig verstehen. Was ist das Hauptproblem?",
}
CLARIFY_OPTIONS = {
    "en": [
        "Fever",
        "Cough or breathing",
        "Vomiting or diarrhoea",
        "Rash or skin",
        "A fall or injury",
        "Feeding or sleep",
        "Something else",
    ],
    "es": [
        "Fiebre",
        "Tos o respiración",
        "Vómitos o diarrea",
        "Manchas o piel",
        "Golpe o caída",
        "Comida o sueño",
        "Otra cosa",
    ],
    "fr": [
        "Fièvre",
        "Toux ou respiration",
        "Vomissements ou diarrhée",
        "Boutons ou peau",
        "Chute ou coup",
        "Alimentation ou sommeil",
        "Autre chose",
    ],
    "de": [
        "Fieber",
        "Husten oder Atmung",
        "Erbrechen oder Durchfall",
        "Ausschlag oder Haut",
        "Sturz oder Verletzung",
        "Essen oder Schlaf",
        "Etwas anderes",
    ],
}
ASK_AGE = {
    "en": "To answer safely I need to know how old your child is (months or years). Could you tell me?",
    "es": "Para responder con seguridad necesito saber la edad (meses o años). ¿Me la dices?",
    "fr": "Pour répondre en toute sécurité, j'ai besoin de l'âge de votre enfant (en mois ou en années). Pouvez-vous me le dire ?",
    "de": "Um sicher antworten zu können, muss ich wissen, wie alt Ihr Kind ist (in Monaten oder Jahren). Können Sie mir das sagen?",
}


@dataclass
class Answer:
    text: str
    level: str
    banner: str | None
    sources: list[str]
    lang: str
    prompt_version: str | None
    llm: LLMResult | None
    chunk_ids: list[str]
    verification: str  # ok | no_source | asked_age | dose_calculator | vaccine_schedule | clarify | regenerated | fallback
    expansion: list[str] = field(default_factory=list)
    options: list[str] = field(default_factory=list)  # quick replies when verification == 'clarify'

    @property
    def clean_text(self) -> str:
        """Answer text for humans: citation markers removed (they stay in `text` for verification)."""
        t = _CIT.sub("", self.text)
        t = re.sub(r"[ \t]+([.,;:!?])", r"\1", t)  # "word [1]." → "word."
        t = re.sub(r"[ \t]{2,}", " ", t)
        return t.strip()

    def render(self) -> str:
        """What the parent sees (operator decision 25-ago): banner + short answer. No source list,
        no document titles, no links — the organisation is already named inside the text. The legal
        line lives in the UI, not in every message."""
        parts = []
        if self.banner:
            parts.append(self.banner)
        parts.append(self.clean_text)
        return "\n\n".join(parts)

    def render_debug(self) -> str:
        """Full rendering with numbered sources, for logs, eval and the operator."""
        parts = [self.render()]
        if self.sources:
            parts.append(
                ("Fuentes:" if self.lang == "es" else "Sources:") + "\n" + "\n".join(self.sources)
            )
        parts.append("ℹ️ " + DISCLAIMER[self.lang])
        return "\n\n".join(parts)


class EmergencyNumbers:
    def __init__(self, path: Path):
        self.raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    def get(self, country: str | None) -> dict[str, str | None]:
        c = (country or "").upper()
        return self.raw.get(c) or self.raw["default"]


def load_prompt(version: str = "answer_v3") -> tuple[str, str]:
    text = (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")
    return version, text


def build_banner(tr: TriageResult, lang: str, numbers: dict[str, str | None]) -> str | None:
    if tr.level == "routine":
        return None
    reasons = "; ".join(tr.reasons(lang))
    if tr.level == "emergency":
        heads = {
            "es": f"🚨 Llama ahora al {numbers['emergency']} o acude a urgencias.",
            "en": f"🚨 Call {numbers['emergency']} now or go to the emergency department.",
            "fr": f"🚨 Appelez tout de suite le {numbers['emergency']} ou allez aux urgences.",
            "de": f"🚨 Rufen Sie jetzt {numbers['emergency']} an oder fahren Sie in die Notaufnahme.",
        }
    elif tr.level == "urgent":
        heads = {
            "es": "🚨 Con estos síntomas hay que acudir a urgencias hoy, sin esperar.",
            "en": "🚨 With these symptoms your child should be seen in the emergency department today, without waiting.",
            "fr": "🚨 Avec ces signes, votre enfant doit être vu aux urgences aujourd'hui, sans attendre.",
            "de": "🚨 Mit diesen Anzeichen sollte Ihr Kind heute in der Notaufnahme gesehen werden, ohne zu warten.",
        }
    else:  # mental_health
        mental = numbers.get("mental") or numbers["emergency"]
        heads = {
            "es": f"💛 Esto es importante y no estás solo/a. Llama al {mental} (o al {numbers['emergency']} si hay peligro inmediato). Si el menor ha hecho algo para hacerse daño, acude a urgencias ahora.",
            "en": f"💛 This matters and you are not alone. Call {mental} (or {numbers['emergency']} if there is immediate danger). If your child has already done something to harm themselves, go to the emergency department now.",
            "fr": f"💛 C'est important et vous n'êtes pas seul·e. Appelez le {mental} (ou le {numbers['emergency']} en cas de danger immédiat). Si votre enfant s'est déjà fait du mal, allez aux urgences maintenant.",
            "de": f"💛 Das ist wichtig, und Sie sind damit nicht allein. Rufen Sie {mental} an (oder {numbers['emergency']} bei unmittelbarer Gefahr). Wenn Ihr Kind sich bereits etwas angetan hat, fahren Sie jetzt in die Notaufnahme.",
        }
    head = heads.get(lang, heads["en"])
    why = {"es": "Motivo", "fr": "Raison", "de": "Grund"}.get(lang, "Reason") + f": {reasons}"
    return head + "\n" + why


def dose_intent(query: str, drugs: DrugCatalog | None = None) -> tuple[str, float] | None:
    """(drug_key, weight_kg) when the message is a dose question with an explicit weight.

    Brand names (Calpol, Tylenol, Dalsy, Nurofen…) resolve through the catalogue when given."""
    w = _WEIGHT.search(query)
    if not w:
        return None
    kg = float(w.group(1).replace(",", "."))
    key: str | None = None
    d = _DRUG.search(query)
    if d:
        key = _DRUG_ALIAS.get(d.group(1).lower(), d.group(1).lower())
    elif drugs is not None:
        for tok in re.findall(r"[a-záéíóúñ][a-záéíóúñ'\-]{3,}", query.lower()):
            r = drugs.resolve(tok)
            if r:
                key = r[0]
                break
    if key is None or key not in DRUGS:
        return None
    return key, kg


_CHILD = re.compile(
    r"\b(hij[oa]|beb[eé]|ni[ñn][oa]|peque|my (son|daughter|baby|child|toddler|kid|little one)|"
    r"mon (fils|b[eé]b[eé]|enfant)|ma (fille|petite)|mein[e]? (sohn|tochter|kind|baby)|"
    r"\d+\s*(años|año|meses|mes|year|years|month|months|weeks?|semanas?|ans|mois|"
    r"jahre[n]?|monate[n]?|wochen)\b)",
    re.I,
)


def _mentions_child(text: str) -> bool:
    return bool(_CHILD.search(text))


def _age_context(tr: TriageResult) -> str:
    """Age line for the prompt. Under 3 months: home medication advice is never appropriate."""
    if tr.age_months is None:
        return "CHILD AGE: unknown\n"
    if tr.age_months < 3:
        return (
            f"CHILD AGE: {tr.age_months:g} months — UNDER 3 MONTHS. Do NOT suggest giving any "
            "medication at home (no paracetamol, no ibuprofen); do not describe home management "
            "of fever. Say that babies this young must be assessed by a doctor the same day and "
            "keep the answer short.\n"
        )
    if tr.age_months < 6:
        return (
            f"CHILD AGE: {tr.age_months:g} months — under 6 months. Do not suggest ibuprofen; "
            "any medication only if a doctor advised it.\n"
        )
    return f"CHILD AGE: {tr.age_months:g} months\n"


def _history_block(history: list[dict[str, str]]) -> str:
    if not history:
        return ""
    lines = []
    for t in history:
        who = "Parent" if t.get("role") == "user" else "PediBot"
        lines.append(f"{who}: {t['text'][:600]}")
    return (
        "CONVERSATION SO FAR (answer the LAST parent message; earlier turns give context such as age or symptoms already mentioned):\n"
        + "\n".join(lines)
        + "\n\n"
    )


def _needs_age(query: str, tr: TriageResult) -> bool:
    """Fever without age → ask (rule: <3 months with fever is urgent, we cannot know)."""
    return tr.has_fever and tr.age_months is None


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


def verify(text: str, hits: list[Hit]) -> list[str]:
    """Return a list of problems (empty = ok)."""
    problems: list[str] = []
    nums = [int(n) for n in _CIT.findall(text)]
    if not nums:
        problems.append("no_citations")
    for n in nums:
        if n < 1 or n > len(hits):
            problems.append(f"bad_citation_{n}")
    sanctioned = any(h.chunk.is_dose_table and h.chunk.is_dose_source for h in hits)
    if looks_like_medication_dose(text) and not sanctioned:
        problems.append("dose_without_table")
    return problems


class Engine:
    def __init__(
        self,
        retriever: Retriever,
        triage: Triage,
        llm: LLMProvider,
        numbers: EmergencyNumbers,
        prompt_version: str = "answer_v3",
        drugs: DrugCatalog | None = None,
        vaccines: Vaccines | None = None,
    ):
        self.retriever = retriever
        self.triage = triage
        self.llm = llm
        self.numbers = numbers
        self.prompt_version, self.prompt = load_prompt(prompt_version)
        self.drugs = drugs
        self.vaccines = vaccines

    def _inject_rule_sources(self, tr: TriageResult, hits: list[Hit]) -> list[Hit]:
        """When a triage rule fired, put the warning-signs chunk of the rule's own source first,
        so the drafted sentence "must be seen today" can cite it instead of echoing the prompt
        (faithfulness judge, 25-ago: 6 of 8 'unfaithful' were exactly this)."""
        if not tr.matched:
            return hits
        present = {h.chunk.doc_id for h in hits if h.chunk.is_red_flag}
        injected: list[Hit] = []
        for rule in tr.matched:
            if rule.source in present:
                continue
            c = self.retriever.index.red_flag_chunk(rule.source)
            if c is not None:
                injected.append(Hit(c, 99.0, 1))
                present.add(rule.source)
        return (injected + hits)[: max(len(hits), 6) + len(injected)]

    def ask(
        self,
        query: str,
        country: str | None = None,
        lang: str | None = None,
        history: list[dict[str, str]] | None = None,
        mode: str = "parent",
    ) -> Answer:
        """`history`: previous turns, oldest first, [{"role": "user"|"assistant", "text": ...}].
        Only the last MAX_TURNS are used (PRD §5.4)."""
        history = (history or [])[-MAX_TURNS:]
        prior_user = " ".join(t["text"] for t in history if t.get("role") == "user")
        context_text = f"{prior_user} {query}".strip() if prior_user else query
        lang = lang or detect_lang(query)
        if lang not in SUPPORTED_LANGS:
            lang = "en"
        tr = self.triage.assess(context_text)
        tr_now = self.triage.assess(query)
        # rules that fired only because of OLD messages must not re-trigger a banner every turn,
        # except the age-based ones (age is context, not a symptom)
        if history:
            keep = {r.id for r in tr_now.matched} | {
                "infant_fever_under_3_months",
                "newborn_refusing_feeds",
            }
            tr.matched = [r for r in tr.matched if r.id in keep]
            tr.level = max(
                (r.level for r in tr.matched), key=lambda lv: LEVEL_ORDER[lv], default="routine"
            )
        nums = self.numbers.get(country)
        banner = build_banner(tr, lang, nums)

        intent = dose_intent(query, self.drugs) or (
            dose_intent(context_text, self.drugs)
            if _DRUG.search(query)
            or (
                self.drugs
                and any(
                    self.drugs.resolve(t) for t in re.findall(r"[a-záéíóúñ]{4,}", query.lower())
                )
            )
            else None
        )
        if intent and tr.level == "routine":
            drug, kg = intent
            text = format_result(calculate(drug, kg, tr.age_months), lang)
            return Answer(text, tr.level, None, [], lang, None, None, [], "dose_calculator")

        if self.vaccines is not None and tr.level == "routine" and is_vaccine_question(query):
            c = self.vaccines.resolve_country(country)
            if c is not None:
                text = format_answer(self.vaccines, c, tr.age_months, lang)
                return Answer(text, tr.level, None, [], lang, None, None, [], "vaccine_schedule")
            # no tabulated schedule for this country → fall through to the sources

        # vague first message -> offer options. The topic is read from the query PLUS its synonym
        # expansion, the same as retrieval does: "se ha desmayado" or "llora sin parar" are clear
        # questions that the taxonomy does not name literally, and clarifying them is a bad answer.
        if (
            tr.level == "routine"
            and not history
            and self.retriever.taxonomy is not None
            and self.retriever.taxonomy.topic_for(
                query + " " + " ".join(self.retriever.expand(query, lang))
            )
            is None
            and (len(query.split()) <= 3 or _mentions_child(query))
        ):
            return Answer(
                CLARIFY[lang],
                tr.level,
                None,
                [],
                lang,
                None,
                None,
                [],
                "clarify",
                options=CLARIFY_OPTIONS[lang],
            )

        if tr.level == "routine" and _needs_age(context_text, tr):
            return Answer(ASK_AGE[lang], tr.level, None, [], lang, None, None, [], "asked_age")

        prev_user = next((t["text"] for t in reversed(history) if t.get("role") == "user"), "")
        search_q = f"{prev_user} {query}" if prev_user and len(query.split()) <= 8 else query
        hits, extra = self.retriever.search(search_q, lang, red_flag_boost=tr.is_alarm)
        hits = self._inject_rule_sources(tr, hits)
        if not hits:
            return Answer(
                NO_SOURCE[lang], tr.level, banner, [], lang, None, None, [], "no_source", extra
            )

        answer_lang = {"en": "English", "es": "Spanish", "fr": "French"}.get(lang, "English")
        user = (
            f"ANSWER LANGUAGE: {answer_lang} — the parent wrote in {answer_lang}; "
            "the sources may be in another language, translate faithfully.\n"
            f"{_age_context(tr)}"
            f"{_history_block(history)}"
            f"{CHILD_MODE if mode == 'child' else ''}"
            f"PARENT MESSAGE:\n{query}\n\nSOURCES:\n{_format_sources(hits)}"
        )
        result = self.llm.complete(self.prompt, user, temperature=0.2)
        problems = verify(result.text, hits)
        verification = "ok"
        if problems:
            verification = "regenerated"
            retry = self.llm.complete(
                self.prompt
                + "\n\nYour previous draft failed verification: "
                + ", ".join(problems)
                + ". Fix it.",
                user,
                temperature=0.0,
            )
            if verify(retry.text, hits):
                return Answer(
                    NO_SOURCE[lang],
                    tr.level,
                    banner,
                    [],
                    lang,
                    self.prompt_version,
                    retry,
                    [h.chunk.chunk_id for h in hits],
                    "fallback",
                    extra,
                )
            result = retry

        cited = sorted({int(n) for n in _CIT.findall(result.text)})
        sources = [
            f"[{n}] {hits[n - 1].chunk.citation()}"
            + (f" — {hits[n - 1].chunk.source_url}" if hits[n - 1].chunk.source_url else "")
            for n in cited
        ]
        return Answer(
            result.text.strip(),
            tr.level,
            banner,
            sources,
            lang,
            self.prompt_version,
            result,
            [h.chunk.chunk_id for h in hits],
            verification,
            extra,
        )
