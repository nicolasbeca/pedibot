"""El revisor de salida sabe dónde vive el lector (3-oct-2026).

La revisión (21-sep) pregunta si la respuesta contesta lo preguntado. «Should I vaccinate my
child polio vaccine?» desde Reino Unido, contestado con el calendario español, lo contestaba: el
revisor no sabía el país. Ahora lo recibe y marca `wrong_country` cuando la respuesta da por
suyos el calendario, los servicios o los números de otro país; eso pide reescribir.
"""

from __future__ import annotations

import json

import pytest

from pedibot.bot.answer import revisa_respuesta
from pedibot.bot.llm import FakeProvider
from pedibot.eval import fake_engine_from_settings

POLIO = "should I vaccinate my child polio vaccine?"


def _con_revisor(dice: dict):
    def responder(system: str, user: str) -> str:
        if system.startswith("You review one answer"):
            return json.dumps(dice)
        return "Grounded draft [1]."

    return FakeProvider(responder)


@pytest.fixture()
def engine():
    return fake_engine_from_settings()


def test_the_reviewer_is_told_the_country(engine):
    engine.llm = _con_revisor({"answers_question": True})
    engine.ask(POLIO, country="GB", lang="en")
    revision = [u for s, u in engine.llm.calls if s.startswith("You review one answer")]
    assert revision and "READER'S COUNTRY: United Kingdom" in revision[0]


def test_a_wrong_country_answer_is_rewritten(engine):
    engine.llm = _con_revisor({"answers_question": True, "wrong_country": True, "note": "UK"})
    engine.ask(POLIO, country="GB", lang="en")
    assert any("A reviewer read your draft" in s for s, _ in engine.llm.calls)


def test_a_right_country_answer_is_not(engine):
    engine.llm = _con_revisor({"answers_question": True, "wrong_country": False})
    engine.ask(POLIO, country="GB", lang="en")
    assert not any("A reviewer read your draft" in s for s, _ in engine.llm.calls)


def test_wrong_country_is_read_strictly():
    r = revisa_respuesta(
        FakeProvider(json.dumps({"wrong_country": "yes"})), "q", "routine", "a", pais="Kenya"
    )
    assert r is not None and not r.pais_ajeno and not r.hay_que_rehacer


def test_without_a_country_the_line_is_not_there():
    llm = FakeProvider(json.dumps({}))
    revisa_respuesta(llm, "q", "routine", "a")
    assert "READER'S COUNTRY" not in llm.calls[0][1]


def test_foreign_medical_advice_is_not_the_wrong_country():
    """5-nov-2026: el revisor marcaba `wrong_country` por citar al NHS en un consejo médico a un
    padre de Kenia o Tanzania, y pedía «una guía tanzana» que no existe; en Nigeria dio por
    europeo el 112, que es el de Nigeria. Medido sobre 74 respuestas guardadas y cuatro
    controles: con la pregunta acotada, los dos falsos positivos desaparecen, los dos casos de
    verdad (calendario español a un británico, «GP surgery» a un keniano) siguen saltando, y las
    reescrituras bajan de 22 a 10. Los números de urgencias los comprueba el código."""
    from pedibot.bot.answer import REVISA

    assert "Medical advice attributed to a" in REVISA
    assert "named foreign health body" in REVISA
    assert "Do not judge emergency" in REVISA
    assert "vaccination schedule" in REVISA
