"""El jarabe o las pastillas de un adulto, tomados por un niño, son una intoxicación (9-oct-2026).

Pendiente desde el 5-oct (STATE, «adult cough medicine va a tos ferina»). En inglés ya saltaba la
regla `poisoning` y su pasaje de la SEUP entra en la respuesta; en castellano «se tomó jarabe para
la tos de adulto» salía rutina. La SEUP, hoja de intoxicaciones: los medicamentos son la primera
causa, y la mayoría pasan en casa por un descuido.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage


@pytest.fixture(scope="module")
def triaje() -> Triage:
    from pedibot.eval import fake_engine_from_settings

    return fake_engine_from_settings().triage


SALTA = [
    "mi hijo se tomó jarabe para la tos de adulto",
    "se ha bebido el jarabe de su abuela",
    "la niña se tomó una pastilla de su padre",
    "my toddler drank adult cough medicine",
    "mon fils a bu du sirop pour adultes",
    "meu filho tomou xarope de adulto",
    "mein Sohn hat Hustensaft für Erwachsene getrunken",
]

NO_SALTA = [
    "¿puedo darle a mi hijo jarabe para la tos de adulto?",
    "can I give my 10 year old adult cough medicine",
    "mi hijo se tomó su jarabe para la tos y sigue tosiendo",
]


@pytest.mark.parametrize("texto", SALTA)
def test_it_is_poisoning(triaje: Triage, texto: str) -> None:
    assert "poisoning" in [m.id for m in triaje.assess(texto).matched], texto


@pytest.mark.parametrize("texto", NO_SALTA)
def test_asking_or_their_own_medicine_is_not(triaje: Triage, texto: str) -> None:
    assert "poisoning" not in [m.id for m in triaje.assess(texto).matched], texto
