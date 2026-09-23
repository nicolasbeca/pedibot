"""Las frases de los padres del 22-sep-2026, sacadas del registro (23-sep-2026).

Diecisiete consultas reales en un día, y una de ellas se fue sin aviso:

    «es asmatico y le esta costando respirar»

`le cuesta respirar` estaba en la regla desde el principio; `le está costando respirar` no. La
misma frase, con la perífrasis que usa media España, y el aviso no salió. La respuesta redactada
sí hablaba de acudir a un centro sanitario —eso salvó la consulta— pero el cartel rojo con el
número de emergencias no estaba, y es lo único que se lee a la primera.

Van también las otras formas de decirlo que un padre escribe de corrido.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT

TRIAJE = Triage(ROOT / "config" / "red_flags.yaml")

ASI_LO_DICEN = [
    "es asmatico y le esta costando respirar",
    "le está costando respirar desde esta tarde",
    "está costándole respirar",
    "le cuesta trabajo respirar",
    "mi hija está teniendo dificultad para respirar",
    "he is having trouble breathing",
    "he's having a hard time breathing",
    "elle a du mal à respirer depuis ce soir",
    "er bekommt schwer Luft",
]


@pytest.mark.parametrize("q", ASI_LO_DICEN)
def test_it_rings(q: str) -> None:
    assert TRIAJE.assess(q).level in ("urgent", "emergency"), q


def test_asking_in_the_cold_still_does_not_ring() -> None:
    """Y la pregunta en frío sigue sin sacar una ambulancia (22-sep-2026)."""
    assert (
        TRIAJE.assess("puede explicarme qué hacer si a un niño le cuesta respirar?").level
        == "routine"
    )
