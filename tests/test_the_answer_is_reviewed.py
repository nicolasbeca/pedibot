"""Una lectura de revisión antes de que el padre vea la respuesta (21-sep-2026).

Revisando 300 respuestas, lo que más fallaba no era el triaje sino la puntería: «a mi bebé le
tiembla la barbilla cuando llora» contestado con los cólicos, «¿le faltan vitaminas?» con el
sarampión, y veredictos que ninguna fuente daba («no hay ningún problema en que siga con el
biberón»). La revisión pregunta tres cosas y, si algo falla, pide un reintento con la nota.
"""

from __future__ import annotations

import json

from test_the_ai_reads_the_question_first import _json, _motor

from pedibot.bot.answer import REVISA, revisa_respuesta
from pedibot.bot.interpret import SYSTEM as LECTURA
from pedibot.bot.llm import LLMResult

BUENO = "El temblor de la barbilla al llorar es frecuente en recién nacidos, según el NHS [1]."
MALO = "Los cólicos son episodios de llanto intenso, según el NHS [1]."


def _con(motor, borradores: list[str], revisiones: list[dict]):  # noqa: ANN001, ANN202
    original = motor.llm.complete
    it_b, it_r = iter(borradores), iter(revisiones)
    llamadas: list[str] = []

    def completa(system, user, **k):  # noqa: ANN001, ANN003, ANN202
        if system == LECTURA:
            return original(system, user, **k)
        if system == REVISA:
            llamadas.append("revisa")
            return LLMResult(json.dumps(next(it_r)), 5, 5, 0.0, "fake")
        llamadas.append("redacta")
        return LLMResult(next(it_b), 5, 5, 0.0, "fake")

    motor.llm.complete = completa
    return llamadas


def test_an_answer_about_something_else_is_redone() -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    llamadas = _con(
        motor,
        [MALO, BUENO],
        [{"answers_question": False, "padding": True, "note": "It talks about colic."}],
    )
    a = motor.ask("a mi recién nacido le tiembla la barbilla cuando llora", lang="es")
    assert a.text.startswith("El temblor")
    assert llamadas == ["redacta", "revisa", "redacta"]


def test_if_the_redo_still_misses_it_is_no_source() -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    _con(
        motor,
        [MALO, "No hay ningún dato sobre esto. Los cólicos, según el NHS [1], son llanto."],
        [{"answers_question": False, "padding": True, "note": "Off topic."}],
    )
    a = motor.ask("a mi recién nacido le tiembla la barbilla cuando llora", lang="es")
    assert a.verification == "no_source"


def test_a_good_answer_passes_untouched() -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    llamadas = _con(motor, [BUENO], [{"answers_question": True, "padding": False}])
    a = motor.ask("a mi recién nacido le tiembla la barbilla cuando llora", lang="es")
    assert a.text.startswith("El temblor")
    assert llamadas == ["redacta", "revisa"]


def test_a_broken_review_changes_nothing() -> None:
    class Rota:
        def complete(self, *a, **k):  # noqa: ANN002, ANN003, ANN202
            return LLMResult("no es json", 1, 1, 0.0, "fake")

    assert revisa_respuesta(Rota(), "x", "routine", BUENO) is None
    assert revisa_respuesta(None, "x", "routine", BUENO) is None
