"""«¿Cuánto suero oral le doy?» en el chat: la cantidad de la tabla, no «pregunta a tu médico».

12-nov-2026, probado para un correo: «1 साल के बच्चे को दस्त हो रहे हैं, ORS कितना देना चाहिए?»
contestaba que la cantidad «no está en estas informaciones» mientras `bot/ors.py` (la misma
tabla que sirve /api/ors y la herramienta oral_rehydration_plan del MCP) la tenía: unos 200 ml por
deposición en un niño de un año, a sorbos. El chat no la usaba. Como con la dosis, la cantidad sale
de la tabla y nunca del modelo.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pedibot.api import ApiConfig, create_app
from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.strings import tool_strings
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
                chunk_id="who_diarrhoea#s#1",
                doc_id="who_diarrhoea",
                org="WHO",
                doc_title="Diarrhoeal disease",
                year=None,
                lang="en",
                section="S",
                pages=[1],
                text="ORS is a mixture of clean water, salt and sugar.",
                topic="gastroenteritis",
                doc_type="hoja_padres",
                evidence="organismo_publico",
                usage="publico",
                source_hash="h",
                n_words=10,
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
        FakeProvider("Ask your doctor how much [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(config_dir / "drugs.yaml"),
    )
    return TestClient(
        create_app(engine, OpsStore(tmp_path / "ops.db"), ApiConfig(allowed_origins=["*"]))
    )


@pytest.mark.parametrize(
    "lang,pregunta,banda",
    [
        ("hi", "1 साल के बच्चे को दस्त हो रहे हैं, ORS कितना देना चाहिए?", "ors_child"),
        ("en", "My 2 year old has diarrhoea. How much ORS should I give?", "ors_child"),
        ("es", "Mi bebé de 8 meses tiene diarrea, ¿cuánto suero oral le doy?", "ors_infant"),
        ("fr", "Mon fils de 3 ans a la diarrhée, combien de SRO je lui donne ?", "ors_child"),
        ("pt", "O meu filho de 2 anos tem diarreia, quanto soro oral devo dar?", "ors_child"),
    ],
)
def test_cuanto_suero_da_la_tabla(client, lang: str, pregunta: str, banda: str):
    j = client.post("/api/ask", json={"question": pregunta, "lang": lang}).json()
    assert j["verification"] == "ors_plan", j
    # el francés pierde el espacio antes de «:» al pulir la tipografía; no es lo que se mide
    assert tool_strings(lang)[banda].replace(" :", ":") in j["text"].replace(" :", ":"), j["text"]
    assert "AEMPS" in j["text"], "la cantidad lleva su fuente"


def test_sin_edad_da_las_tres_franjas(client):
    j = client.post(
        "/api/ask", json={"question": "How much ORS for diarrhoea?", "lang": "en"}
    ).json()
    assert j["verification"] == "ors_plan", j
    for k in ("ors_under_1_month", "ors_infant", "ors_child"):
        assert tool_strings("en")[k] in j["text"]


def test_lo_que_es_el_suero_sigue_yendo_a_las_guias(client):
    """Sin «cuánto» no hay cantidad que dar: la pregunta va a las guías como siempre."""
    j = client.post("/api/ask", json={"question": "What is ORS?", "lang": "en"}).json()
    assert j["verification"] != "ors_plan", j


# 17-nov-2026: «quanto soro caseiro ou soro de farmácia devo dar?» (Brasil, probado para un correo)
# daba la cantidad del sobre de farmacia y callaba el casero. Ninguna fuente del corpus da la receta
# brasileña (la única es la india de las ASHA, con otras medidas): se dice, y se manda a pedirla.
@pytest.mark.parametrize(
    ("lang", "pregunta", "frase"),
    [
        ("pt", "Meu bebê de 10 meses está com diarreia, quanto soro caseiro devo dar?", "soro caseiro"),
        ("es", "¿Cuánto suero casero le doy a mi hijo de 2 años con diarrea?", "suero casero"),
        ("en", "How much homemade ORS should I give my 2 year old?", "homemade"),
    ],
)
def test_el_suero_casero_dice_que_no_hay_receta(client, lang: str, pregunta: str, frase: str):
    j = client.post("/api/ask", json={"question": pregunta, "lang": lang}).json()
    assert j["verification"] == "ors_plan", j
    assert frase in j["text"].lower(), j["text"]


def test_sin_casero_no_se_habla_del_casero(client):
    j = client.post(
        "/api/ask", json={"question": "How much ORS should I give my 2 year old?", "lang": "en"}
    ).json()
    assert "homemade" not in j["text"].lower()
