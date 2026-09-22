"""Si en la pregunta hay un hijo, la pregunta es de PediBot (22-sep-2026).

De la batería de 854, cinco preguntas de crianza recibieron «eso se sale de lo que hace
PediBot»: «mi hija tiene miedo después de ver un vídeo de monstruos», «mi hijo se pone nervioso
si no tiene wifi», «mi hija llora cuando se acaba la batería del móvil», «mi hijo de 3 años
quiere dormir con el teléfono», «mi hijo pide buscar cosas en internet que no debería ver». Las
cinco son de crianza y de sueño, que es de lo que más se pregunta.

El texto de «fuera de tema» se escribió para el perro que come chocolate y para la bechamel, y
ésos no nombran a ningún niño. Así que la regla es esa misma: si la pregunta habla de un hijo,
de una hija, de un bebé o de un niño, no se le dice que no es de aquí. Como mucho, no habrá
fuente — y eso ya tiene su propia respuesta, que es honesta y no echa a nadie.
"""

from __future__ import annotations

import pytest
from test_the_ai_reads_the_question_first import _json, _motor

#: La lectura que hace la IA de algo que, para ella, no va de salud: sin frase médica que
#: buscar, que es justo lo que llega a la rama de «fuera de tema».
_FUERA = _json(
    lang="es", lang_name="Spanish", intent="other", query_en="", query_es="", keywords=[]
)

CON_HIJO = [
    "mi hija tiene miedo despues de ver un video de monstruos",
    "mi hijo se pone nervioso si no tiene wifi",
    "mi hija llora cuando se acaba la bateria del movil",
    "mi hijo de 3 años quiere dormir con el telefono",
    "mi hijo pide buscar cosas en internet que no deberia ver",
]

SIN_HIJO = [
    "como se hace una bechamel?",
    "mi perro puede comer chocolate?",
]


@pytest.mark.parametrize("q", CON_HIJO)
def test_a_question_about_a_child_is_not_sent_away(q: str) -> None:
    motor, _ = _motor(_FUERA)
    a = motor.ask(q, lang="es")
    assert a.verification != "off_topic", a.text


@pytest.mark.parametrize("q", SIN_HIJO)
def test_what_really_is_off_topic_still_is(q: str) -> None:
    motor, _ = _motor(_FUERA)
    a = motor.ask(q, lang="es")
    assert a.verification == "off_topic", a.text
