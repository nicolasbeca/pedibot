from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pedibot.bot.dose import DoseError, calculate, format_result


def test_paracetamol_10kg():
    r = calculate("paracetamol", 10)
    # one figure to act on: 15 mg/kg, which is what the published 60 mg/kg/day is built from
    assert r.mg == 150
    assert r.ml["gotas 100 mg/ml"] == 1.5
    assert r.ml["jarabe 120 mg/5 ml"] == 6.2
    # and the band the guide publishes, kept visible rather than hidden
    assert (r.mg_min, r.mg_max) == (100, 150)
    assert r.ml_band["gotas 100 mg/ml"] == (1.0, 1.5)
    assert r.interval_hours == (4, 6)
    assert r.max_doses_per_day == 4  # 60 mg/kg/day / 15 mg/kg
    assert not r.refer and r.warnings == []


def test_ibuprofen_20kg():
    r = calculate("ibuprofen", 20, age_months=48)
    assert r.mg == 200  # 10 mg/kg, the figure behind the 30 mg/kg/day cap
    assert r.ml["jarabe 2 % (100 mg/5 ml)"] == 10.0
    assert r.ml["jarabe 4 % (200 mg/5 ml)"] == 5.0
    assert (r.mg_min, r.mg_max) == (100, 200)
    assert r.max_doses_per_day == 3


def test_the_dose_shown_is_a_number_a_syringe_can_measure() -> None:
    """It used to print the mg/kg band — "3–6 ml" — which at three in the morning is the same as
    nothing, and which no manufacturer's leaflet does. Dalsy tells a 12 kg child 6 ml."""
    r = calculate("ibuprofeno", 12)
    assert r.ml["jarabe 2 % (100 mg/5 ml)"] == 6.0
    for millilitres in r.ml.values():
        assert isinstance(millilitres, float), "una dosis es un número, no una banda"


def test_millilitres_round_down_and_never_above_the_dose() -> None:
    """Rounding to the nearest tenth can put the volume above the milligrams it came from. On the
    one page where a number is an instruction, err downwards."""
    for kg in range(5, 41):
        for drug in ("paracetamol", "ibuprofeno"):
            r = calculate(drug, kg)
            for name, millilitres in r.ml.items():
                strength = next(p.mg_per_ml for p in r.drug.presentations if p.name == name)
                assert millilitres * strength <= r.mg + 1e-9, f"{drug} {kg}kg {name}: se pasa"
                assert round(millilitres * 10) == millilitres * 10, "más fino que 0,1 ml"


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
