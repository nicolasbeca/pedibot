"""Las cifras de las descripciones del agente se cuentan, no se escriben (2-oct-2026).

Glama leyó la herramienta de alarmas y la puntuó por «46 fixed warning-sign rules». Eran 96
desde hacía semanas. La dosis decía «32 brands across 27 countries» y son 35 en 57. Esas
descripciones las leen los asistentes por MCP y los compradores de ACP, y una cifra vieja en un
sitio de salud es justo lo que el proyecto no se permite. Cada número que aparezca en una
descripción tiene que coincidir con lo que el código cuenta hoy.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.growth import load_countries
from pedibot.bot.triage import Triage
from pedibot.bot.vaccines import Vaccines
from pedibot.settings import ROOT

CFG = ROOT / "config"
OFF = {
    o["name"]: o
    for o in json.loads((ROOT / "ops" / "acp_catalogue.json").read_text(encoding="utf-8"))[
        "offerings"
    ]
}


def _desc(name: str) -> str:
    return OFF[name]["description"]


def test_the_warning_rules_are_counted():
    n = len(Triage(CFG / "red_flags.yaml").rules)
    assert f"{n} fixed warning-sign rules" in _desc("paediatric_warning_sign_check")


def test_the_brands_and_their_countries_are_counted():
    cat = DrugCatalog(CFG / "drugs.yaml")
    brands = [b for k in cat.drugs for b in cat.brands_for(k, None)]
    names = {b.name for b in brands}
    countries = {c for b in brands for c in b.countries}
    assert f"{len(names)} brands across {len(countries)} countries" in _desc("child_medicine_dose")


def test_the_vaccine_schedules_are_counted():
    v = Vaccines(CFG / "vaccines.yaml")
    who = [c for c in v.countries if "WIISE" in str(v.meta(c, "en").get("source", ""))]
    d = _desc("childhood_vaccination_schedule")
    assert f"for {len(v.countries)} countries" in d
    assert f"{len(v.countries) - len(who)} transcribed by hand" in d
    assert f"{len(who)} read from the WHO" in d


def test_the_growth_countries_are_counted():
    n = len(load_countries(CFG / "growth_charts.yaml"))
    assert f"{n} countries covered" in _desc("child_growth_percentile")


#: Cifras que no son recuentos: años de las tablas, edades, límites de una regla clínica.
NO_SON_RECUENTOS = {"5", "10", "2006", "2007", "2", "2000"}


def test_every_number_in_a_description_is_checked_above():
    comprobados = {
        "paediatric_warning_sign_check",
        "child_medicine_dose",
        "childhood_vaccination_schedule",
        "child_growth_percentile",
    }
    for name, o in OFF.items():
        sueltos = set(re.findall(r"\d+", o["description"])) - NO_SON_RECUENTOS
        if name not in comprobados:
            assert not sueltos, f"{name} lleva cifras sin test: {sueltos}"
