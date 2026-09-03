"""Rule-based severity triage. Runs before any LLM call (CLAUDE.md rule 3 and 5).

Levels: emergency > urgent > mental_health > routine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

LEVEL_ORDER = {"routine": 0, "mental_health": 1, "urgent": 2, "emergency": 3}

_AGE_PATTERNS = [
    # (regex, unit multiplier to months)
    (
        re.compile(
            r"(\d{1,2})\s*(?:meses|mes|months?|mois|monate[n]?|monat|mo|месяц\w*|мес|شهر|أشهر|شهور)\b",
            re.I,
        ),
        1.0,
    ),
    (
        re.compile(
            r"(\d{1,2})\s*(?:años|año|anos|years?|yrs?|ans?|jahre[n]?|jahr|год\w*|лет|سنة|سنوات|سنين|y\.?o\.?)\b",
            re.I,
        ),
        12.0,
    ),
    (
        re.compile(
            r"(\d{1,2})\s*(?:semanas|semana|weeks?|semaines?|wochen|woche|недел\w*|нед|أسبوع|أسابيع|wks?)\b",
            re.I,
        ),
        1 / 4.345,
    ),
    (
        re.compile(
            r"(\d{1,2})\s*(?:d[ií]as|d[ií]a|days?|jours?)\s*(?:de (?:vida|edad|nacid|vie)|old)",
            re.I,
        ),
        1 / 30.4,
    ),
    (re.compile(r"(?:tiene|has|is|de)\s+(\d{1,2})\s*(?:a|y)\b", re.I), 12.0),
]
_NEWBORN = re.compile(
    r"reci[eé]n nacid|newborn|neonat|nouveau[- ]n[eé]|neugeboren|новорожд|حديث الولادة|مولود جديد",
    re.I,
)
_WORD_AGES = {
    "un mes": 1,
    "1 mes": 1,
    "dos meses": 2,
    "tres meses": 3,
    "one month": 1,
    "two months": 2,
    "three months": 3,
    "un año": 12,
    "dos años": 24,
    "one year": 12,
    "two years": 24,
    "un mois": 1,
    "deux mois": 2,
    "trois mois": 3,
    "un an": 12,
    "deux ans": 24,
    "ein monat": 1,
    "einem monat": 1,
    "zwei monate": 2,
    "zwei monaten": 2,
    "drei monate": 3,
    "drei monaten": 3,
    "ein jahr": 12,
    "einem jahr": 12,
    "zwei jahre": 24,
    "zwei jahren": 24,
    "один месяц": 1,
    "месяц": 1,
    "два месяца": 2,
    "три месяца": 3,
    "год": 12,
    "одного года": 12,
    "два года": 24,
    # Arabic has a form of its own for exactly two, and it is the age that matters most here
    "شهر": 1,
    "شهر واحد": 1,
    "شهران": 2,
    "شهرين": 2,
    "ثلاثة أشهر": 3,
    "ثلاثة اشهر": 3,
    "سنة": 12,
    "سنة واحدة": 12,
    "سنتان": 24,
    "سنتين": 24,
}


@dataclass
class Rule:
    id: str
    level: str
    source: str
    reason_es: str
    reason_en: str
    reason_fr: str = ""
    reason_de: str = ""
    reason_ru: str = ""
    reason_ar: str = ""
    patterns: list[re.Pattern[str]] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)


@dataclass
class TriageResult:
    level: str
    matched: list[Rule]
    age_months: float | None
    has_fever: bool

    def reasons(self, lang: str = "en") -> list[str]:
        def pick(r: Rule) -> str:
            if lang == "es":
                return r.reason_es
            if lang == "fr" and r.reason_fr:
                return r.reason_fr
            if lang == "de" and r.reason_de:
                return r.reason_de
            if lang == "ru" and r.reason_ru:
                return r.reason_ru
            if lang == "ar" and r.reason_ar:
                return r.reason_ar
            return r.reason_en

        return [pick(r) for r in self.matched]

    @property
    def is_alarm(self) -> bool:
        return self.level != "routine"


def parse_age_months(text: str) -> float | None:
    low = text.lower()
    if _NEWBORN.search(low):
        return 0.5
    for phrase, months in _WORD_AGES.items():
        if re.search(rf"\b{re.escape(phrase)}\b", low):
            return float(months)
    for rx, mult in _AGE_PATTERNS:
        m = rx.search(text)
        if m:
            return float(m.group(1)) * mult
    return None


class Triage:
    def __init__(self, path: Path):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.rules: list[Rule] = []
        for r in raw["rules"]:
            self.rules.append(
                Rule(
                    id=r["id"],
                    level=r["level"],
                    source=r["source"],
                    reason_es=r["reason_es"],
                    reason_en=r["reason_en"],
                    reason_fr=r.get("reason_fr", ""),
                    reason_de=r.get("reason_de", ""),
                    reason_ru=r.get("reason_ru", ""),
                    reason_ar=r.get("reason_ar", ""),
                    patterns=[re.compile(p, re.I) for p in r.get("patterns", [])],
                    requires=list(r.get("requires", [])),
                )
            )
        ctx = raw.get("context", {})
        self._fever = [re.compile(p, re.I) for p in ctx.get("fever", [])]

    def has_fever(self, text: str) -> bool:
        return any(rx.search(text) for rx in self._fever)

    def assess(self, text: str) -> TriageResult:
        age = parse_age_months(text)
        fever = self.has_fever(text)
        flags = {
            "fever": fever,
            "age_under_3_months": age is not None and age < 3,
        }
        matched: list[Rule] = []
        for r in self.rules:
            if r.requires:
                if all(flags.get(k, False) for k in r.requires):
                    matched.append(r)
                continue
            if any(rx.search(text) for rx in r.patterns):
                matched.append(r)
        level = "routine"
        for r in matched:
            if LEVEL_ORDER[r.level] > LEVEL_ORDER[level]:
                level = r.level
        # mental health has its own protocol but never outranks a physical emergency
        matched.sort(key=lambda r: -LEVEL_ORDER[r.level])
        return TriageResult(level=level, matched=matched, age_months=age, has_fever=fever)
