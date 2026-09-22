"""«¿Puedes decirme qué hacer ante una convulsión?» no es una convulsión (22-sep-2026).

En la batería de 854 preguntas del operador había un bloque entero de padres preguntando al chat
qué sabe hacer: «puede explicarme qué hacer si un niño se atraganta?», «puede decirme qué hacer
ante una quemadura?», «puede explicarme la diferencia entre arcada y atragantamiento?». El
triaje las leía como el caso en curso y las coronaba con «llama a una ambulancia ahora».

Un padre que pregunta en frío, un martes por la tarde, y recibe una ambulancia, aprende dos
cosas: que el aviso no significa nada, y que este sitio no sabe distinguir. La segunda se
arregla aquí; la primera no se arregla nunca.

Lo que NO puede pasar: que «¿me ayudas? mi hijo se ha atragantado con una uva» se calle. Por eso
hace falta la construcción entera —preguntarle al chat Y hablar en general— y no basta con
preguntarle al chat.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT

TRIAJE = Triage(ROOT / "config" / "red_flags.yaml")

EN_FRIO = [
    "puede decirme que hacer ante una convulsion?",
    "puede explicarme que hacer si un niño se atraganta?",
    "puede explicarme que hacer ante una quemadura?",
    "puede decirme que hacer ante un golpe en la cabeza?",
    "puede decirme si un alimento es peligroso por atragantamiento?",
    "puede explicarme diferencia entre arcada y atragantamiento?",
    "puede ayudarme si mi hijo se autolesiona durante una rabieta?",
    'que pasa si escribo solo "fiebre 39 bebe 5 meses"?',
    "can you tell me what to do if a child chokes?",
    "können Sie mir erklären, was man bei einem Krampfanfall macht?",
]

DE_VERDAD = [
    "ayudame, mi hijo se ha atragantado con una uva y no puede respirar",
    "puedes ayudarme? mi bebe esta convulsionando ahora mismo",
    "mi hijo se ha quemado con aceite hirviendo, que hago",
]


@pytest.mark.parametrize("q", EN_FRIO)
def test_asking_the_chat_what_it_would_do_is_not_an_alarm(q: str) -> None:
    assert TRIAJE.assess(q).level == "routine", q


@pytest.mark.parametrize("q", DE_VERDAD)
def test_a_real_one_still_rings(q: str) -> None:
    assert TRIAJE.assess(q).level in ("urgent", "emergency"), q
