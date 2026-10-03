"""El redactor sabe que hay un aviso encima de su texto (3-oct-2026).

Comprobado en vivo: «le cuesta respirar pero no mucho y solo cuando llora» → cartel «llama
ahora al 112» y, debajo, «consulta en urgencias si aparece dificultad para respirar de verdad».
Desde la v6 el redactor no recibe el nivel —para que no repita la urgencia—, así que no sabía que
arriba ya se decía «ahora». Se le dice que el aviso está y qué dice, sin pedirle que lo repita.

Se probó antes que lo mirase el revisor (`softens_warning`): marcaba 162 de 315 respuestas con
aviso y la reescritura seguía con condicionales. Descartado.
"""

from __future__ import annotations

import pytest

from pedibot.eval import fake_engine_from_settings

NOTA = "WARNING ALREADY SHOWN ABOVE YOUR TEXT"


@pytest.fixture(scope="module")
def engine():
    return fake_engine_from_settings()


def _redactor(engine) -> list[str]:
    return [u for _, u in engine.llm.calls if "PARENT MESSAGE:" in u]


def test_under_a_warning_the_writer_is_told(engine):
    engine.llm.calls.clear()
    engine.ask("le cuesta respirar pero no mucho y solo cuando llora", country="ES", lang="es")
    r = _redactor(engine)
    assert r and NOTA in r[0]


def test_the_note_says_which_warning(engine):
    engine.llm.calls.clear()
    engine.ask("le cuesta respirar pero no mucho y solo cuando llora", country="ES", lang="es")
    assert "breathing" in _redactor(engine)[0].split(NOTA)[1][:300].lower()


def test_without_a_warning_there_is_no_note(engine):
    engine.llm.calls.clear()
    engine.ask("my child has a mild cough", country="GB", lang="en")
    assert not any(NOTA in u for u in _redactor(engine))
