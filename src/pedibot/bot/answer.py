"""The answer pipeline (PRD §5.1): triage → retrieval → drafting → verification → assembly."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pedibot.bot.dose import DRUGS, calculate, format_result
from pedibot.bot.llm import LLMProvider, LLMResult
from pedibot.bot.retrieval import Retriever, detect_lang
from pedibot.bot.triage import Triage, TriageResult
from pedibot.index.store import Hit

PROMPTS_DIR = Path(__file__).parent / "prompts"
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


def load_prompt(version: str = "answer_v1") -> tuple[str, str]:
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


def dose_intent(query: str) -> tuple[str, float] | None:
    """(drug_key, weight_kg) when the message is a dose question with an explicit weight."""
    d = _DRUG.search(query)
    w = _WEIGHT.search(query)
    if not d or not w:
        return None
    key = _DRUG_ALIAS.get(d.group(1).lower(), d.group(1).lower())
    if key not in DRUGS:
        return None
    return key, float(w.group(1).replace(",", "."))


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
        prompt_version: str = "answer_v1",
    ):
        self.retriever = retriever
        self.triage = triage
        self.llm = llm
        self.numbers = numbers
        self.prompt_version, self.prompt = load_prompt(prompt_version)

    def ask(self, query: str, country: str | None = None, lang: str | None = None) -> Answer:
        lang = lang or detect_lang(query)
        if lang not in ("es", "en"):
            lang = "en"
        tr = self.triage.assess(query)
        nums = self.numbers.get(country)
        banner = build_banner(tr, lang, nums)

        intent = dose_intent(query)
        if intent and tr.level == "routine":
            drug, kg = intent
            text = format_result(calculate(drug, kg, tr.age_months), lang)
            return Answer(text, tr.level, None, [], lang, None, None, [], "dose_calculator")

        if tr.level == "routine" and _needs_age(query, tr):
            return Answer(ASK_AGE[lang], tr.level, None, [], lang, None, None, [], "asked_age")

        hits, extra = self.retriever.search(query, lang, red_flag_boost=tr.is_alarm)
        if not hits:
            return Answer(
                NO_SOURCE[lang], tr.level, banner, [], lang, None, None, [], "no_source", extra
            )

        answer_lang = "English" if lang == "en" else "Spanish"
        user = (
            f"ANSWER LANGUAGE: {answer_lang} — the parent wrote in {answer_lang}; "
            "the sources may be in another language, translate faithfully.\n"
            f"{_age_context(tr)}"
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
