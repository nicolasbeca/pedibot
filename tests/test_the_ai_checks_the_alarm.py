"""La IA que lee la pregunta confirma también la alarma de las reglas (3-oct-2026).

Consulta real, Reino Unido, 2-oct: «what are the side effects of HPV vaccine… risks as well as
benefits» → «🚨 Call 999 — seizure». La regla «fits» casaba dentro de «bene-fits». Ese patrón se
arregló el mismo día, pero el operador preguntó lo que tocaba: ¿no hay una IA leyendo las
preguntas? La había, y por diseño (21-sep) sólo podía AÑADIR alarmas, nunca quitarlas.

Ahora las reglas corren antes de la lectura (son instantáneas) y, si saltan, la misma llamada
dice si el mensaje habla de verdad de esa situación. Sin llamada nueva ni espera nueva. Una
alarma sólo se quita con un `false` explícito; la duda, un JSON roto o un modelo caído la
dejan como estaba.
"""

from __future__ import annotations

import json

import pytest

from pedibot.bot.interpret import interpret
from pedibot.bot.llm import FakeProvider
from pedibot.eval import fake_engine_from_settings

SEIZURE = "my son is having a seizure right now"


def _lector(veredicto: object):
    """Un modelo falso: a la lectura le contesta con `veredicto` para cada alarma."""

    def responder(system: str, user: str) -> str:
        if not system.startswith("You read a parent's message"):
            return "Grounded draft [1]."
        ids = [ln.split(":")[0].strip("- ").strip() for ln in user.splitlines() if ln.startswith("- ")]
        alarms = {i: veredicto for i in ids} if "KEYWORD WARNINGS" in user else None
        return json.dumps(
            {
                "lang": "en",
                "lang_name": "English",
                "intent": "health",
                "requested_lang": None,
                "requested_name": None,
                "query_en": user[-200:],
                "query_es": "",
                "keywords": [],
                "new_topic": None,
                "vague": False,
                "alarms": alarms,
            }
        )

    return FakeProvider(responder)


@pytest.fixture()
def engine():
    return fake_engine_from_settings()


def test_the_reading_is_told_which_alarm_fired(engine):
    engine.llm = _lector(True)
    engine.ask(SEIZURE, country="GB", lang="en")
    lectura = [u for s, u in engine.llm.calls if s.startswith("You read a parent's message")]
    assert lectura and "KEYWORD WARNINGS" in lectura[0]
    assert "seizure" in lectura[0].lower()


def test_an_alarm_the_reading_rejects_is_dropped(engine):
    engine.llm = _lector(False)
    a = engine.ask(SEIZURE, country="GB", lang="en")
    assert a.level == "routine" and not a.banner, (a.level, a.banner)


def test_an_alarm_the_reading_confirms_stays(engine):
    engine.llm = _lector(True)
    a = engine.ask(SEIZURE, country="GB", lang="en")
    assert a.level == "emergency" and a.banner


@pytest.mark.parametrize("veredicto", [None, "no", 0, "false"])
def test_anything_but_an_explicit_false_keeps_it(engine, veredicto):
    engine.llm = _lector(veredicto)
    a = engine.ask(SEIZURE, country="GB", lang="en")
    assert a.level == "emergency" and a.banner


def test_without_a_reading_the_alarm_stays(engine):
    engine.llm = FakeProvider("not json at all")
    a = engine.ask(SEIZURE, country="GB", lang="en")
    assert a.level == "emergency" and a.banner


def test_no_alarm_no_question_about_it(engine):
    engine.llm = _lector(True)
    engine.ask("my child has a mild cough", country="GB", lang="en")
    lectura = [u for s, u in engine.llm.calls if s.startswith("You read a parent's message")]
    assert lectura and "KEYWORD WARNINGS" not in lectura[0]


def test_only_ids_that_were_asked_count():
    """Un id inventado por el modelo no quita nada que no se le preguntó."""
    llm = FakeProvider(
        json.dumps(
            {
                "lang": "en",
                "lang_name": "English",
                "intent": "health",
                "query_en": "x",
                "query_es": "x",
                "keywords": [],
                "alarms": {"seizure": False, "otra": False},
            }
        )
    )
    leida = interpret(llm, "x", alarms={"seizure": "Abnormal movements / seizure"})
    assert leida is not None and leida.false_alarms == frozenset({"seizure"})
