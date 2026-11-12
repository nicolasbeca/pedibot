"""Dos pesos en la misma pregunta: se pregunta cuál (30-sep-2026, decisión del operador).

«En el centro de salud lo pesaron en 7,2 kg y en casa me sale 7,8: ¿cuánto paracetamol?» se
calculaba con el primer número que aparecía, sin decir que había otro. Da igual cuál fuese el
bueno: el padre no sabía que habíamos elegido. De las tres salidas posibles —preguntar,
calcular con los dos o usar el menor— el operador eligió la que haría una persona: preguntar.

Si los dos números son el mismo peso escrito dos veces («7,2 kg… sí, 7,2 kg») no hay nada que
preguntar.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pedibot.api import ApiConfig, create_app
from pedibot.bot.answer import EmergencyNumbers, Engine, weights_in
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


def test_los_pesos_se_leen_todos():
    assert weights_in("pesa 7,2 kg en el centro y 7.8 kg en casa") == [7.2, 7.8]
    assert weights_in("7,2 kg… sí, 7,2 kg") == [7.2]
    assert weights_in("весит 12 кг") == [12.0]


@pytest.mark.parametrize(
    "lang,pregunta",
    [
        ("es", "En el centro lo pesaron en 7,2 kg y en casa 7,8 kg. ¿Cuánto paracetamol le doy?"),
        ("en", "The clinic said 7.2 kg but at home she is 7.8 kg. How much paracetamol?"),
        ("fr", "7,2 kg chez le médecin et 7,8 kg à la maison : combien de paracétamol ?"),
    ],
)
def test_con_dos_pesos_pregunta_cual(client, lang: str, pregunta: str):
    j = client.post("/api/ask", json={"question": pregunta, "lang": lang}).json()
    assert j["verification"] == "dose_two_weights", j
    assert "7.2" in j["text"].replace(",", ".") and "7.8" in j["text"].replace(",", ".")
    assert " mg " not in j["text"], "no puede dar una dosis mientras no sepa el peso"


def test_con_un_solo_peso_calcula(client):
    j = client.post(
        "/api/ask", json={"question": "Pesa 7,2 kg. ¿Cuánto paracetamol le doy?", "lang": "es"}
    ).json()
    assert j["verification"] == "dose_calculator"


def test_y_cuando_contesta_calcula_con_el_que_dice(client):
    """La pregunta sólo sirve si la respuesta del padre lleva a la dosis."""
    s = "sesion-dos-pesos"
    client.post(
        "/api/ask",
        json={
            "question": "En el centro 7,2 kg y en casa 7,8 kg. ¿Cuánto paracetamol le doy?",
            "lang": "es",
            "session": s,
        },
    )
    j = client.post("/api/ask", json={"question": "7,8 kg", "lang": "es", "session": s}).json()
    assert j["verification"] == "dose_calculator", j
    assert "7.8 kg" in j["text"] or "7,8 kg" in j["text"], j["text"]


# 12-nov-2026: dos pesos de DOS niños no son una duda sobre el peso. «My twins both have a fever.
# How much Calpol? One weighs 9 kg and the other 10 kg» recibía «¿con cuál calculo?», y a un
# padre de gemelos la respuesta obvia es: las dos. La regla del 30-sep (preguntar) sigue para el
# mismo niño pesado dos veces; aquí la pregunta nombra a dos niños.
@pytest.mark.parametrize(
    "lang,pregunta",
    [
        ("en", "My twins both have a fever. How much Calpol? One weighs 9 kg and the other 10 kg"),
        ("en", "How much paracetamol for my two kids? One is 9 kg, the other is 14 kg"),
        ("es", "Mis gemelos tienen fiebre, uno pesa 9 kg y el otro 10 kg. ¿Cuánto Apiretal?"),
        ("es", "¿Cuánto ibuprofeno le doy a cada uno? El mayor pesa 14 kg y la pequeña 9 kg"),
        ("fr", "Mes jumeaux ont de la fièvre, l'un fait 9 kg et l'autre 10 kg. Combien de paracétamol ?"),
        ("de", "Meine Zwillinge haben Fieber, einer wiegt 9 kg und der andere 10 kg. Wie viel Paracetamol?"),
        ("pt", "Os meus gémeos têm febre, um pesa 9 kg e o outro 10 kg. Quanto paracetamol?"),
    ],
)
def test_dos_ninos_calcula_las_dos(client, lang: str, pregunta: str):
    j = client.post("/api/ask", json={"question": pregunta, "lang": lang}).json()
    assert j["verification"] == "dose_calculator", j
    pesos = weights_in(pregunta)
    for kg in pesos:
        assert f"{kg:g} kg" in j["text"] or f"{kg:g} kg".replace(".", ",") in j["text"], j["text"]
    assert j["text"].count(" mg") >= 2, "una dosis por niño"


def test_la_otra_bascula_sigue_siendo_un_nino(client):
    """«La otra» de una báscula no es otro niño: con el mismo niño se sigue preguntando."""
    j = client.post(
        "/api/ask",
        json={
            "question": "En una báscula pesa 7,2 kg y en la otra 7,8 kg. ¿Cuánto paracetamol?",
            "lang": "es",
        },
    ).json()
    assert j["verification"] == "dose_two_weights", j
