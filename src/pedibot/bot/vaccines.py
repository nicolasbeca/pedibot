"""Tabulated vaccination schedules (config/vaccines.yaml). Deterministic — the LLM never invents dates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from pedibot.bot.strings import data_lang, tool_strings

#: "Is this about vaccines?" — the gate to the vaccination tables, which are the most visited
#: pages on the site. It knew Spanish, English and French, so German, Russian, Arabic, Hindi and
#: PORTUGUESE ("vacina", no u) fell through to the corpus and never saw a calendar at all.
#: Devanagari sits outside the `\b(...)\b` group: `\w` excludes its combining vowel signs, so a
#: word boundary after टीके never matches — the same property that broke the triage patterns and
#: the query tokeniser.
_VACC = re.compile(
    r"\b("
    r"vacun\w*|vacin\w*|vaccin\w*|inmuniz\w*|immuniz\w*|imuniz\w*"
    r"|impf\w*|geimpft"
    r"|привив\w*|вакцин\w*"
    r"|teeka|teeke|teekaakaran"
    r"|shots?|jabs?|mmr|dtap|dtpa|menb|hpv|vph|triple v[ií]rica"
    r")\b"
    # Devanagari y árabe van FUERA del grupo con `\b`, y no por descuido: `\b` se define
    # sobre `\w`, y en estas escrituras el artículo y el plural son caracteres de palabra.
    # En «اللقاحات» la raíz لقاح lleva ال delante y ات detrás, así que no hay ninguna frontera
    # y `\bاللقاح\b` no casa nunca. El devanagari ya estaba fuera por esta misma razón; el
    # árabe seguía dentro y no detectaba media pregunta (7-sep-2026).
    r"|टीक|वैक्सीन"
    r"|تطعيم|تلقيح"
    # «حبوب اللقاح» es el POLEN, no una vacuna: una pregunta por la alergia al polen no puede
    # acabar en el calendario de vacunación.
    # Dos lookbehind encadenados y no una alternancia: `re` exige anchura fija en cada uno,
    # y «حبوب » (5) y «حبوب ال» (7) no la comparten. El primero cubre la forma desnuda y el
    # segundo la del artículo, que era la que se colaba.
    r"|(?<!حبوب )(?<!حبوب ال)لقاح",
    re.I,
)
COUNTRY_ALIASES = {"UK": "GB", "EN": "GB", "USA": "US", "SPAIN": "ES", "ESPAÑA": "ES"}

#: Country names as a parent writes them, in the eight languages of the site. Used ONLY to read a
#: country the question states out loud — never to infer one from the language. A French speaker
#: may be in Belgium, Canada or Switzerland, and handing a Belgian family the French calendar
#: would be worse than saying nothing, because it would look right.
COUNTRY_IN_TEXT: dict[str, tuple[str, ...]] = {
    "ES": (
        "españa",
        "espana",
        "spain",
        "espagne",
        "spanien",
        "испани",
        "إسبانيا",
        "espanha",
        "स्पेन",
    ),
    "FR": ("francia", "france", "frankreich", "франци", "فرنسا", "frança", "फ़्रांस", "फ्रांस"),
    "DE": (
        "alemania",
        "germany",
        "allemagne",
        "deutschland",
        "герман",
        "ألمانيا",
        "alemanha",
        "जर्मनी",
    ),
    "GB": (
        "reino unido",
        "united kingdom",
        "royaume-uni",
        "vereinigtes königreich",
        "великобритани",
        "المملكة المتحدة",
        "inglaterra",
        "england",
        "angleterre",
        "यूनाइटेड किंगडम",
    ),
    "US": (
        "estados unidos",
        "united states",
        "états-unis",
        "etats-unis",
        "vereinigte staaten",
        "сша",
        "الولايات المتحدة",
        "eeuu",
        "अमेरिका",
        "usa",
    ),
    "PT": ("portugal", "португали", "البرتغال", "पुर्तगाल"),
    "BR": (
        "brasil",
        "brazil",
        "brésil",
        "bresil",
        "brasilien",
        "бразили",
        "البرازيل",
        "ब्राज़ील",
        "ब्राजील",
    ),
}


#: Las formas cortas, que son como un padre nombra de verdad su país en inglés: «in the UK»,
#: «in the US». Faltaban las dos —y el mercado primero del producto es el inglés—, así que
#: «What vaccines are due at 12 months in the UK?» no llegaba a la tabla y se iba al corpus.
#:
#: Van aparte y con frontera de palabra porque la búsqueda de arriba es por subcadena, y con dos
#: letras eso es una trampa: «us» vive dentro de *because*, *must* y hasta de *bukhar*, y «uk»
#: dentro de *Ukraine*. Con «us» no basta la frontera —es un pronombre inglés corriente: «tell us
#: what vaccines»— así que se exige el artículo delante, que es como se escribe el país.
#:
#: «America» se queda fuera a propósito: en castellano y en portugués nombra el continente, y
#: leerlo como Estados Unidos le enseñaría a un padre colombiano el calendario que no es.
COUNTRY_SHORT: dict[str, re.Pattern[str]] = {
    "GB": re.compile(r"\b(?:uk|u\.k\.|great britain|britain|gro(?:ß|ss)britannien)\b", re.I),
    "US": re.compile(r"\b(?:the u\.?s\.?|u\.?s\.?a\.?)\b", re.I),
}


def country_in_question(text: str) -> str | None:
    """The country the question names out loud, or None.

    Longest name wins, so "reino unido" is not read as a shorter name that happens to sit inside
    it. Only consulted when the reader picked no country: a country they wrote themselves beats a
    guess, and there is no guess to fall back on.
    """
    low = text.lower()
    best: tuple[int, str] | None = None
    for code, names in COUNTRY_IN_TEXT.items():
        for name in names:
            if name in low and (best is None or len(name) > best[0]):
                best = (len(name), code)
    if best is not None:
        return best[1]
    for code, rx in COUNTRY_SHORT.items():
        if rx.search(low):
            return code
    return None


@dataclass(frozen=True)
class Slot:
    age_months: float
    label: str
    vaccines: list[str]
    every_year: bool = False


class Vaccines:
    def __init__(self, path: Path):
        self.raw = yaml.safe_load(path.read_text(encoding="utf-8"))["countries"]

    @property
    def countries(self) -> list[str]:
        return list(self.raw)

    def resolve_country(self, country: str | None) -> str | None:
        if not country:
            return None
        c = COUNTRY_ALIASES.get(country.upper(), country.upper())
        return c if c in self.raw else None

    def schedule(self, country: str, lang: str = "en") -> list[Slot]:
        out = []
        for s in self.raw[country]["schedule"]:
            lg = data_lang(s["label"], lang)
            out.append(
                Slot(
                    float(s["age"]), s["label"][lg], list(s["vaccines"]), bool(s.get("every_year"))
                )
            )
        return sorted(out, key=lambda x: x.age_months)

    def meta(self, country: str, lang: str = "en") -> dict[str, str]:
        c = self.raw[country]
        return {
            "name": c["name"][data_lang(c["name"], lang)],
            "source": c["source"],
            "source_url": c.get("source_url", ""),
            "note": c["note"][data_lang(c["note"], lang)],
        }

    def at_age(
        self, country: str, age_months: float, lang: str = "en"
    ) -> tuple[list[Slot], Slot | None]:
        """Slots due around this age (±1.5 months for infants, ±6 months after 2 years) and the next one."""
        sched = self.schedule(country, lang)
        tol = 1.5 if age_months < 24 else 6.0
        due = [s for s in sched if not s.every_year and abs(s.age_months - age_months) <= tol]
        due += [s for s in sched if s.every_year and s.age_months <= age_months]
        nxt = next((s for s in sched if not s.every_year and s.age_months > age_months + tol), None)
        return due, nxt


def is_vaccine_question(text: str) -> bool:
    return bool(_VACC.search(text))


def format_answer(v: Vaccines, country: str, age_months: float | None, lang: str = "en") -> str:
    T = tool_strings(lang)
    m = v.meta(country, lang)
    if age_months is None:
        sched = v.schedule(country, lang)
        lines = [f"{m['name']}:"]
        for s in sched:
            lines.append(f"• {s.label}: " + ", ".join(s.vaccines))
        lines.append(T["vax_source"] + m["source"] + ". " + m["note"])
        return "\n".join(lines)
    due, nxt = v.at_age(country, age_months, lang)
    lines = []
    if due:
        lines.append(T["vax_due"])
        for s in due:
            lines.append(f"• {s.label}: " + ", ".join(s.vaccines))
    else:
        lines.append(T["vax_none"])
    if nxt:
        lines.append(T["vax_next"].format(label=nxt.label) + ", ".join(nxt.vaccines))
    lines.append(T["vax_source"] + m["source"] + ". " + m["note"])
    return "\n".join(lines)
