from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pedibot.bot.dose import DoseError, calculate, format_result


def test_paracetamol_10kg():
    r = calculate("paracetamol", 10)
    assert (r.mg_min, r.mg_max) == (100, 150)
    assert r.ml["gotas 100 mg/ml"] == (1.0, 1.5)
    assert r.ml["jarabe 120 mg/5 ml"] == (4.2, 6.2)
    assert r.interval_hours == (4, 6)
    assert r.max_doses_per_day == 4  # 60 mg/kg/day / 15 mg/kg
    assert not r.refer and r.warnings == []


def test_ibuprofen_20kg():
    r = calculate("ibuprofen", 20, age_months=48)
    assert (r.mg_min, r.mg_max) == (100, 200)
    assert r.ml["jarabe 2 % (100 mg/5 ml)"] == (5.0, 10.0)
    assert r.ml["jarabe 4 % (200 mg/5 ml)"] == (2.5, 5.0)
    assert r.max_doses_per_day == 3


def test_ibuprofen_under_3_months_refers():
    r = calculate("ibuprofeno", 4.5, age_months=2)
    assert r.refer and "under_3_months_refer" in r.warnings and "below_min_weight" in r.warnings


def test_paracetamol_under_3_months_refers_even_if_allowed():
    r = calculate("paracetamol", 4, age_months=1)
    assert r.refer


def test_single_dose_cap_applies_to_big_children():
    r = calculate("paracetamol", 80)
    assert r.mg_max == 1000 and "capped_single_dose" in r.warnings
    r2 = calculate("ibuprofen", 50, age_months=150)
    assert r2.mg_max == 400


def test_unknown_drug_and_bad_weight():
    with pytest.raises(DoseError):
        calculate("amoxicilina", 10)
    with pytest.raises(DoseError):
        calculate("paracetamol", 0.5)


@given(
    st.floats(min_value=1, max_value=120),
    st.one_of(st.none(), st.floats(min_value=0, max_value=216)),
)
def test_never_exceeds_hard_caps(kg, months):
    for drug in ("paracetamol", "ibuprofen"):
        r = calculate(drug, kg, months)
        assert r.mg_max <= r.drug.max_single_dose_mg
        assert r.mg_max * r.max_doses_per_day <= r.drug.max_daily_mg + 1e-6
        assert (
            r.mg_max * r.max_doses_per_day <= r.drug.max_mg_per_kg_day * kg + r.mg_max
        )  # integer floor slack
        assert r.mg_min <= r.mg_max


def test_format_mentions_source_and_check(capsys):
    out = format_result(calculate("paracetamol", 12), "es")
    assert "AEPap" in out and "Comprueba" in out
    out_en = format_result(calculate("paracetamol", 12), "en")
    assert "Source:" in out_en
