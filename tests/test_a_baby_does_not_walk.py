"""Un bebé no habla ni anda: lo que sólo vale para niños mayores sobra (26-oct-2026).

Consulta real 1074 (Brasil): «Caiu do sofá e vomitou duas vezes», con 2 meses y 4,5 kg puestos en
el formulario. El aviso estaba bien (urgencias hoy), pero el texto mandaba vigilar si tenía
«dificuldade para falar ou andar» y «visão dupla» (la lista de conmoción de los CDC, escrita para
niños que hablan) y guardar «repouso físico e mental, sem atividades intensas» (la vuelta al cole
de la SEUP). La regla 7c del prompt ya pedía quitar lo que no puede aplicarse a esta edad; con la
edad dicha en número, el redactor no lo hacía. La línea de edad lo dice ahora con palabras.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import _age_context
from pedibot.bot.triage import TriageResult


def _linea(meses: float, nivel: str = "urgent") -> str:
    return _age_context(TriageResult(nivel, [], meses, False))


@pytest.mark.parametrize("meses", [0.5, 2, 5, 11])
def test_under_one_the_writer_is_told_what_a_baby_cannot_do(meses: float) -> None:
    linea = _linea(meses)
    assert "cannot yet talk or walk" in linea
    assert "school" in linea and "physical activity" in linea


@pytest.mark.parametrize("meses", [2, 5])
def test_the_under_three_and_under_six_rules_stay(meses: float) -> None:
    linea = _linea(meses)
    assert ("UNDER 3 MONTHS" in linea) if meses < 3 else ("under 6 months" in linea)


@pytest.mark.parametrize("meses", [14, 48])
def test_a_toddler_is_not_told_that(meses: float) -> None:
    assert "cannot yet talk or walk" not in _linea(meses)
