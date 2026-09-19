from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pedibot.api import ApiConfig, create_app
from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.index.store import Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk
from pedibot.ops.store import OpsStore


def _chunk(cid, text, url=None):
    return Chunk(
        chunk_id=cid,
        doc_id=cid.split("#")[0],
        org="SEUP",
        doc_title="Fiebre. Información para padres",
        year=None,
        lang="es",
        section="¿Qué hacer?",
        pages=[1],
        text=text,
        topic="fiebre",
        doc_type="hoja_padres",
        evidence="sociedad_cientifica",
        usage="publico",
        source_url=url,
        source_hash="h",
        n_words=len(text.split()),
    )


@pytest.fixture
def client(tmp_path: Path, config_dir):
    db = tmp_path / "i.db"
    build_index(
        [
            _chunk(
                "seup_fiebre#s#1",
                "La fiebre no es peligrosa por sí misma. Ofrezca líquidos.",
                url="https://seup.org/f.pdf",
            )
        ],
        db,
    )
    llm = FakeProvider("La fiebre no es peligrosa, según la SEUP [1].")
    engine = Engine(
        Retriever(
            Index(db),
            Synonyms(config_dir / "synonyms.yaml"),
            taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
        ),
        Triage(config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(config_dir / "drugs.yaml"),
    )
    ops = OpsStore(tmp_path / "ops.db")
    cfg = ApiConfig(
        allowed_origins=["http://localhost:4321"],
        rate_limit_per_10min=3,
        rate_limit_per_day=5,
        max_daily_llm_usd=2.0,
    )
    # the same header the chat sends. Without it a request is `unknown` and the panel does not
    # count it as a reader, which is the whole point of test_who_asked.py — here we are standing
    # in for the front end, so we say so.
    return TestClient(create_app(engine, ops, cfg), headers={"x-pedibot-client": "web"}), ops


def test_health(client):
    c, _ = client
    r = c.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] and r.json()["index_chunks"] == 1


def test_ask_returns_sources_and_logs(client):
    c, ops = client
    r = c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre", "country": "ES"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["verification"] == "ok" and j["level"] == "routine" and j["banner"] is None
    assert j["sources"][0]["n"] == 1 and j["sources"][0]["url"] == "https://seup.org/f.pdf"
    assert "SEUP" in j["sources"][0]["citation"]
    assert j["session"] and j["answer_id"] >= 1
    assert ops.stats()["answers"] == 1


def test_a_request_that_does_not_say_who_it_is_is_not_a_reader(client):
    """The header is the whole mechanism (see tests/test_who_asked.py). A POST without it is
    answered exactly the same — nobody is ever refused help — but it does not reach the panel
    as somebody asking about their child. That is how 103 of my own test strings got there."""
    c, ops = client
    q = {"question": "mi hijo de 4 años tiene fiebre"}
    assert c.post("/api/ask", json=q, headers={"x-pedibot-client": ""}).status_code == 200
    assert c.post("/api/ask", json=q, headers={"x-pedibot-client": "test"}).status_code == 200
    assert ops.stats()["answers"] == 0
    # the rows are there, they are simply not readers
    assert ops.con.execute("SELECT COUNT(*) FROM answers").fetchone()[0] == 2


def test_feedback_only_from_owning_session(client):
    c, ops = client
    j = c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre"}).json()
    assert (
        c.post(
            "/api/feedback",
            json={"answer_id": j["answer_id"], "session": "someone-else", "value": 1},
        ).status_code
        == 404
    )
    assert c.post(
        "/api/feedback", json={"answer_id": j["answer_id"], "session": j["session"], "value": 1}
    ).json() == {"ok": True}
    assert ops.stats()["thumbs_up"] == 1


def test_rate_limit(client):
    c, _ = client
    for _ in range(3):
        assert (
            c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre"}).status_code
            == 200
        )
    assert (
        c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre"}).status_code == 429
    )


def test_validation(client):
    c, _ = client
    assert c.post("/api/ask", json={"question": "x"}).status_code == 422
    # Every language the engine speaks must be accepted, and one it does not must be refused
    # rather than answered in English. This test used to name the languages itself — it asserted
    # that German was refused, so when German shipped the test passed and hid a live 422 on
    # every question asked from the German site. It reads the list from the engine now.
    from pedibot.bot.answer import SUPPORTED_LANGS

    # one real request per side: the rate limiter would answer 429 to six of them, and the full
    # list is checked against the pattern in test_i18n_parity without spending the quota
    assert (
        c.post("/api/ask", json={"question": "hola", "lang": SUPPORTED_LANGS[-1]}).status_code
        == 200
    )
    # A code that will never be a language of this site, rather than the next one on the roadmap:
    # this line said "pt" and broke the day Portuguese shipped, which is the same trap in miniature
    # as the German one above.
    unsupported = next(c for c in ("zz", "qq", "xx") if c not in SUPPORTED_LANGS)
    assert c.post("/api/ask", json={"question": "ola", "lang": unsupported}).status_code == 422


def test_emergency_banner_in_api(client):
    c, _ = client
    j = c.post(
        "/api/ask", json={"question": "my 3 year old is having a seizure", "country": "US"}
    ).json()
    assert j["level"] == "emergency" and j["banner"].startswith("🚨 Call 911")


def test_degraded_mode_when_budget_spent(client, monkeypatch):
    c, ops = client
    monkeypatch.setattr(ops, "cost_today_usd", lambda: 99.0)
    j = c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre"}).json()
    assert j["degraded"] is True and j["verification"] == "degraded" and j["sources"]


