"""Rule-based severity triage. Runs before any LLM call (CLAUDE.md rule 3 and 5).

Levels: emergency > urgent > mental_health > routine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

LEVEL_ORDER = {"routine": 0, "mental_health": 1, "urgent": 2, "emergency": 3}

# `\b` is useless after Devanagari: most words end in a combining vowel sign, which Python does
# not count as a word character, so there is no boundary there to match. This pair works for both
# scripts — "not followed by a letter, a digit or any Devanagari sign" — and is what every age
# lookup below uses instead.
DEV = "\u0900-\u097f"
NOT_BEFORE = rf"(?<![\w{DEV}])"
NOT_AFTER = rf"(?![\w{DEV}])"

_AGE_PATTERNS = [
    # (regex, unit multiplier to months)
    (
        re.compile(
            r"(\d{1,2})\s*(?:meses|m[eê]s|months?|mois|monate[n]?|monat|mo|месяц\w*|мес"
            r"|شهر|أشهر|شهور)\b",
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
    # Hindi, in both scripts. Separate entries because they end with NOT_AFTER instead of `\b`.
    (
        re.compile(
            rf"(\d{{1,2}})\s*(?:महीने|महीना|महीनों|माह|मास|mahin[ae]|maheene){NOT_AFTER}", re.I
        ),
        1.0,
    ),
    (re.compile(rf"(\d{{1,2}})\s*(?:साल|वर्ष|बरस|s[a]?al|varsh){NOT_AFTER}", re.I), 12.0),
    (
        re.compile(rf"(\d{{1,2}})\s*(?:हफ़्ते|हफ्ते|हफ़्ता|हफ्ता|सप्ताह|haft[ae]|saptah){NOT_AFTER}", re.I),
        1 / 4.345,
    ),
    (re.compile(rf"(\d{{1,2}})\s*(?:दिन|din)\s*(?:का|के|की|ka|ke){NOT_AFTER}", re.I), 1 / 30.4),
]
_NEWBORN = re.compile(
    r"reci[eé]n nacid|rec[eé]m[- ]?nascid|newborn|neonat|nouveau[- ]n[eé]|neugeboren|новорожд"
    r"|حديث الولادة|مولود جديد|नवजात|navjat|naujaat",
    re.I,
)
_WORD_AGES = {
    "un mes": 1,
    # Las semanas en letra: es como se dice la edad de un recién nacido, y en cifra ya se
    # entendían. «mi bebé de tres semanas» no llegaba a la regla del lactante (7-sep-2026).
    "una semana": 0.23,
    "dos semanas": 0.46,
    "tres semanas": 0.69,
    "cuatro semanas": 0.92,
    "cinco semanas": 1.15,
    "seis semanas": 1.38,
    "siete semanas": 1.61,
    "ocho semanas": 1.84,
    "one week": 0.23,
    "two weeks": 0.46,
    "three weeks": 0.69,
    "four weeks": 0.92,
    "five weeks": 1.15,
    "six weeks": 1.38,
    "seven weeks": 1.61,
    "eight weeks": 1.84,
    "two week": 0.46,
    "three week": 0.69,
    "six week": 1.38,
    "1 mes": 1,
    "dos meses": 2,
    "tres meses": 3,
    "one month": 1,
    "two months": 2,
    "three months": 3,
    # "my two month old" — English drops the plural when the age is used as an adjective, and
    # that is the phrasing a parent types
    "two month": 2,
    "three month": 3,
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
    # Portuguese: it had been riding on the Spanish words, which works for "meses" and not for "mês"
    "um mês": 1,
    "um mes": 1,
    "dois meses": 2,
    "três meses": 3,
    "um ano": 12,
    "dois anos": 24,
    # Hindi, both scripts
    "एक महीने": 1,
    "एक महीना": 1,
    "एक माह": 1,
    "दो महीने": 2,
    "दो महीना": 2,
    "तीन महीने": 3,
    "एक साल": 12,
    "दो साल": 24,
    "ek mahina": 1,
    "ek mahine": 1,
    "do mahine": 2,
    "teen mahine": 3,
    "ek saal": 12,
    "do saal": 24,
}


@dataclass
class Rule:
    id: str
    level: str
    source: str
    reason_es: str
    reason_en: str
    #: every other language, keyed by code. It used to be one field per language with the
    #: loader copying each by name, so a new language silently answered in English — which
    #: is what happened to Hindi, on the component where silence is worst.
    reasons_by_lang: dict[str, str] = field(default_factory=dict)
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
            # a lookup, not a ladder of ifs: a new language used to mean remembering to add
            # a branch here, and forgetting meant silently answering in English
            if lang == "es":
                return r.reason_es
            return r.reasons_by_lang.get(lang) or r.reason_en

        return [pick(r) for r in self.matched]

    @property
    def is_alarm(self) -> bool:
        return self.level != "routine"


def parse_age_months(text: str) -> float | None:
    low = text.lower()
    if _NEWBORN.search(low):
        return 0.5
    for phrase, months in _WORD_AGES.items():
        if re.search(rf"{NOT_BEFORE}{re.escape(phrase)}{NOT_AFTER}", low):
            return float(months)
    for rx, mult in _AGE_PATTERNS:
        m = rx.search(text)
        if m:
            return float(m.group(1)) * mult
    return None


#: Lo que anula una señal si aparece justo antes de ella. Un padre que escribe «sin dificultad
#: para respirar» está diciendo lo contrario de lo que la regla busca, y hasta el 7-sep-2026
#: recibía una alarma de emergencia por decirlo.
NEGADORES = re.compile(
    r"(?:\bsin\b|\bno\b|\bni\b|\bnada de\b"
    r"|\bwithout\b|\bno\b|\bnot\b|\bdoes ?n[o']?t\b|\bhas ?n[o']?t\b|\bisn[o']?t\b"
    r"|\bsans\b|\bpas de\b|\baucun\w*\b"
    r"|\bohne\b|\bkein\w*\b|\bnicht\b"
    r"|\bsem\b|\bn[ãa]o\b"
    r"|\bбез\b|\bне\b|\bнет\b"
    r"|بدون|بلا|ليس|لا\s"
    r"|बिना|नहीं)"
    r"[\s\wáéíóúüñ,]{0,18}$",
    re.I | re.U,
)

#: Cuánto se mira hacia atrás. Corto a propósito: «no tiene fiebre, pero sí le cuesta respirar»
#: no puede quedar anulado por un «no» que iba con otra cosa.
VENTANA_NEGACION = 26


#: Lo que devuelve a la frase su valor afirmativo: el final de una oración, y las conjunciones
#: adversativas. «sin fiebre pero le cuesta respirar» tiene que seguir saltando.
CORTES = (
    ".", ";", "!", "?", "\n",
    " pero ", " aunque ", " but ", " aber ", " doch ", " jedoch ",
    " mais ", " mas ", " porém ", " но ", " однако ", " لكن ", " लेकिन ",
)


def _negada(texto: str, inicio: int, fin: int) -> bool:
    """¿Hay una negación pegada justo antes de esta coincidencia?

    No entiende la frase: solo mira la ventana anterior. Y no cuenta la negación que forma parte
    de la propia coincidencia — «no responde», «no deja de sangrar» y «no puede respirar» son
    patrones que empiezan por una negación y tienen que seguir saltando.
    """
    antes = texto[max(0, inicio - VENTANA_NEGACION) : inicio]
    # Una frase nueva corta el efecto de la negación anterior. Y una conjunción adversativa
    # también: «sin fiebre PERO le cuesta respirar» afirma la segunda mitad, y sin este corte
    # el «sin» de la fiebre anulaba la dificultad respiratoria (probado el 7-sep-2026).
    for corte in CORTES:
        if corte in antes:
            antes = antes.rsplit(corte, 1)[1]
    if NEGADORES.search(antes):
        # salvo que la propia coincidencia ya empiece negada
        return not NEGADORES.search(texto[inicio:fin][:14] + " ")
    return False


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
                    reasons_by_lang={
                        k[7:]: v for k, v in r.items()
                        if k.startswith("reason_") and k not in ("reason_es", "reason_en")
                    },
                    patterns=[re.compile(p, re.I) for p in r.get("patterns", [])],
                    requires=list(r.get("requires", [])),
                )
            )
        ctx = raw.get("context", {})
        self._fever = [re.compile(p, re.I) for p in ctx.get("fever", [])]

    def has_fever(self, text: str) -> bool:
        """«Sin fiebre» no es fiebre: la misma regla de negación que para los patrones."""
        return any(self._hits(rx, text) for rx in self._fever)

    @staticmethod
    def _hits(rx: re.Pattern[str], text: str) -> bool:
        """Una coincidencia cuenta salvo que venga negada. Se recorren todas: «sin fiebre pero le
        cuesta respirar» tiene que seguir saltando por la segunda mitad."""
        return any(not _negada(text, m.start(), m.end()) for m in rx.finditer(text))

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
            if any(self._hits(rx, text) for rx in r.patterns):
                matched.append(r)
        level = "routine"
        for r in matched:
            if LEVEL_ORDER[r.level] > LEVEL_ORDER[level]:
                level = r.level
        # mental health has its own protocol but never outranks a physical emergency
        matched.sort(key=lambda r: -LEVEL_ORDER[r.level])
        return TriageResult(level=level, matched=matched, age_months=age, has_fever=fever)
