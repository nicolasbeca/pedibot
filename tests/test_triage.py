from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage, parse_age_months


@pytest.fixture(scope="module")
def triage(config_dir) -> Triage:
    return Triage(config_dir / "red_flags.yaml")


@pytest.mark.parametrize(
    "text,months",
    [
        ("mi hijo de 2 meses", 2),
        ("tiene 3 años", 36),
        ("my 5 year old", 60),
        ("18 months old", 18),
        ("recién nacido", 0.5),
        ("newborn baby", 0.5),
        ("tiene 6 semanas", pytest.approx(1.38, abs=0.05)),
        ("3 days old", pytest.approx(0.1, abs=0.05)),
        ("le duele la tripa", None),
        # hasta el 12-sep-2026 esta línea decía 12: la prueba tenía el fallo por bueno
        ("un año y medio", 18),
    ],
)
def test_parse_age(text, months):
    assert parse_age_months(text) == months


# --- must be EMERGENCY ---
@pytest.mark.parametrize(
    "text",
    [
        "mi hijo no responde y está muy pálido",
        "está teniendo una convulsión",
        "my daughter is struggling to breathe and her lips are blue",
        "se le han hinchado los labios y le cuesta respirar",
        "he fell from the bed and was knocked out for a few seconds",
        "tiene manchas en la piel que no desaparecen al presionar",
        "my son is choking on a grape",
        "no para de sangrar la herida",
    ],
)
def test_emergency(triage, text):
    assert triage.assess(text).level == "emergency"


# --- must be URGENT ---
@pytest.mark.parametrize(
    "text",
    [
        "mi bebé de 2 meses tiene fiebre de 38",
        "my 6 week old has a fever",
        "tiene 41 grados",
        "se ha bebido lejía",
        "my toddler swallowed a button battery",
        "se ha dado un golpe en la cabeza y ha vomitado dos veces",
        "lleva 2 días con diarrea, tiene los ojos hundidos y no hace pis",
        "she is very drowsy and hard to wake",
        "mi hijo de 13 años dice que quiere morir",
    ],
)
def test_urgent_or_worse(triage, text):
    assert triage.assess(text).level in ("urgent", "emergency", "mental_health")


def test_mental_health_level(triage):
    r = triage.assess("mi hija se hace cortes en los brazos")
    assert r.level == "mental_health"
    assert r.matched[0].id == "self_harm"


def test_infant_fever_rule_requires_both(triage):
    assert triage.assess("mi bebé de 2 meses está muy contento").level == "routine"
    assert triage.assess("mi hijo de 4 años tiene fiebre de 38,5").level == "routine"
    r = triage.assess("mi bebé de 2 meses tiene 38,2 de fiebre")
    assert r.level == "urgent" and "infant_fever_under_3_months" in [m.id for m in r.matched]


# --- must stay ROUTINE (precision) ---
@pytest.mark.parametrize(
    "text",
    [
        "mi hijo de 3 años tiene mocos y algo de tos",
        "¿cuándo puedo empezar con la alimentación complementaria?",
        "what vaccines does a 4 month old get?",
        "my 2 year old has had a runny nose for two days",
        "le han salido unos granitos que desaparecen al apretar",
        "¿cuánto paracetamol le doy a un niño de 12 kilos?",
        "tiene 38 de fiebre y 4 años, está jugando",
    ],
)
def test_routine(triage, text):
    assert triage.assess(text).level == "routine", triage.assess(text).matched


def test_reasons_language(triage):
    r = triage.assess("está teniendo una convulsión")
    assert r.reasons("es")[0].startswith("Movimientos")
    assert r.reasons("en")[0].startswith("Abnormal")
