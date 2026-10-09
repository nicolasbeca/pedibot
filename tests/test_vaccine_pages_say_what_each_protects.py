"""Cada página de calendario dice de qué protege cada vacuna (9-oct-2026).

La descripción prometía «cada edad con las vacunas que tocan y de qué protegen» y la tabla sólo
ponía siglas («DTwP-Hib-HepB», «MR», «PCV»); Google rastreaba 17 páginas de vacunas y no las
indexaba. `config/vaccine_protects.yaml` nombra la enfermedad de cada vacuna, con el CDC, el NHS
y la OMS como fuentes, y nada más: ni descripciones ni complicaciones.
"""

from __future__ import annotations

import pytest
import yaml

from pedibot.settings import ROOT
from pedibot.vaccine_protects import enfermedades, nombre_corto, por_pais

LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


@pytest.mark.parametrize(
    ("vacuna", "esperado"),
    [
        ("DTwP-Hib-HepB", {"diphtheria", "tetanus", "pertussis", "hib", "hepb"}),
        ("Hexavalent DTCaPolio-Hib-HepB (2e dose, obligatoire)", {"diphtheria", "tetanus", "pertussis", "hib", "hepb", "polio"}),
        ("Td booster", {"diphtheria", "tetanus"}),
        ("MR", {"measles", "rubella"}),
        ("Haemophilus influenzae b", {"hib"}),
        ("Méningocoque B (1re dose, obligatoire)", {"meningococcal"}),
        ("BCG (tuberculosis)", {"tb"}),
        ("Vitamin A (a supplement, not a vaccine)", set()),
    ],
)
def test_each_vaccine_names_its_diseases(vacuna: str, esperado: set[str]) -> None:
    assert set(enfermedades(vacuna)) == esperado


def test_every_vaccine_in_every_schedule_is_known() -> None:
    """Ninguna vacuna de los calendarios se queda sin enfermedad, salvo lo que no es vacuna."""
    paises = yaml.safe_load((ROOT / "config" / "vaccines.yaml").read_text(encoding="utf-8"))["countries"]
    sueltas = {
        str(v)
        for p in paises.values()
        for fila in p["schedule"]
        for v in fila["vaccines"]
        if not enfermedades(str(v)) and "vitamin a" not in str(v).lower()
    }
    assert not sueltas, sorted(sueltas)


def test_every_disease_in_every_language() -> None:
    raw = yaml.safe_load((ROOT / "config" / "vaccine_protects.yaml").read_text(encoding="utf-8"))
    for k, nombres in raw["diseases"].items():
        assert set(nombres) == set(LANGS), k
    for r in raw["rules"]:
        assert all(d in raw["diseases"] for d in r["diseases"]), r


def test_the_short_name_keeps_the_acronym_and_drops_the_dose() -> None:
    assert nombre_corto("Méningocoque B (1re dose, obligatoire)") == "Méningocoque B"
    assert nombre_corto("Polio oral (OPV)") == "Polio oral (OPV)"
    assert nombre_corto("Pentavalent-1") == "Pentavalent"
    assert nombre_corto("Td booster — 2nd dose 1 months later") == "Td booster"


def test_a_country_says_each_set_of_diseases_once() -> None:
    us = por_pais()["US"]
    sets = [tuple(v["diseases"]) for v in us]
    assert len(sets) == len(set(sets))
    dtap = next(v for v in us if v["diseases"] == ["diphtheria", "tetanus", "pertussis"])
    assert dtap["names"]["en"] == ["DTaP"]
    es = por_pais()["ES"]
    men = next(v for v in es if v["diseases"] == ["meningococcal"])
    assert len(men["names"]["es"]) == 3, men  # MenB, MenC y MenACWY, en una línea


def test_the_dose_number_goes_but_6_in_1_stays() -> None:
    assert nombre_corto("JE-1 (endemic districts only)") == "JE (endemic districts only)"
    assert nombre_corto("6-in-1 vaccine") == "6-in-1 vaccine"
    assert nombre_corto("Rotavirus-3") == "Rotavirus"


def test_the_dose_number_after_a_bracket_goes_too() -> None:
    assert nombre_corto("Measles & Rubella (MR)-1") == "Measles & Rubella (MR)"
    es = por_pais()["ES"]
    var = next(v for v in es if v["diseases"] == ["varicella"])
    assert var["names"]["es"] == ["Varicela (VVZ)"]


def test_the_built_pages_show_it() -> None:
    dist = ROOT / "web" / "site" / "dist"
    if not dist.exists():
        return
    us = (dist / "vaccines" / "us" / "index.html").read_text(encoding="utf-8")
    assert "What each vaccine protects against" in us and "Whooping cough (pertussis)" in us
    es = (dist / "es" / "vaccines" / "es" / "index.html").read_text(encoding="utf-8")
    assert "De qué protege cada vacuna" in es and "Tos ferina" in es
    eg = (dist / "ar" / "vaccines" / "eg" / "index.html").read_text(encoding="utf-8")
    assert "الدفتيريا، الكزاز" in eg  # la coma árabe