def test_api_keeps_conversation_per_session(client):
    c, ops = client
    j1 = c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre"}).json()
    j2 = c.post(
        "/api/ask", json={"question": "¿y si además vomita?", "session": j1["session"]}
    ).json()
    assert j2["session"] == j1["session"] and j2["verification"] == "ok"
    h = ops.history(j1["session"])
    assert [t["role"] for t in h] == ["user", "assistant", "user", "assistant"]


def test_admin_panel_renders_and_flags(client, monkeypatch, tmp_path):
    c, ops = client
    from pedibot import admin
    from pedibot.ops import report

    # the flag file used to be a module constant, so every run of this test appended a line to
    # the working copy: it held 189 lines, all of them this same answer, before anybody looked
    monkeypatch.setattr(admin, "flagged_path", lambda: tmp_path / "flagged.jsonl")

    monkeypatch.setattr(
        report,
        "web_visits",
        lambda days=7: {
            "views": 3,
            "visitors": 2,
            "chat_pageviews": 1,
            "top": [("/", 3)],
            "per_day": {"2026-08-25": 3},
        },
    )
    monkeypatch.setattr(report, "balance", lambda: 9.5)
    j = c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre"}).json()
    r = c.get("/admin?days=7")
    assert r.status_code == 200
    assert "noindex" in r.text, "el panel nunca debe indexarse"
    # the question and its answer are the point of the page, not a metric beside them
    assert "mi hijo de 4 años" in r.text
    assert "ver la respuesta" in r.text
    # and the shape it was rewritten into: a chart, bars, and no token block
    assert "<svg" in r.text and "consultas por día" in r.text
    assert 'class="bars"' in r.text
    assert "PDBT" not in r.text, "el token tiene su propio aviso; aquí sobra"

    r2 = c.post("/admin/flag", data={"id": j["answer_id"]}, follow_redirects=False)
    assert r2.status_code == 303
    assert "🚩" in c.get("/admin").text

    # pressing it twice does not write it twice, and it can be taken back: a misclick used to
    # mark an answer for ever
    c.post("/admin/flag", data={"id": j["answer_id"]}, follow_redirects=False)
    assert "🚩" not in c.get("/admin").text
    c.post("/admin/flag", data={"id": j["answer_id"]}, follow_redirects=False)
    assert len(admin.load_flagged()) == 1


def test_the_panel_opens_on_the_totals(client, monkeypatch):
    """It opened on the last 7 days, so the first question it answered was "how did this week go",
    and the one the operator actually has is "how much is there at all". The windows stay one
    click away."""
    c, _ = client
    from pedibot.ops import report

    monkeypatch.setattr(
        report,
        "web_visits",
        lambda days=7: {
            "views": 3,
            "visitors": 2,
            "chat_pageviews": 1,
            "top": [("/", 3)],
            "per_day": {"2026-08-25": 3},
            "covers": ("2026-08-25", "2026-08-25"),
        },
    )
    c.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre"})

    landing = c.get("/admin").text
    assert 'href="/admin?days=0" class="on"' in landing, "no entra por los totales"
    assert "desde el principio" in landing
    # the two blocks of numbers do NOT cover the same period, and the page has to say so:
    # questions live in the database for ever, visits only as long as the journal keeps them
    assert "desde el 25 ago" in landing
    assert "no guarda desde siempre" in landing

    week = c.get("/admin?days=7").text
    assert 'href="/admin?days=7" class="on"' in week
    assert "últimos 7 días" in week
    assert "consultas por día" in week


def test_the_dose_endpoint_hands_the_page_a_figure_not_a_band(client):
    """The web calculator rendered `mg_min–mg_max` and `ml_min–ml_max` joined by a dash, and a
    parent at three in the morning cannot measure "3–6 ml". The endpoint carries `mg` and a
    per-form `ml` now; the band stays alongside so the page can show it as context."""
    c, _ = client
    # con edad: Dalsy es ibuprofeno, y desde el 9-sep-2026 un fármaco con edad mínima no da la
    # cifra si no se indica la edad — no se puede descartar que el niño esté por debajo. Lo que
    # este test comprueba es otra cosa (que la cifra sea una cifra y no una banda), así que se
    # le da la edad en vez de aflojar aquello.
    j = c.post("/api/dose", json={"drug": "dalsy", "weight_kg": 12, "age_months": 36}).json()
    assert j["mg"] == 120, j
    two_percent = next(
        f for f in j["ml_by_form"] if "2 %" in f["form"] or "100 mg/5 ml" in f["form"]
    )
    assert two_percent["ml"] == 6.0, two_percent  # what the Dalsy leaflet gives for 12 kg
    assert (j["mg_min"], j["mg_max"]) == (60, 120)
    for f in j["ml_by_form"]:
        assert isinstance(f["ml"], (int, float)), "una dosis es un número, no una banda"


def test_the_panel_can_name_every_language_and_level() -> None:
    """`_LANG_NAME` is a hand-written list and Hindi shipped in it as a bare "hi". A list of
    languages typed by hand always exempts the one just added — which is the one most likely to
    be wrong. Same for the triage levels, which decide whether a red banner sits over a parent's
    answer and were printed in their internal English."""
    from pedibot.admin import _LANG_NAME, _LEVEL_NAME
    from pedibot.bot.answer import SUPPORTED_LANGS
    from pedibot.bot.triage import LEVEL_ORDER

    missing = set(SUPPORTED_LANGS) - set(_LANG_NAME)
    assert not missing, f"el panel no sabe nombrar {sorted(missing)}"
    assert not set(LEVEL_ORDER) - set(_LEVEL_NAME), "falta traducir algún nivel de triaje"
