"""Si la primera búsqueda no contesta, una segunda con las palabras de la IA (21-sep-2026).

«¿Cuándo puedo darle una chuleta a mi hijo?», «¿y una salchicha?», «¿y cacahuetes?»: las tres
«no tengo información», con las guías de alimentación complementaria en el corpus. El padre dice
«chuleta»; la guía, «carne».
"""

from __future__ import annotations

from test_the_ai_reads_the_question_first import _json, _motor

from pedibot.bot.interpret import SYSTEM as LECTURA

CHULETA = "¿Cuándo puedo darle una chuleta a mi hijo?"
LEIDA = _json(
    lang="es",
    lang_name="Spanish",
    query_en="When can a baby start eating meat in complementary feeding?",
    query_es="¿Cuándo puede un bebé empezar a comer carne en la alimentación complementaria?",
    keywords=["meat", "carne", "alimentación complementaria"],
)


def _con_borradores(motor, borradores: list[str]) -> list[str]:  # noqa: ANN001
    """Cambia el redactor por uno que contesta, en orden, los borradores dados."""
    original = motor.llm.complete
    pedidos: list[str] = []

    def completa(system, user, **k):  # noqa: ANN001, ANN003, ANN202
        if system == LECTURA:
            return original(system, user, **k)
        pedidos.append(user)
        r = original(system, user, **k)
        r.text = borradores[min(len(pedidos), len(borradores)) - 1]
        return r

    motor.llm.complete = completa
    return pedidos


def test_no_source_first_then_the_ai_words_find_it() -> None:
    motor, visto = _motor(LEIDA)
    pedidos = _con_borradores(motor, ["NO_SOURCE", "Most fevers get better, says the NHS [1]."])
    a = motor.ask(CHULETA, lang="es")
    assert len(visto["busquedas"]) == 2
    assert "carne" in visto["busquedas"][1][0]
    assert len(pedidos) == 2
    assert a.verification != "no_source"


def test_an_answer_found_first_time_is_not_searched_again() -> None:
    motor, visto = _motor(LEIDA)
    _con_borradores(motor, ["Most fevers get better in a few days, according to the NHS [1]."])
    motor.ask(CHULETA, lang="es")
    assert len(visto["busquedas"]) == 1


def test_only_one_second_try() -> None:
    motor, visto = _motor(LEIDA)
    _con_borradores(motor, ["NO_SOURCE"])
    a = motor.ask(CHULETA, lang="es")
    assert len(visto["busquedas"]) == 2
    assert a.verification == "no_source"


def test_without_a_reading_there_is_no_second_search() -> None:
    motor, visto = _motor(None)
    _con_borradores(motor, ["NO_SOURCE"])
    motor.ask("mi hijo tiene fiebre desde ayer", lang="es")
    assert len(visto["busquedas"]) == 1
