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
        FakeProvider("Según la SEUP, x [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(config_dir / "drugs.yaml"),
    )
    return TestClient(
        create_app(engine, OpsStore(tmp_path / "ops.db"), ApiConfig(allowed_origins=["*"]))
    )


def test_dose_api_with_brand(client):
    r = client.post(
        "/api/dose", json={"drug": "Calpol", "weight_kg": 14, "age_months": 36, "lang": "en"}
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["drug"] == "paracetamol" and j["brand"] == "Calpol" and j["mg_min"] == 140
    forms = {f["form"]: f for f in j["ml_by_form"]}
    # 8.7 y no 8.8: 210 mg a 24 mg/ml son 8.75 ml exactos, y los mililitros NUNCA redondean
    # hacia arriba (6-sep-2026 — ver test_millilitres_never_round_up). Esta expectativa guardaba
    # el redondeo al más cercano que tenían los extremos de la banda antes de arreglarlos.
    assert (
        forms["infant 120 mg/5 ml"]["ml_min"] == 5.8
        and forms["infant 120 mg/5 ml"]["ml_max"] == 8.7
    )
    assert "AEPap" in j["source"]


def test_dose_api_generic_uses_default_presentations(client):
    """Sin marca, la respuesta trae TODAS las presentaciones del medicamento.

    Antes decía `== 2`, un número clavado a mano que se rompió el 7-sep-2026 al añadir las gotas
    de 50 mg/ml — que el catálogo ya conocía y el chat no. Contar presentaciones no comprueba
    nada: lo que importa es que estén todas las del medicamento y que cada una traiga su volumen,
    porque un padre tiene que encontrar SU bote en la lista."""
    from pedibot.bot.dose import DRUGS

    j = client.post(
        "/api/dose", json={"drug": "ibuprofeno", "weight_kg": 20, "age_months": 48, "lang": "es"}
    ).json()
    assert j["brand"] is None and j["generic"] == "Ibuprofeno"
    esperadas = {p.name for p in DRUGS["ibuprofeno"].presentations}
    assert {f["form"] for f in j["ml_by_form"]} == esperadas
    assert all(f["ml"] > 0 for f in j["ml_by_form"])


def test_dose_api_refers_young_infant_and_rejects_unknown(client):
    j = client.post("/api/dose", json={"drug": "nurofen", "weight_kg": 5, "age_months": 2}).json()
    assert j["refer"] is True and "under_3_months_refer" in j["warnings"]
    assert client.post("/api/dose", json={"drug": "aspirin", "weight_kg": 10}).status_code == 422


def test_drugs_list(client):
    j = client.get("/api/drugs?country=ES&lang=es").json()
    assert set(j) == {"paracetamol", "ibuprofen"}
    assert "ES" in j["ibuprofen"]["brands"][0]["countries"]


def test_ask_routes_brand_dose_question(client):
    j = client.post(
        "/api/ask",
        json={"question": "how much Calpol for my 3 year old, she weighs 14 kg", "country": "GB"},
    ).json()
    assert j["verification"] == "dose_calculator" and "140" in j["text"]


def test_checklist_endpoint(client):
    j = client.get("/api/checklist?lang=es").json()
    assert "SEUP" in j["source"] and len(j["items"]) >= 30
    assert {i["level"] for i in j["items"]} == {"call_now", "go_today", "gp"}
    assert any("3 meses" in i["text"] for i in j["items"])
    assert "Skin" in client.get("/api/checklist?lang=en").json()["categories"].values()


def test_share_flow(client):
    j = client.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre"}).json()
    assert (
        client.post(
            "/api/share", json={"answer_id": j["answer_id"], "session": "other"}
        ).status_code
        == 404
    )
    s = client.post(
        "/api/share", json={"answer_id": j["answer_id"], "session": j["session"]}
    ).json()
    page = client.get(s["path"])
    assert page.status_code == 200 and "noindex" in page.text and "fiebre" in page.text
    assert j["session"] not in page.text
    assert client.get("/a/nope").status_code == 404


def test_child_mode_reaches_prompt(client):
    j = client.post(
        "/api/ask", json={"question": "mi hijo de 4 años tiene fiebre", "mode": "child"}
    ).json()
    assert j["verification"] in ("ok", "fallback")


def test_ors_endpoint(client):
    j = client.get("/api/ors?age_months=36&vomiting=true&lang=es").json()
    assert (
        j["age_band"] == "vomiting"
        and any("200 ml" in ln for ln in j["lines"])
        and any("SEUP" in s for s in j["sources"])
    )
    assert client.get("/api/ors?age_months=0.5").json()["refer"] is True
