"""Con el aviso rojo encima, el texto no manda a esperar en casa (5-oct-2026).

La comprobación ya cazaba «no es urgente» y «es normal». En las baterías con el reparto de las
consultas reales salieron otras formas de rebajar el aviso, que no decían ninguna de esas: «keep
him at home under watch» con un imán tragado, «most cases are mild and can be managed at home»
con un bebé que pita al respirar, «follow up in 5 days» con un bebé que no puede mamar. Con aviso,
un borrador así se reescribe.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import _QUITA_URGENCIA, _MANDA_A_CASA


def _rebaja(t: str) -> bool:
    return bool(_QUITA_URGENCIA.search(t) or _MANDA_A_CASA.search(t))


@pytest.mark.parametrize(
    "texto",
    [
        "Keep him at home under watch and give small sips of water.",
        "Most cases are mild and can be managed at home.",
        "This is usually mild and gets better on its own.",
        "Watch your child at home for the next 24 hours.",
        "Vigílalo en casa durante las próximas horas.",
        "Suele ser leve y se puede tratar en casa.",
        "Follow up with your doctor in 5 days if it does not improve.",
        # 7-oct-2026, las páginas del NHS
        "You can usually look after them at home: give plenty of fluids.",
        "Most sprains can be treated at home without seeing a doctor.",
    ],
)
def test_rebaja(texto: str) -> None:
    assert _rebaja(texto)


@pytest.mark.parametrize(
    "texto",
    [
        "While you wait for help, keep her lying on her side.",
        "Do not give anything by mouth until a doctor has seen him.",
        "Bring the medicine packet with you to the hospital.",
    ],
)
def test_no_rebaja(texto: str) -> None:
    assert not _rebaja(texto)
