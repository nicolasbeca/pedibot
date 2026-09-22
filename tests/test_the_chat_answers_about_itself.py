"""«¿PediBot guarda las conversaciones?» tiene una respuesta, y no es el folleto (22-sep-2026).

De las 854 preguntas que mandó el operador esa mañana, 220 no eran de salud: eran sobre PediBot
—si entiende hindi, si puede leer un informe, si recuerda lo que le dijiste hace diez minutos, si
puede buscar una farmacia abierta—. Las 220 recibían el mismo párrafo: «PediBot es un servicio
gratuito que contesta dudas sobre la salud de los niños…». Ninguna quedaba contestada.

Se contestan como las de salud: con una ficha de hechos comprobados (`config/sobre_pedibot.md`)
y la regla de siempre —lo que la ficha no dice, no se dice—. Lo que PediBot no puede hacer se
dice claro, que es la mitad de estas preguntas.
"""

from __future__ import annotations

from test_the_ai_reads_the_question_first import _json, _motor

from pedibot.bot.about import ficha_de, responde_sobre
from pedibot.bot.answer import ABOUT_PEDIBOT
from pedibot.bot.interpret import SYSTEM as LECTURA
from pedibot.bot.llm import LLMResult

GUARDA = "Sí: la pregunta y la respuesta se guardan de forma anónima, sin tu IP."


def _con(motor, respuestas: list[str]):  # noqa: ANN001, ANN202
    """El modelo contesta la lectura como siempre y lo que se le diga a la ficha."""
    original = motor.llm.complete
    it = iter(respuestas)
    visto: list[str] = []

    def completa(system, user, **k):  # noqa: ANN001, ANN003, ANN202
        if system == LECTURA:
            return original(system, user, **k)
        if "THE CARD:" in system:
            visto.append(system + " || " + user)
            return LLMResult(next(it), 5, 5, 0.0, "fake")
        raise AssertionError("una pregunta sobre PediBot no debe buscar en las guías")

    motor.llm.complete = completa
    return visto


def test_it_answers_the_question_that_was_asked() -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish", intent="about_pedibot"))
    visto = _con(motor, [GUARDA])
    a = motor.ask("pedibot guarda las conversaciones?", lang="es")
    assert a.text == GUARDA
    assert a.verification == "about"
    # y se le enseñó la ficha, no las guías
    assert "no IP address" in visto[0]
    assert "pedibot guarda las conversaciones" in visto[0]


def test_without_a_model_answer_it_falls_back_to_the_paragraph() -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish", intent="about_pedibot"))
    _con(motor, [""])
    a = motor.ask("que es pedibot?", lang="es")
    assert a.text == ABOUT_PEDIBOT["es"]


def test_the_card_carries_the_real_numbers() -> None:
    f = ficha_de(docs=570, rules=92, countries=91, vax=66)
    assert "570 documents" in f
    assert "92 rules" in f
    assert "{" not in f  # ningún hueco sin rellenar


def test_the_card_says_what_it_cannot_do() -> None:
    f = ficha_de(docs=1, rules=1, countries=1, vax=1)
    for no_puede in ("photographs", "pharmacy", "pregnancy", "reminders"):
        assert no_puede in f


def test_a_model_that_breaks_is_not_an_error() -> None:
    class Roto:
        def complete(self, *a, **k):  # noqa: ANN002, ANN003, ANN201
            raise RuntimeError("boom")

    assert responde_sobre(Roto(), "¿qué es?", "Spanish", "ficha") is None
    assert responde_sobre(None, "¿qué es?", "Spanish", "ficha") is None


def test_asking_the_assistant_what_it_can_do_is_never_off_topic() -> None:
    """«¿Puede decirme dónde está el hospital infantil más cercano?» → «eso no es de PediBot».

    Es la única de las 76 preguntas sobre el servicio que se escapó por la puerta de al lado
    (22-sep-2026). La lectura la vio como «otra cosa», con razón —un hospital cercano no es la
    salud de un niño—, y el texto de fuera de tema la echó sin contestarle lo que preguntaba,
    que es si PediBot sabe hacer eso. No: no sabe. Eso es una respuesta.
    """
    motor, _ = _motor(
        _json(lang="es", lang_name="Spanish", intent="other", query_en="", query_es="", keywords=[])
    )
    llamadas: list[str] = []
    original = motor.llm.complete

    def completa(system, user, **k):  # noqa: ANN001, ANN003, ANN202
        if "THE CARD:" in system:
            llamadas.append(user)
            return LLMResult("No, no puedo buscar un hospital cercano.", 5, 5, 0.0, "fake")
        return original(system, user, **k)

    motor.llm.complete = completa
    a = motor.ask("puede decirme donde esta el hospital infantil mas cercano?", lang="es")
    assert a.verification == "about", a.text
    assert llamadas
