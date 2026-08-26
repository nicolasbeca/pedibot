from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pedibot.api import ApiConfig, create_app
from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.llm import FakeProvider
from pedibot.bot.photo import interpret, parse
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.bot.vaccines import Vaccines, format_answer, is_vaccine_question
from pedibot.index.store import Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk
from pedibot.ops.store import OpsStore


@pytest.fixture(scope="module")
def vax(config_dir):
    return Vaccines(config_dir / "vaccines.yaml")


def test_vaccines_countries_and_lookup(vax):
    assert set(vax.countries) >= {"ES", "GB", "US"}
    assert vax.resolve_country("uk") == "GB" and vax.resolve_country("fr") is None
    due, nxt = vax.at_age("ES", 4, "es")
    assert any("MenC" in v for s in due for v in s.vaccines) and nxt and nxt.age_months == 11
    due_gb, _ = vax.at_age("GB", 12, "en")
    assert any("MMRV" in v for s in due_gb for v in s.vaccines)
    txt = format_answer(vax, "US", 2, "en")
    assert "DTaP (dose 1)" in txt and "CDC" in txt
    assert is_vaccine_question("what vaccines does a 4 month old get") and not is_vaccine_question(
        "tiene fiebre"
    )


def test_photo_interpretation():
    d = parse('{"petechiae":"yes","cyanosis":"no","swelling":"no","quality":"ok","note":"spots"}')
    level, text = interpret(d, "en", "999")
    assert level == "urgent" and "glass test" in text
    level2, text2 = interpret(
        parse('{"petechiae":"no","cyanosis":"yes","swelling":"no","quality":"ok","note":""}'),
        "es",
        "112",
    )
    assert level2 == "emergency" and "112" in text2
    assert interpret(parse("garbage"), "en", "911")[0] == "unsure"
    ok_level, ok_text = interpret(
        parse('{"petechiae":"no","cyanosis":"no","swelling":"no","quality":"ok","note":""}'),
        "en",
        "911",
    )
    assert ok_level == "routine" and "cannot replace an examination" in ok_text


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
                text="La fiebre no es peligrosa.",
                topic="fiebre",
                doc_type="hoja_padres",
                evidence="sociedad_cientifica",
                usage="publico",
                source_hash="h",
                n_words=5,
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
        FakeProvider("x [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(config_dir / "drugs.yaml"),
        vaccines=Vaccines(config_dir / "vaccines.yaml"),
    )

    def fake_vision(*a, **k):
        return (
            '{"petechiae":"yes","cyanosis":"no","swelling":"no","quality":"ok","note":"t"}',
            0.0001,
        )

    return TestClient(
        create_app(
            engine,
            OpsStore(tmp_path / "ops.db"),
            ApiConfig(allowed_origins=["*"]),
            vision_fn=fake_vision,
        )
    )


def test_vaccine_api_and_chat_routing(client):
    j = client.get("/api/vaccines?country=GB&age_months=2&lang=en").json()
    assert j["country"] == "GB" and any("6-in-1" in v for s in j["due"] for v in s["vaccines"])
    assert client.get("/api/vaccines?country=FR").status_code == 404
    a = client.post(
        "/api/ask",
        json={"question": "what vaccines does my 4 month old get?", "country": "ES", "lang": "en"},
    ).json()
    assert a["verification"] == "vaccine_schedule" and "MenC" in a["text"]


def test_photo_api(client, monkeypatch):
    from pedibot import settings as st

    monkeypatch.setattr(
        st,
        "get_settings",
        lambda: type(
            "S",
            (),
            {
                "photo_enabled": True,
                "deepseek_api_key": "k",
                "deepseek_base_url": "u",
                "deepseek_vision_model": "m",
            },
        )(),
    )
    import pedibot.api as api_mod

    monkeypatch.setattr(api_mod, "get_settings", st.get_settings, raising=False)
    r = client.post(
        "/api/photo",
        json={"image_b64": "A" * 200, "mime": "image/png", "lang": "en", "country": "GB"},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["level"] == "urgent" and "glass test" in j["text"] and j["signs"]["petechiae"] == "yes"
