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
    es = lang == "es"
    warnings: list[str] = []
    refer = False
    if age_months is not None and age_months < 1:
        refer = True
        return OrsAdvice(
            "under_1_month",
            [
                "Un bebé de menos de un mes con vómitos o diarrea debe ser valorado por un médico hoy; no se dan sueros sin indicación."
                if es
                else "A baby under one month with vomiting or diarrhoea must be seen by a doctor today; do not give rehydration solution without medical advice."
            ],
            [],
            [SOURCES["aemps"]],
            refer,
        )
    if age_months is not None and age_months < 24:
        warnings.append(
            "Menores de 2 años: consulta con el pediatra si los vómitos o la diarrea duran más de 24 horas o si rechaza los líquidos."
            if es
            else "Under 2 years: contact your paediatrician if vomiting or diarrhoea lasts more than 24 hours or the child refuses fluids."
        )
    lines: list[str] = []
    if vomiting:
        lines.append(
            "Tras un vómito, ofrece suero de rehidratación oral en cantidades muy pequeñas: 5–10 ml (una o dos cucharaditas, con cuchara o jeringa) cada 10 minutos, aumentando poco a poco si no vuelve a vomitar."
            if es
            else "After a vomit, offer oral rehydration solution in very small amounts: 5–10 ml (one or two teaspoons, by spoon or syringe) every 10 minutes, increasing gradually if there is no further vomiting."
        )
    if age_months is not None and age_months < 12:
        band = "infant"
        lines.append(
            "Lactante mayor de 1 mes con diarrea: aproximadamente 1–1,5 veces el volumen de su toma habitual, en pequeñas cantidades y despacio; no hace falta suspender la lactancia."
            if es
            else "Infant over 1 month with diarrhoea: roughly 1–1.5 times the usual feed volume, in small amounts and slowly; breastfeeding does not need to stop."
        )
    else:
        band = "child"
        lines.append(
            "Niño a partir de 1 año: unos 200 ml de suero por cada deposición diarreica, dándolo en tandas de 25–30 ml cada 10–15 minutos."
            if es
            else "Child aged 1 year or more: about 200 ml of solution for each loose stool, given as 25–30 ml every 10–15 minutes."
        )
    lines.append(
        "Prepara el sobre exactamente como dice el prospecto (un sobre por la cantidad de agua indicada); no lo diluyas más ni menos. No uses bebidas isotónicas, refrescos ni zumos."
        if es
        else "Make up the sachet exactly as the leaflet says (one sachet per the stated volume of water); do not make it stronger or weaker. Do not use sports drinks, fizzy drinks or juice."
    )
    warnings.append(
        "Acude a urgencias si no consigue retener líquidos, orina muy poco, tiene los ojos hundidos, está muy decaído o hay sangre en las heces."
        if es
        else "Go to the emergency department if fluids will not stay down, there is very little urine, sunken eyes, unusual drowsiness or blood in the stool."
    )
    srcs = [SOURCES["aemps"]]
    if vomiting:
        srcs.append(SOURCES["seup_vomitos"])
    return OrsAdvice(
        "vomiting" if vomiting and band == "child" else band, lines, warnings, srcs, refer
    )
