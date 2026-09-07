"""Lo que ve un padre cuando no hay modelo (7-sep-2026).

Cuando se alcanza el tope de gasto del día —o si DeepSeek está caído— el API responde sin LLM:
devuelve los pasajes de las guías que ha recuperado. Es un camino que casi nunca se ejecuta, así
que nadie lo miraba, y construía la respuesta con el nivel escrito a mano:

    Answer(text, "routine", None, ...)

Es decir: **quien preguntara por el sarpullido que no blanquea, los labios azules o una convulsión
el día que se agotó el presupuesto recibía «rutina» y ninguna alarma.** Es exactamente al revés de
como debe fallar un sistema así: lo primero que se pierde tiene que ser lo prescindible, y aquí se
perdía lo único que no lo es.

No había razón técnica. El triaje es determinista y gratis: no usa el modelo, no cuesta un
céntimo, y funciona igual con el presupuesto a cero.

De paso, el aviso de presupuesto estaba en dos idiomas de ocho —inglés, y español para los otros
seis—, así que un padre alemán recibía una frase en español.
"""

from __future__ import annotations

import pytest
from test_api import client  # noqa: F401 — la fixture: motor, índice de prueba y OpsStore

from pedibot.api import BUDGET_SPENT
from pedibot.bot.answer import SUPPORTED_LANGS


@pytest.fixture
def sin_presupuesto(client, monkeypatch):  # noqa: F811
    """El API en modo degradado, como el día que se agota el tope de gasto."""
    c, ops = client
    monkeypatch.setattr(ops, "cost_today_usd", lambda: 99.0)
    return c


def test_the_alarm_still_fires_with_no_model(sin_presupuesto) -> None:
    """La comprobación que da nombre al fichero, en español."""
    r = sin_presupuesto.post(
        "/api/ask",
        json={
            "question": "le ha salido un sarpullido que no desaparece al apretarlo con un vaso",
            "lang": "es",
            "country": "ES",
        },
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["degraded"] is True, "esta prueba solo vale con el API en modo degradado"
    assert j["level"] == "emergency", f"sin modelo se pierde la alarma: nivel {j['level']}"
    assert j["banner"], "sin modelo desaparece el banner de emergencia"


def test_the_alarm_still_fires_with_no_model_in_english(sin_presupuesto) -> None:
    """Y en inglés, con el número de emergencias del país — el banner se construye entero."""
    j = sin_presupuesto.post(
        "/api/ask",
        json={"question": "my 3 year old is having a seizure", "lang": "en", "country": "US"},
    ).json()
    assert j["degraded"] is True
    assert j["level"] == "emergency"
    assert j["banner"].startswith("🚨 Call 911")


def test_an_ordinary_question_stays_ordinary_with_no_model(sin_presupuesto) -> None:
    """La otra mitad: el modo degradado no puede convertirse en una máquina de alarmas."""
    j = sin_presupuesto.post(
        "/api/ask", json={"question": "mi hijo de 4 años tiene mocos", "lang": "es"}
    ).json()
    assert j["degraded"] is True
    assert j["level"] == "routine"
    assert j["banner"] is None


def test_the_budget_notice_exists_in_every_language() -> None:
    """Estaba en inglés y español; los otros seis recibían la frase española.

    La lista de idiomas se lee del propio motor, no se escribe a mano: un idioma nuevo tiene que
    romper esta prueba, no colarse en silencio (es el fallo del clon podrido, L23)."""
    faltan = [lang for lang in SUPPORTED_LANGS if lang not in BUDGET_SPENT]
    assert not faltan, f"sin aviso de presupuesto: {faltan}"
    assert len(set(BUDGET_SPENT.values())) == len(BUDGET_SPENT), (
        "hay dos idiomas con la misma frase"
    )


def test_the_budget_notice_comes_back_in_the_readers_language(sin_presupuesto) -> None:
    """Y llega de verdad al lector: el índice de prueba solo tiene un pasaje, en español."""
    j = sin_presupuesto.post(
        "/api/ask", json={"question": "mi hijo de 4 años tiene fiebre", "lang": "es"}
    ).json()
    assert j["text"] == BUDGET_SPENT["es"]


def test_the_answer_still_names_its_sources_with_no_model(sin_presupuesto) -> None:
    """Sin modelo se pierde la redacción, no las fuentes: el camino degradado existe precisamente
    para seguir enseñando de dónde sale la información."""
    j = sin_presupuesto.post(
        "/api/ask", json={"question": "mi hijo de 4 años tiene fiebre", "lang": "es"}
    ).json()
    assert j["verification"] == "degraded"
    assert j["sources"], "sin modelo la respuesta se queda sin fuentes que enseñar"
