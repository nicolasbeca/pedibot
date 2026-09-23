"""«Tengo fiebre, pero la pregunta es sobre mí, no sobre mi hijo» (23-sep-2026).

De la octava tanda. La respuesta empezó por «si el niño tiene menos de 3 meses…» y siguió con la
fiebre infantil, a alguien que acababa de decir, con todas las letras, que no preguntaba por un
niño. La ficha lo dice claro —PediBot no es para adultos— y el chat lo contesta bien cuando le
preguntan en abstracto («¿sirves para adultos?»); lo que fallaba es el caso con síntoma dentro,
que es como llega de verdad.

Va con el perro, que es el mismo caso por la otra punta: «mi perro tiene diarrea, ¿qué le doy?»
recibía «no tengo información fiable en mis fuentes» en vez de un no amable.
"""

from __future__ import annotations

import pytest
from test_the_ai_reads_the_question_first import _json, _motor

NO_ES_UN_NIÑO = [
    "tengo fiebre, pero la pregunta es sobre mí, no sobre mi hijo",
    "la consulta es para mí, no para el niño: llevo dos días con diarrea",
    "soy yo el que tiene el dolor de garganta, no mi hija",
    "mi perro tiene diarrea, ¿qué le doy?",
    "mi gato ha vomitado tres veces, que hago?",
]


@pytest.mark.parametrize("q", NO_ES_UN_NIÑO)
def test_it_says_no_instead_of_answering_about_a_child(q: str) -> None:
    from pedibot.bot.answer import OFF_TOPIC

    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    a = motor.ask(q, lang="es")
    assert a.verification == "off_topic", a.text
    assert a.text == OFF_TOPIC["es"]


def test_a_child_with_the_same_words_is_untouched() -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    for q in (
        "mi hijo tiene fiebre desde ayer",
        "tengo un bebé de 3 meses con fiebre",
        "me preocupa mi hija, tiene diarrea",
    ):
        a = motor.ask(q, lang="es")
        assert a.verification != "off_topic", q
