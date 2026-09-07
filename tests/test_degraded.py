"""Lo que ve un padre cuando no hay modelo (7-sep-2026).

Dos causas, un solo camino: el tope de gasto del día (decisión nuestra) y la avería del proveedor
(DeepSeek caído, lento o sin saldo). Se contestan igual —las guías recuperadas más el triaje
completo— y se etiquetan distinto, `degraded` y `no_model`, para que una avería no se esconda
dentro de algo que parece normal.

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

from pedibot.bot.answer import BUDGET_SPENT, NO_MODEL, SUPPORTED_LANGS
from pedibot.bot.llm import FakeProvider, LLMUnavailable


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


# --------------------------------------------------------------------------------------------
# La otra causa: el modelo no contesta. Hasta el 7-sep-2026 esto era un 500.
#
# El camino salía por la excepción sin pasar por `log_answer`, así que además de perder el triaje
# ya hecho y los pasajes ya recuperados, **no quedaba registro**: no había forma de saber cuántas
# veces le había pasado a alguien. Ahora se contesta y se cuenta.
# --------------------------------------------------------------------------------------------


@pytest.fixture
def modelo_caido(client, monkeypatch):  # noqa: F811
    """El API con DeepSeek caído: el proveedor levanta LLMUnavailable."""
    c, ops = client

    def boom(self, system, user, temperature=0.2, max_tokens=1500):
        raise LLMUnavailable("APITimeoutError: no contesta")

    monkeypatch.setattr(FakeProvider, "complete", boom)
    return c, ops


def test_a_dead_model_does_not_take_the_alarm_with_it(modelo_caido) -> None:
    """Antes: 500, y el padre veía «algo ha fallado por nuestra parte» sin ninguna alarma."""
    c, _ = modelo_caido
    r = c.post(
        "/api/ask",
        json={
            "question": "mi hijo de 4 años tiene fiebre y está teniendo una convulsión",
            "lang": "es",
            "country": "ES",
        },
    )
    assert r.status_code == 200, "el modelo caído no puede tumbar la respuesta"
    j = r.json()
    assert j["level"] == "emergency"
    assert j["banner"] and "112" in j["banner"]
    assert j["sources"], "los pasajes ya estaban recuperados: tirarlos es gratuito"


def test_a_dead_model_is_told_apart_from_our_own_budget(modelo_caido) -> None:
    """La avería no puede esconderse dentro del tope de gasto: son cosas distintas."""
    c, ops = modelo_caido
    j = c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre", "lang": "es"}).json()
    assert j["verification"] == "no_model"
    assert j["degraded"] is False, "no es el presupuesto: el presupuesto está intacto"
    assert j["text"] == NO_MODEL["es"]
    # y queda contada, que es la mitad del arreglo: antes salía por la excepción sin pasar por
    # log_answer, así que la avería no dejaba rastro en ninguna parte
    ultima = ops.con.execute("SELECT verification FROM answers ORDER BY id DESC LIMIT 1").fetchone()
    assert ultima[0] == "no_model", "la avería no queda registrada: no sabríamos que ocurre"


def test_a_bug_of_ours_still_blows_up(client, monkeypatch) -> None:  # noqa: F811
    """El candado del candado: recoger el fallo del modelo NO puede tapar nuestros errores.

    Por eso el proveedor levanta una excepción propia y el API recoge solo esa. Un TypeError
    nuestro tiene que seguir saliendo a gritos."""
    c, _ = client

    def bug(self, system, user, temperature=0.2, max_tokens=1500):
        raise TypeError("esto es un error nuestro, no del proveedor")

    monkeypatch.setattr(FakeProvider, "complete", bug)
    with pytest.raises(TypeError):
        c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre", "lang": "es"})


def test_the_outage_notice_is_in_every_language() -> None:
    faltan = [lang for lang in SUPPORTED_LANGS if lang not in NO_MODEL]
    assert not faltan, f"sin aviso de avería: {faltan}"
    assert len(set(NO_MODEL.values())) == len(NO_MODEL)
    # y no puede ser el mismo texto que el del presupuesto: dicen cosas distintas
    assert not set(NO_MODEL.values()) & set(BUDGET_SPENT.values())


def test_the_model_is_not_given_ten_minutes_of_a_parents_time() -> None:
    """El cliente de OpenAI espera 600 s y reintenta 2 veces: hasta media hora de reloj girando.

    Medido sobre las respuestas reales (n=108): mediana 3,2 s, p99 5,8 s, la más lenta 8,3 s. El
    número que se ponga aquí es discutible; que sean diez minutos, no."""
    from pedibot.bot.llm import OpenAICompatibleProvider

    p = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
    OpenAICompatibleProvider.__init__(p, "sk-de-mentira", "https://example.invalid", "m", 0.0, 0.0)
    espera = p._client.timeout
    segundos = espera if isinstance(espera, int | float) else espera.read
    assert segundos is not None and segundos <= 60, f"espera {segundos} s: demasiado para un padre"
    assert p._client.max_retries <= 1, "cada reintento multiplica la espera"


# --------------------------------------------------------------------------------------------
# Y que se vea. Registrar una avería sin enseñarla es media reparación: nadie baja a leer la
# lista de las últimas consultas para descubrir que el modelo estuvo caído el martes.
# --------------------------------------------------------------------------------------------


def _panel(ops, days: int = 7) -> str:
    from pedibot.admin import render

    return render(ops.con, days)


def test_the_panel_stays_quiet_when_nothing_broke(client) -> None:  # noqa: F811
    c, ops = client
    c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre", "lang": "es"})
    assert "sin modelo" not in _panel(ops)


def test_the_panel_says_it_out_loud_when_the_model_failed(modelo_caido) -> None:
    c, ops = modelo_caido
    c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre", "lang": "es"})
    html = _panel(ops)
    assert "sin modelo" in html
    assert "el modelo no contestó" in html
    assert "tope de gasto" not in html, "no es el presupuesto: no se puede decir que lo sea"


def test_the_panel_tells_the_two_causes_apart(sin_presupuesto, client) -> None:  # noqa: F811
    _, ops = client
    sin_presupuesto.post(
        "/api/ask", json={"question": "mi hijo de 4 años tiene fiebre", "lang": "es"}
    )
    html = _panel(ops)
    assert "tope de gasto" in html
    assert "el modelo no contestó" not in html, "el tope lo decidimos nosotros: no es una avería"


# --------------------------------------------------------------------------------------------
# Telegram. El mismo motor, otro frente — y hasta el 7-sep-2026 no tenía nada de esto:
#
#   * el tope de gasto del día **solo existía en el API**, así que por Telegram se seguía llamando
#     al modelo con el presupuesto agotado. El freno de gasto tenía una puerta abierta al lado.
#   * un fallo del modelo lo recogía un `except Exception` en la capa de transporte, que contestaba
#     «Something went wrong on our side» —en inglés, dijera el chat lo que dijera— y tiraba el
#     triaje ya hecho.
# --------------------------------------------------------------------------------------------


@pytest.fixture
def telegram(tmp_path, config_dir):
    from test_api import _chunk

    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.drugs import DrugCatalog
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.bot.triage import Triage
    from pedibot.index.store import Index, build_index
    from pedibot.ingest.classify import Taxonomy
    from pedibot.ops.store import OpsStore
    from pedibot.telegram_bot import TelegramFront

    db = tmp_path / "tg.db"
    es = _chunk(
        "seup_fiebre#s#1",
        "La fiebre no es peligrosa por sí misma. Ofrezca líquidos.",
        url="https://seup.org/f.pdf",
    )
    # y uno en alemán: sin él, una pregunta alemana no recupera nada, el motor corta antes de
    # llamar al modelo y la prueba de la avería no probaría nada (pasaba con el código viejo)
    de = _chunk(
        "rki_fieber#s#1",
        "Fieber bei Kindern ist meist harmlos. Geben Sie Ihrem Kind genug zu trinken.",
        url="https://rki.de/f.pdf",
    ).model_copy(update={"lang": "de", "doc_title": "Fieber bei Kindern"})
    build_index([es, de], db)
    engine = Engine(
        Retriever(
            Index(db),
            Synonyms(config_dir / "synonyms.yaml"),
            taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
        ),
        Triage(config_dir / "red_flags.yaml"),
        FakeProvider("La fiebre no es peligrosa, según la SEUP [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(config_dir / "drugs.yaml"),
    )
    ops = OpsStore(tmp_path / "tgops.db")
    return TelegramFront(engine, ops, max_daily_usd=2.0), ops, engine


def test_telegram_respects_the_daily_spending_cap(telegram, monkeypatch) -> None:
    """El hueco era de dinero: con el tope alcanzado, Telegram seguía llamando al modelo."""
    front, ops, engine = telegram
    monkeypatch.setattr(ops, "cost_today_usd", lambda: 99.0)
    front.handle_message(7, "mi hijo de 4 años tiene fiebre")
    assert engine.llm.calls == [], "con el presupuesto agotado no se puede llamar al modelo"
    fila = ops.con.execute("SELECT verification FROM answers ORDER BY id DESC LIMIT 1").fetchone()
    assert fila[0] == "degraded"


def test_telegram_keeps_the_alarm_when_the_model_is_down(telegram, monkeypatch) -> None:
    front, ops, _ = telegram

    def boom(self, system, user, temperature=0.2, max_tokens=1500):
        raise LLMUnavailable("APITimeoutError: no contesta")

    monkeypatch.setattr(FakeProvider, "complete", boom)
    front.handle_command(7, "/lang es")
    front.handle_command(7, "/country ES")
    texto, _ = front.handle_message(
        7, "mi hijo de 4 años tiene fiebre y está teniendo una convulsión"
    )
    assert "112" in texto, "el modelo caído no puede llevarse por delante el número de urgencias"
    fila = ops.con.execute(
        "SELECT level, verification FROM answers ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert fila[0] == "emergency" and fila[1] == "no_model"


def test_telegram_answers_an_outage_in_the_chats_language(telegram, monkeypatch) -> None:
    """El mensaje viejo era inglés fijo: un padre alemán recibía una frase que no entiende."""
    front, _, _ = telegram

    def boom(self, system, user, temperature=0.2, max_tokens=1500):
        raise LLMUnavailable("APITimeoutError: no contesta")

    monkeypatch.setattr(FakeProvider, "complete", boom)
    front.handle_command(9, "/lang de")
    texto, _ = front.handle_message(9, "mein Kind ist 4 Jahre alt und hat Fieber")
    from pedibot.bot.answer import NO_MODEL as NM

    assert "Something went wrong" not in texto
    assert NM["de"] in texto, "la avería se le cuenta al padre en su idioma, no en inglés"
