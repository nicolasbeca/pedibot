"""«Consciencia alterada» es alarma de emergencia, no sólo «inconsciente» (28-sep-2026).

La guía árabe de malaria que se generó el 28-sep pone «اضطراب في الوعي» entre los signos graves que
piden urgencias —es el «impaired consciousness» de la malaria grave de la OMS y el CDC— y el
triaje lo dejaba en rutina. No era cosa del árabe: ninguna lengua conocía la consciencia
ALTERADA, sólo la PERDIDA. Un niño con fiebre que no está del todo presente es el que más prisa
corre, y es justo el que un padre describe así.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]

FRASES = [
    "tiene fiebre y una alteración de la consciencia",
    "con fiebre y el nivel de conciencia disminuido",
    "fever and impaired consciousness",
    "high fever with altered level of consciousness",
    "fièvre et troubles de la conscience",
    "Fieber und eine Bewusstseinsstörung",
    "температура и нарушение сознания",
    "حمى مع اضطراب في الوعي",
    "حمى وتغير في مستوى الوعي",
    "febre e alteração da consciência",
    "बुखार और चेतना में बदलाव",
]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


@pytest.mark.parametrize("frase", FRASES)
def test_altered_consciousness_is_an_emergency(triage: Triage, frase: str) -> None:
    r = triage.assess(frase)
    assert "not_responding" in [m.id for m in r.matched], (frase, r.level)
