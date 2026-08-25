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
    llm = FakeProvider("La fiebre no es peligrosa [1].")
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
    return TestClient(create_app(engine, ops, cfg)), ops


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
    assert c.post("/api/ask", json={"question": "hola", "lang": "fr"}).status_code == 422


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
