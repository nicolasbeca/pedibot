"""«दमा का दौरा» es una crisis de asma, no una convulsión (1-oct-2026).

«दौरा» es «ataque» en general: el de epilepsia (मिर्गी का दौरा), el de asma (दमा का दौरा) y la
circulación de la sangre (ख़ून का दौरा). La regla de convulsión lo tenía suelto, así que «बच्चे को
दमा का दौरा पड़ा» sacaba el aviso rojo de convulsión: a un padre con un niño que no respira bien se
le decía que vigilara movimientos anormales. En inglés y en castellano, la misma frase sin más
datos es rutina, y escala por sus propias reglas (el inhalador que no hace efecto, el pecho que se
hunde). Salió al probar las páginas de Vikaspedia sobre el asma.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import get_settings


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(get_settings().config_dir / "red_flags.yaml")


def _reglas(t: Triage, texto: str) -> set[str]:
    return {r.id for r in t.assess(texto).matched}


@pytest.mark.parametrize(
    "texto",
    [
        "बच्चे को दमा का दौरा पड़ा",
        "मेरे बेटे को दमे का दौरा आया है",
        "बच्चे को अस्थमा का दौरा पड़ा",
        "bachche ko dama ka daura pada",
        "bete ko asthma ka daura aaya",
    ],
)
def test_an_asthma_attack_is_not_a_seizure(triaje: Triage, texto: str) -> None:
    assert "seizure" not in _reglas(triaje, texto)


@pytest.mark.parametrize(
    "texto",
    [
        "बच्चे को दौरा पड़ा",
        "बच्चे को मिर्गी का दौरा पड़ा",
        "उसे दौरे पड़ रहे हैं",
        "bachche ko daura pada",
    ],
)
def test_a_real_seizure_still_raises_the_alarm(triaje: Triage, texto: str) -> None:
    assert "seizure" in _reglas(triaje, texto)
