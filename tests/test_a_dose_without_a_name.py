"""«Pesa 16 kg y el bote dice 100mg/5ml, ¿cuánto le toca?» (22-sep-2026).

Esa pregunta llegó en la batería del operador y se contestó con «no tengo información fiable
sobre esto en mis fuentes». Es la peor respuesta posible: el padre tiene el bote en la mano, el
niño delante, y lo único que falta es una palabra —cuál de los dos medicamentos es—. La
calculadora de PediBot sabe hacer exactamente eso en cuanto la tenga.

Y no se puede adivinar. 100 mg/5 ml es la concentración habitual del ibuprofeno infantil y
también existe en paracetamol; elegir uno por el padre es lo único que aquí no se puede hacer.
Así que se le pregunta, en una línea, y se le dice que con el nombre ya está.
"""

from __future__ import annotations

import pytest
from test_the_ai_reads_the_question_first import _json, _motor

CON_PESO_SIN_NOMBRE = [
    "mi hijo pesa 16 kg y el bote dice 100mg/5ml, cuanto le toca?",
    "que dosis le doy a un niño de 12 kg?",
    "cuanto jarabe le toca si pesa 9,5 kg",
]

NO_ES = [
    "mi hijo pesa 16 kg, cuanto paracetamol le doy?",
    "mi bebe pesa 7 kg y tiene fiebre desde ayer",
]


@pytest.mark.parametrize("q", CON_PESO_SIN_NOMBRE)
def test_it_asks_which_medicine(q: str) -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    a = motor.ask(q, lang="es")
    assert a.verification == "which_drug", a.text
    assert "paracetamol" in a.text.lower() and "ibuprofeno" in a.text.lower()


@pytest.mark.parametrize("q", NO_ES)
def test_a_question_that_is_not_that_is_left_alone(q: str) -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    a = motor.ask(q, lang="es")
    assert a.verification != "which_drug"
