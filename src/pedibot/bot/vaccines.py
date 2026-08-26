"""Tabulated vaccination schedules (config/vaccines.yaml). Deterministic — the LLM never invents dates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_VACC = re.compile(
    r"\b(vacun\w*|vaccin\w*|inmuniz\w*|immuniz\w*|shots?|jabs?|mmr|dtap|dtpa|menb|hpv|vph|triple v[ií]rica)\b",
    re.I,
)
COUNTRY_ALIASES = {"UK": "GB", "EN": "GB", "USA": "US", "SPAIN": "ES", "ESPAÑA": "ES"}


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
        lg = "es" if lang == "es" else "en"
        out = []
        for s in self.raw[country]["schedule"]:
            out.append(
                Slot(
                    float(s["age"]), s["label"][lg], list(s["vaccines"]), bool(s.get("every_year"))
                )
            )
        return sorted(out, key=lambda x: x.age_months)

    def meta(self, country: str, lang: str = "en") -> dict[str, str]:
        lg = "es" if lang == "es" else "en"
        c = self.raw[country]
        return {
            "name": c["name"][lg],
            "source": c["source"],
            "source_url": c.get("source_url", ""),
            "note": c["note"][lg],
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
    es = lang == "es"
    m = v.meta(country, lang)
    if age_months is None:
        sched = v.schedule(country, lang)
        lines = [f"{m['name']}:"]
        for s in sched:
            lines.append(f"• {s.label}: " + ", ".join(s.vaccines))
        lines.append(("Fuente: " if es else "Source: ") + m["source"] + ". " + m["note"])
        return "\n".join(lines)
    due, nxt = v.at_age(country, age_months, lang)
    lines = []
    if due:
        lines.append(
            "A esta edad tocan, según el calendario oficial:"
            if es
            else "At this age the official schedule lists:"
        )
        for s in due:
            lines.append(f"• {s.label}: " + ", ".join(s.vaccines))
    else:
        lines.append(
            "A esta edad no hay ninguna vacuna programada en el calendario oficial."
            if es
            else "There is no vaccine scheduled at this exact age in the official calendar."
        )
    if nxt:
        lines.append(
            (f"Siguiente cita: {nxt.label} — " if es else f"Next: {nxt.label} — ")
            + ", ".join(nxt.vaccines)
        )
    lines.append(("Fuente: " if es else "Source: ") + m["source"] + ". " + m["note"])
    return "\n".join(lines)
