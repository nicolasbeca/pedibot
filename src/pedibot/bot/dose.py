"""Deterministic dose calculator. The LLM never computes doses (CLAUDE.md rule 4).

Source of the ranges: AEPap, "Guía rápida de dosificación práctica en pediatría" (3.ª ed.),
table of analgesics/antipyretics:
  PARACETAMOL  40-60 mg/kg/día, 10-15 mg/kg/dosis, cada 4-6-8 h.
  IBUPROFENO   20 mg/kg/día (as listed in the guide; up to 30-40 mg/kg/día in other references),
               cada 6-8 h. Not under 3 months / 5 kg (ficha técnica).
Hard caps follow the Spanish summary of product characteristics (adult maxima) and are
intentionally conservative. Every number here has a unit test.
"""

from __future__ import annotations

from dataclasses import dataclass

from pedibot.bot.strings import tool_strings


@dataclass(frozen=True)
class Presentation:
    name: str
    mg_per_ml: float


@dataclass(frozen=True)
class Drug:
    key: str
    name_es: str
    name_en: str
    mg_per_kg_min: float
    mg_per_kg_max: float
    interval_hours: tuple[int, int]
    max_mg_per_kg_day: float
    max_single_dose_mg: float
    max_daily_mg: float
    min_age_months: float
    min_weight_kg: float
    presentations: tuple[Presentation, ...]
    source: str


PARACETAMOL = Drug(
    key="paracetamol",
    name_es="Paracetamol",
    name_en="Paracetamol (acetaminophen)",
    mg_per_kg_min=10,
    mg_per_kg_max=15,
    interval_hours=(4, 6),
    max_mg_per_kg_day=60,
    max_single_dose_mg=1000,
    max_daily_mg=4000,
    min_age_months=0,
    min_weight_kg=0,
    presentations=(
        Presentation("gotas 100 mg/ml", 100.0),
        Presentation("jarabe 120 mg/5 ml", 24.0),
        Presentation("jarabe 160 mg/5 ml", 32.0),
    ),
    source="AEPap — Guía rápida de dosificación práctica en pediatría (3.ª ed.), tabla analgésicos/antitérmicos",
)

IBUPROFENO = Drug(
    key="ibuprofeno",
    name_es="Ibuprofeno",
    name_en="Ibuprofen",
    mg_per_kg_min=5,
    mg_per_kg_max=10,
    interval_hours=(6, 8),
    max_mg_per_kg_day=30,
    max_single_dose_mg=400,
    max_daily_mg=1200,
    min_age_months=3,
    min_weight_kg=5,
    presentations=(
        Presentation("jarabe 2 % (100 mg/5 ml)", 20.0),
        Presentation("jarabe 4 % (200 mg/5 ml)", 40.0),
    ),
    source="AEPap — Guía rápida de dosificación práctica en pediatría (3.ª ed.), tabla analgésicos/antitérmicos",
)

DRUGS: dict[str, Drug] = {
    "paracetamol": PARACETAMOL,
    "acetaminophen": PARACETAMOL,
    "ibuprofeno": IBUPROFENO,
    "ibuprofen": IBUPROFENO,
}


@dataclass(frozen=True)
class DoseResult:
    drug: Drug
    weight_kg: float
    mg_min: float
    mg_max: float
    ml: dict[str, tuple[float, float]]
    interval_hours: tuple[int, int]
    max_doses_per_day: int
    warnings: list[str]
    refer: bool  # True → do not give: refer to paediatrician / emergency


class DoseError(ValueError):
    pass


def _round_ml(x: float) -> float:
    return round(x * 10) / 10


def calculate(drug_key: str, weight_kg: float, age_months: float | None = None) -> DoseResult:
    drug = DRUGS.get(drug_key.lower())
    if drug is None:
        raise DoseError(f"unknown drug: {drug_key}")
    if not (1.0 <= weight_kg <= 120.0):
        raise DoseError("weight must be between 1 and 120 kg")

    warnings: list[str] = []
    refer = False
    if age_months is not None and age_months < 3:
        warnings.append("under_3_months_refer")
        refer = True
    if age_months is not None and age_months < drug.min_age_months:
        warnings.append("below_min_age")
        refer = True
    if weight_kg < drug.min_weight_kg:
        warnings.append("below_min_weight")
        refer = True

    mg_min = drug.mg_per_kg_min * weight_kg
    mg_max = drug.mg_per_kg_max * weight_kg
    if mg_max > drug.max_single_dose_mg:
        warnings.append("capped_single_dose")
        mg_max = drug.max_single_dose_mg
        mg_min = min(mg_min, mg_max)

    # daily cap → max number of doses at the max single dose
    daily_cap = min(drug.max_mg_per_kg_day * weight_kg, drug.max_daily_mg)
    max_doses = int(daily_cap // mg_max) if mg_max > 0 else 0
    max_doses = max(1, min(max_doses, 24 // drug.interval_hours[0]))

    ml = {
        p.name: (_round_ml(mg_min / p.mg_per_ml), _round_ml(mg_max / p.mg_per_ml))
        for p in drug.presentations
    }
    return DoseResult(
        drug=drug,
        weight_kg=weight_kg,
        mg_min=round(mg_min, 1),
        mg_max=round(mg_max, 1),
        ml=ml,
        interval_hours=drug.interval_hours,
        max_doses_per_day=max_doses,
        warnings=warnings,
        refer=refer,
    )


def format_result(r: DoseResult, lang: str = "en") -> str:
    d = r.drug
    T = tool_strings(lang)
    name = d.name_es if lang == "es" else d.name_en
    lines = [T["dose_for"].format(name=name, kg=r.weight_kg)]
    if r.refer:
        lines.append(T["dose_refer"] + ", ".join(T["dose_warn"].get(w, w) for w in r.warnings) + ".")
    lines.append(
        T["dose_line"].format(
            mg_min=r.mg_min,
            mg_max=r.mg_max,
            h0=d.interval_hours[0],
            h1=d.interval_hours[1],
            max_doses=r.max_doses_per_day,
        )
    )
    for pname, (a, b) in r.ml.items():
        lines.append(f"  – {pname}: {a:g}–{b:g} ml")
    lines.append(T["dose_source"].format(source=d.source))
    lines.append(T["dose_check"])
    return "\n".join(lines)


def _warn_es(w: str) -> str:
    return {
        "under_3_months_refer": "menor de 3 meses",
        "below_min_age": "por debajo de la edad mínima del fármaco",
        "below_min_weight": "por debajo del peso mínimo del fármaco",
        "capped_single_dose": "dosis limitada al máximo por toma",
    }.get(w, w)


def _warn_en(w: str) -> str:
    return {
        "under_3_months_refer": "under 3 months old",
        "below_min_age": "below the minimum age for this drug",
        "below_min_weight": "below the minimum weight for this drug",
        "capped_single_dose": "dose capped at the maximum per dose",
    }.get(w, w)
