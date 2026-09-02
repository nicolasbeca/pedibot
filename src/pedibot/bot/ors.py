"""Oral rehydration solution (ORS) helper — deterministic, sourced (idea I-30).

Amounts are quoted from official leaflets and the SEUP parent sheets, never computed by the LLM:
- AEMPS (Spain) package leaflet, Sueroral Hiposódico (CIMA 59877): infants > 1 month ≈ 1–1.5 × the
  usual feed volume, in small frequent amounts; children ≥ 1 year ≈ 200 ml per loose stool, given as
  25–30 ml every 10–15 minutes; adults 200–400 ml per stool.
- SEUP "Vómitos": after vomiting, 5–10 ml (one or two spoonfuls) every 10 minutes, increasing
  gradually if no further vomiting; small frequent amounts; do not force food.
"""

from __future__ import annotations

from dataclasses import dataclass

from pedibot.bot.strings import tool_strings

SOURCES = {
    "aemps": "AEMPS — Prospecto Sueroral Hiposódico (CIMA 59877), sección 3 «Cómo tomar»",
    "seup_vomitos": "SEUP — «Vómitos. Información para padres», «¿Debemos ofrecerle alguna alimentación especial?»",
}


@dataclass(frozen=True)
class OrsAdvice:
    age_band: str  # under_1_month | infant | child | vomiting
    lines: list[str]
    warnings: list[str]
    sources: list[str]
    refer: bool


def advise(age_months: float | None, vomiting: bool = False, lang: str = "en") -> OrsAdvice:
    T = tool_strings(lang)
    warnings: list[str] = []
    refer = False
    if age_months is not None and age_months < 1:
        refer = True
        return OrsAdvice("under_1_month", [T["ors_under_1_month"]], [], [SOURCES["aemps"]], refer)
    if age_months is not None and age_months < 24:
        warnings.append(T["ors_under_2y"])
    lines: list[str] = []
    if vomiting:
        lines.append(T["ors_after_vomit"])
    if age_months is not None and age_months < 12:
        band = "infant"
        lines.append(T["ors_infant"])
    else:
        band = "child"
        lines.append(T["ors_child"])
    lines.append(T["ors_sachet"])
    warnings.append(T["ors_go_er"])
    srcs = [SOURCES["aemps"]]
    if vomiting:
        srcs.append(SOURCES["seup_vomitos"])
    return OrsAdvice(
        "vomiting" if vomiting and band == "child" else band, lines, warnings, srcs, refer
    )
