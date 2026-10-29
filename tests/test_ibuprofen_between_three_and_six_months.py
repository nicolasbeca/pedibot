"""Ibuprofeno entre los 3 y los 6 meses: las guías no coinciden y se dicen las dos (29-oct-2026).

Prueba mía del 29-oct, antes de citar la lactancia en un correo: «¿Puedo dar ibuprofeno a mi bebé
de 4 meses si sigo dando el pecho? Tiene fiebre» recibió «No, no le des ibuprofeno a un bebé de 4
meses: la AEPap indica que no se puede dar si el niño tiene menos de 3 meses o menos de 5 kg». La
AEPap dice justo lo contrario para un bebé de 4 meses, y la calculadora de dosis (min_age_months=3,
min_weight_kg=5) sí le da cifra. La línea de edad mandaba «Do not suggest ibuprofen» por debajo de
6 meses, que es lo que dice MedlinePlus; el NHS y la AEPap lo permiten desde 3 meses y 5 kg. Ante
una discrepancia no se elige por el padre (bot/guides_differ.py): se nombra a cada organización.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import _age_context
from pedibot.bot.dose import IBUPROFENO
from pedibot.bot.triage import TriageResult


def _linea(meses: float) -> str:
    return _age_context(TriageResult("routine", [], meses, True))


@pytest.mark.parametrize("meses", [3, 4, 5.5])
def test_both_positions_are_named(meses: float) -> None:
    linea = _linea(meses)
    assert "NHS" in linea and "AEPap" in linea and "MedlinePlus" in linea
    assert "3 months" in linea and "5 kg" in linea and "6 months" in linea
    assert "do not decide for the parent" in linea


@pytest.mark.parametrize("meses", [3, 4, 5.5])
def test_the_three_month_limit_is_not_a_reason_to_refuse(meses: float) -> None:
    assert "Never present the 3-month limit" in _linea(meses)


def test_the_calculator_and_the_chat_use_the_same_limit() -> None:
    # Si la ficha de la calculadora cambia, la línea de edad tiene que cambiar con ella.
    assert IBUPROFENO.min_age_months == 3 and IBUPROFENO.min_weight_kg == 5


@pytest.mark.parametrize("meses", [1, 2.5])
def test_under_three_months_still_gets_no_medication(meses: float) -> None:
    linea = _linea(meses)
    assert "UNDER 3 MONTHS" in linea and "MedlinePlus" not in linea


@pytest.mark.parametrize("meses", [7, 30])
def test_older_children_do_not_get_the_note(meses: float) -> None:
    assert "MedlinePlus" not in _linea(meses)
