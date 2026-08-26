from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pedibot.api import ApiConfig, create_app
from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.index.store import Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk
from pedibot.ops.store import OpsStore
from pedibot.publish.articles import TOPIC_PLAN, seasonal_first


@pytest.fixture
def client(tmp_path: Path, config_dir):
    db = tmp_path / "i.db"
    build_index(
        [
            Chunk(
                chunk_id="seup_fiebre#s#1",
                doc_id="seup_fiebre",
                org="SEUP",
                doc_title="Fiebre",
                year=None,
                lang="es",
                section="S",
                pages=[1],
                text="La fiebre no es peligrosa por sí misma.",
                topic="fiebre",
                doc_type="hoja_padres",
                evidence="sociedad_cientifica",
                usage="publico",
                source_hash="h",
                n_words=6,
            )
        ],
        db,
    )
    engine = Engine(
        Retriever(
            Index(db),
            Synonyms(config_dir / "synonyms.yaml"),
            taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
        ),
        Triage(config_dir / "red_flags.yaml"),
        FakeProvider("Según la SEUP, la fiebre no es peligrosa [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
    )
    return TestClient(
        create_app(engine, OpsStore(tmp_path / "ops.db"), ApiConfig(allowed_origins=["*"]))
    )


def test_vague_first_message_gets_clarify_options(client):
    j = client.post("/api/ask", json={"question": "mi hijo está malo", "lang": "es"}).json()
    assert j["verification"] == "clarify" and "Fiebre" in j["options"] and j["banner"] is None
    # a clear message does not
    j2 = client.post(
        "/api/ask", json={"question": "mi hijo de 4 años tiene fiebre", "lang": "es"}
    ).json()
    assert j2["verification"] == "ok"
    # follow-up in the same session is never clarified
    j3 = client.post(
        "/api/ask", json={"question": "está malo", "lang": "es", "session": j2["session"]}
    ).json()
    assert j3["verification"] != "clarify"


def test_seasonal_reorders_pending():
    topics = ["tca", "bronquiolitis", "heat", "flu"]
    assert seasonal_first(topics, month=12)[:2] == ["bronquiolitis", "flu"]
    assert seasonal_first(topics, month=7)[0] == "heat"
    assert seasonal_first(topics, month=7, hemisphere="south")[0] == "bronquiolitis"
    assert set(seasonal_first(topics, month=3)) == set(topics)


def test_compare_topics_span_organisations(config_dir):
    from pedibot.ingest.catalog import load_catalog

    docs = {d.doc_id: d for d in load_catalog(config_dir / "fuentes.yaml")}
    for t, plan in TOPIC_PLAN.items():
        if plan.get("compare"):
            orgs = {docs[d].org for d in plan["docs"]}
            assert len(orgs) >= 2, t


def test_agent_endpoint_requires_key(client, monkeypatch):
    r = client.post(
        "/api/agent/ask", json={"question": "mi hijo de 4 años tiene fiebre", "lang": "es"}
    )
    assert r.status_code == 401
    monkeypatch.setenv("AGENT_API_KEYS", "k1,k2")
    r2 = client.post(
        "/api/agent/ask",
        json={"question": "mi hijo de 4 años tiene fiebre", "lang": "es"},
        headers={"x-api-key": "k2"},
    )
    assert (
        r2.status_code == 200
        and r2.json()["verification"] == "ok"
        and "SEUP" in r2.json()["answer"]
    )


def test_a_clear_question_in_everyday_words_is_not_clarified(client):
    """26-ago: the clarify filter read the raw question only, so «se ha desmayado en el colegio»
    or «llora sin parar» — which the taxonomy does not name literally — were treated as vague and
    the parent got a menu instead of an answer. The synonyms already know these words."""
    for q in (
        "Se ha desmayado en el colegio, tiene 12 años",
        "Mi bebé de 1 mes llora sin parar cada tarde",
        "Mi hija de 14 años apenas come y ha perdido mucho peso",
    ):
        j = client.post("/api/ask", json={"question": q, "lang": "es"}).json()
        assert j["verification"] != "clarify", q


def test_a_genuinely_vague_message_is_still_clarified(client):
    j = client.post("/api/ask", json={"question": "mi hijo está malito", "lang": "es"}).json()
    assert j["verification"] == "clarify"
