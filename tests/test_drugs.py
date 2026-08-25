from __future__ import annotations

import pytest

from pedibot.bot.dose import DRUGS, calculate
from pedibot.bot.drugs import DrugCatalog


@pytest.fixture(scope="module")
def cat(config_dir) -> DrugCatalog:
    return DrugCatalog(config_dir / "drugs.yaml")


@pytest.mark.parametrize(
    "name,key,brand",
    [
        ("paracetamol", "paracetamol", None),
        ("Acetaminophen", "paracetamol", None),
        ("ibuprofeno", "ibuprofen", None),
        ("Calpol", "paracetamol", "Calpol"),
        ("tylenol", "paracetamol", "Tylenol Children's / Infants'"),
        ("Dalsy", "ibuprofen", "Dalsy"),
        ("nurofen", "ibuprofen", "Nurofen for Children"),
        ("Apiretal", "paracetamol", "Apiretal"),
        ("Advil", "ibuprofen", "Advil Children's / Infants'"),
        ("motrin", "ibuprofen", "Motrin Children's / Infants'"),
    ],
)
def test_resolve(cat, name, key, brand):
    r = cat.resolve(name)
    assert r is not None and r[0] == key
    assert (r[1].name if r[1] else None) == brand


def test_unknown_and_excluded(cat):
    assert cat.resolve("aspirin") is None
    assert cat.resolve("amoxicillin") is None
    assert (
        cat.resolve("dalsy is ibuprofen") is None
        or cat.resolve("dalsy is ibuprofen")[0] == "ibuprofen"
    )


def test_brand_strengths_parse(cat):
    _, calpol = cat.resolve("calpol")
    assert calpol is not None
    assert calpol.strengths_mg_per_ml() == [
        ("infant 120 mg/5 ml", 24.0),
        ("six plus 250 mg/5 ml", 50.0),
    ]
    _, advil = cat.resolve("advil")
    assert ("infant drops 200 mg/5 ml (40 mg/ml)", 40.0) in advil.strengths_mg_per_ml()


def test_country_ordering(cat):
    es = cat.brands_for("ibuprofen", "ES")
    assert es[0].name in ("Apirofeno", "Dalsy", "Junifen") and "ES" in es[0].countries
    us = cat.brands_for("paracetamol", "US")
    assert "US" in us[0].countries


def test_catalog_matches_calculator_keys(cat):
    for key in cat.drugs:
        assert key in DRUGS
        calculate(key, 10, 24)  # must not raise


def test_drops_strength_without_ml_quantity(cat):
    _, apiretal = cat.resolve("apiretal")
    assert apiretal.strengths_mg_per_ml() == [("gotas 100 mg/ml", 100.0)]
    _, alivium = cat.resolve("alivium")
    assert ("gotas 50 mg/ml", 50.0) in alivium.strengths_mg_per_ml()
