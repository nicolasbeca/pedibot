"""El punto de «39.5» no termina la frase (8-oct-2026).

Casi todas las reglas separan sus dos mitades con `[^.]{0,N}`, para que una alarma no se arme con
palabras de dos frases distintas. Pero el punto decimal también es un punto: «fever of 39.5 and
his hands and feet are cold» salía como rutina, y con 39 a secas, urgente. Lo encontró la batería
del 7-oct en árabe («حرارة 39.5 واطرافه باردة»). En EE. UU. todas las temperaturas llevan punto
(«102.5»), así que el agujero era sobre todo inglés.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage


@pytest.fixture(scope="module")
def triage(config_dir) -> Triage:
    return Triage(config_dir / "red_flags.yaml")


@pytest.mark.parametrize(
    "text",
    [
        "ولدي عمره 3 سنوات عنده حرارة 39.5 واطرافه باردة",
        "my son has a fever of 39.5 and his hands and feet are cold",
        "fever 102.5 and cold hands and feet",
        "mi hijo tiene 39.5 de fiebre y los pies fríos",
        "il a 39.5 de fièvre et les mains froides",
        "er hat 39.5 Fieber und kalte Hände",
    ],
)
def test_a_decimal_temperature_does_not_hide_cold_hands(triage, text):
    t = triage.assess(text)
    assert "cold_extremities_with_fever" in [r.id for r in t.matched], text


def test_a_real_full_stop_still_separates_sentences(triage):
    # el candado sigue: dos frases de cosas distintas no arman la alarma
    t = triage.assess("He had a fever last week. Today his hands are cold from playing outside.")
    assert "cold_extremities_with_fever" not in [r.id for r in t.matched]


def test_the_temperature_itself_still_reads(triage):
    # los patrones de 41-42 °C aceptan [.,]; con la coma siguen saltando
    t = triage.assess("my son has a fever of 41.5")
    assert "very_high_fever" in [r.id for r in t.matched]
    assert triage.assess("my baby has 38.5 fever").has_fever


def test_the_ai_reader_sees_the_same_words(triage):
    # `matched_words` es lo que se enseña a la IA que confirma las alarmas; tiene que ver la
    # misma coincidencia que `assess`, o la regla le llega sin palabras
    w = triage.matched_words("my son has a fever of 39.5 and his hands and feet are cold")
    assert "cold_extremities_with_fever" in w
