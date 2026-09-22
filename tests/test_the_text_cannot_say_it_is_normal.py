"""Bajo un aviso rojo, «es normal» es tan contradictorio como «no es urgente» (22-sep-2026).

L222 dejó escrito que el texto no puede quitarle la razón al aviso, y el detector se escribió
con las formas de entonces: «no es urgente», «no es grave», «no es peligroso». La revisión de
las 854 respuestas encontró las otras cuatro maneras de decir lo mismo, todas debajo de un
«hay que acudir a urgencias hoy»:

    «tener las manos y los pies fríos con fiebre es NORMAL»
    «si ha chupado una moneda pero no la ha tragado, NO HAY INGESTIÓN»
    «NO HAY NINGÚN MOTIVO DE ALARMA por esa tos si el niño está bien»
    «NO HAY PROBLEMA si el color vuelve a la normalidad»

Un padre que lee el aviso y luego eso no sabe qué hacer, y lo que decide en esa duda es lo que
el aviso existía para evitar.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import _QUITA_URGENCIA

CONTRADICEN = [
    "tener las manos y los pies fríos con fiebre es normal, según la SEUP",
    "no hay ningún motivo de alarma por esa tos si el niño está bien",
    "si no la ha tragado, no hay ingestión y no hace falta nada más",
    "no hay problema si el color vuelve a la normalidad",
    "es algo habitual y no requiere hacer nada",
    "this is normal in babies and nothing needs to be done",
    "there is no cause for alarm if he is otherwise well",
    "c'est normal et il n'y a pas lieu de s'inquiéter",
    "das ist normal und kein Grund zur Sorge",
    "это нормально и нет повода для беспокойства",
]

NO_CONTRADICEN = [
    "la fiebre es una señal de que el cuerpo se está defendiendo, según la SEUP",
    "las cacas del bebé cambian mucho en las primeras semanas",
    "haz ahora lo que dice el aviso de arriba",
    "conviene vigilar si le cuesta respirar o se le hunde el pecho",
    "es normal que no tenga apetito, pero con estos síntomas hay que acudir hoy",
]


@pytest.mark.parametrize("t", CONTRADICEN)
def test_it_is_caught(t: str) -> None:
    assert _QUITA_URGENCIA.search(t), t


@pytest.mark.parametrize("t", NO_CONTRADICEN)
def test_a_normal_sentence_is_left_alone(t: str) -> None:
    assert not _QUITA_URGENCIA.search(t), t
