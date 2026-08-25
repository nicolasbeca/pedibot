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

DISCLAIMER = {
    "en": "PediBot gives information from official paediatric guidelines. It is not medical advice and does not replace your paediatrician.",
    "es": "PediBot informa a partir de guías pediátricas oficiales. No es consejo médico y no sustituye a tu pediatra.",
}
NO_SOURCE = {
    "en": "I don't have reliable information on this in my sources, so I'd rather not guess. Please contact your paediatrician or a nurse line. If your child seems seriously unwell, go to the emergency department.",
    "es": "No tengo información fiable sobre esto en mis fuentes y prefiero no adivinar. Consulta con tu pediatra. Si tu hijo o hija parece estar grave, acude a urgencias.",
}
ASK_AGE = {
    "en": "To answer safely I need to know how old your child is (months or years). Could you tell me?",
    "es": "Para responder con seguridad necesito saber la edad (meses o años). ¿Me la dices?",
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
    verification: str  # ok | no_source | asked_age | dose_calculator | regenerated | fallback
    expansion: list[str] = field(default_factory=list)

    def render(self) -> str:
        parts = []
        if self.banner:
            parts.append(self.banner)
        parts.append(self.text)
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


def load_prompt(version: str = "answer_v2") -> tuple[str, str]:
    text = (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")
    return version, text


def build_banner(tr: TriageResult, lang: str, numbers: dict[str, str | None]) -> str | None:
    if tr.level == "routine":
        return None
    reasons = "; ".join(tr.reasons(lang))
    src = ", ".join(sorted({r.source for r in tr.matched}))
    if tr.level == "emergency":
        head = (
            f"🚨 Llama ahora al {numbers['emergency']} o acude a urgencias."
            if lang == "es"
            else f"🚨 Call {numbers['emergency']} now or go to the emergency department."
        )
    elif tr.level == "urgent":
        head = (
            "🚨 Con estos síntomas hay que acudir a urgencias hoy, sin esperar."
            if lang == "es"
            else "🚨 With these symptoms your child should be seen in the emergency department today, without waiting."
        )
    else:  # mental_health
        mental = numbers.get("mental") or numbers["emergency"]
        head = (
            f"💛 Esto es importante y no estás solo/a. Llama al {mental} (o al {numbers['emergency']} si hay peligro inmediato). Si el menor ha hecho algo para hacerse daño, acude a urgencias ahora."
            if lang == "es"
            else f"💛 This matters and you are not alone. Call {mental} (or {numbers['emergency']} if there is immediate danger). If your child has already done something to harm themselves, go to the emergency department now."
        )
    why = ("Motivo" if lang == "es" else "Reason") + f": {reasons} [{src}]"
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
    if _DOSE_NUM.search(text) and not any(h.chunk.is_dose_table for h in hits):
        problems.append("dose_without_table")
    return problems


class Engine:
    def __init__(
        self,
        retriever: Retriever,
        triage: Triage,
        llm: LLMProvider,
        numbers: EmergencyNumbers,
        prompt_version: str = "answer_v2",
        drugs: DrugCatalog | None = None,
    ):
        self.retriever = retriever
        self.triage = triage
        self.llm = llm
        self.numbers = numbers
        self.prompt_version, self.prompt = load_prompt(prompt_version)
        self.drugs = drugs

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
        if lang not in ("es", "en"):
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

        answer_lang = "English" if lang == "en" else "Spanish"
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
