"""Cinco alarmas de la octava tanda que salían como rutina (29-sep-2026).

Leídas una por una las 42 que el revisor marcó por nivel de urgencia, la mayoría eran ruido —fiebre
de 39 en un niño de ocho meses es rutina según las guías—, pero estas cinco no: cada regla existía
y le faltaba la forma en que lo escribió el padre. El doble ibuprofeno es el caso más claro: quien
se equivoca no sabe que se ha equivocado, así que nunca escribe «por error»; escribe «otro jarabe
que también lleva ibuprofeno».
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


@pytest.mark.parametrize(
    "texto,minimo",
    [
        ("mi bebe tiene mocos y hace pausas al respirar mientras duerme", "emergency"),
        ("hace ruido al respirar incluso estando tranquilo", "emergency"),
        ("le di ibuprofeno y despues otro jarabe que tambien lleva ibuprofeno, pasa algo?", "urgent"),
        ("le di Dalsy y luego Nurofen porque pensaba que eran diferentes", "urgent"),
        ("I gave him Calpol and then another syrup that also contains paracetamol", "urgent"),
        ("el niño tiene menos fiebre pero respira peor", "urgent"),
        ("tiene dos ojos hinchados y acaba de comer algo", "urgent"),
    ],
)
def test_salta(triage, texto, minimo):
    orden = {"routine": 0, "urgent": 1, "emergency": 2}
    nivel = triage.assess(texto).level
    assert orden.get(nivel, 0) >= orden[minimo], f"{texto!r} → {nivel}"


@pytest.mark.parametrize(
    "texto",
    [
        "mi bebe hace ruido al respirar pero solo cuando esta llorando",
        "hace ruido al respirar cuando llora pero no cuando está tranquilo",
        "le di Dalsy hace 8 horas y ahora paracetamol, ¿está bien?",
        "tiene los ojos hinchados de llorar",
        "respira mejor que ayer",
    ],
)
def test_no_salta(triage, texto):
    assert triage.assess(texto).level == "routine", texto
