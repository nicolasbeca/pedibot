"""«Problemas respiratórios graves»: la dificultad grave dicha con sustantivo (20-oct-2026).

La guía portuguesa del asma, generada el 19-oct, manda a buscar ayuda «imediatamente» ante
«problemas respiratórios graves», y el triaje lo leía como rutina; el candado de las guías
(`test_guides_agree_with_triage`) lo cazó. Mirado en las demás lenguas, la forma con sustantivo
y adjetivo de gravedad sólo saltaba en inglés: «dificuldade respiratória grave» y «graves
problemas respiratorios» también salían rutina. Es como lo escriben una guía y un padre que lo
ha leído en un informe.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.triage import Triage

ROOT = Path(__file__).resolve().parents[1]

GRAVES = [
    "problemas respiratórios graves",
    "meu filho tem dificuldade respiratória grave",
    "ela está com desconforto respiratório grave",
    "mi hijo tiene problemas respiratorios graves",
    "tiene una dificultad respiratoria grave",
    "graves problemas respiratorios",
    "mon fils a des problèmes respiratoires graves",
    "difficultés respiratoires sévères",
    "mein Kind hat schwere Atemnot",
    "starke Atemprobleme seit heute Nacht",
    "severe breathing problems",
]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


@pytest.mark.parametrize("frase", GRAVES)
def test_severe_breathing_said_as_a_noun_is_an_emergency(triage: Triage, frase: str) -> None:
    assert triage.assess(frase).level == "emergency", frase


@pytest.mark.parametrize(
    "frase",
    [
        "não tem problemas respiratórios graves",
        "no tiene problemas respiratorios graves, solo mocos",
    ],
)
def test_denied_it_is_not(triage: Triage, frase: str) -> None:
    assert triage.assess(frase).level != "emergency", frase
