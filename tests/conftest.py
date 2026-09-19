from __future__ import annotations

import os
from pathlib import Path

import pytest

# AVG on the dev machine injects SSLKEYLOGFILE and kills Python processes that open TLS (L06).
os.environ.pop("SSLKEYLOGFILE", None)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
FUENTES = ROOT / "FUENTES"


@pytest.fixture(scope="session")
def config_dir() -> Path:
    return CONFIG


@pytest.fixture(scope="session")
def fuentes_dir() -> Path:
    if not FUENTES.exists() or not any(FUENTES.rglob("*.pdf")):
        pytest.skip("FUENTES/ PDFs not available")
    return FUENTES


@pytest.fixture
def app_con_familia(tmp_path: Path):
    """La API entera con una cuenta de familia detrás (19-sep-2026).

    Vive aquí y no en el fichero de la prueba porque montar el motor son veinte líneas que ya
    estaban repetidas en `test_api.py`, y porque lo que se prueba con esto —que el chat conteste
    por la edad de Laura sin que nadie la escriba— va a necesitarla desde más de un sitio.

    El índice lleva una sola ficha, de vacunas, que es de lo que se pregunta.
    """
    from fastapi.testclient import TestClient

    from pedibot.api import ApiConfig, create_app
    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.drugs import DrugCatalog
    from pedibot.bot.llm import FakeProvider
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.bot.triage import Triage
    from pedibot.family.store import FamilyStore
    from pedibot.index.store import Index, build_index
    from pedibot.ingest.classify import Taxonomy
    from pedibot.ingest.schema import Chunk
    from pedibot.ops.store import OpsStore

    db = tmp_path / "i.db"
    build_index(
        [
            Chunk(
                chunk_id="aep_vacunas#s#1",
                doc_id="aep_vacunas",
                org="AEP",
                doc_title="Calendario de vacunaciones",
                year=2025,
                lang="es",
                section="Calendario",
                pages=[1],
                text=(
                    "A los 12 meses se administran la triple vírica y la vacuna frente al "
                    "meningococo C. A los 18 meses, la cuarta dosis de hexavalente."
                ),
                topic="vacunas",
                doc_type="hoja_padres",
                evidence="sociedad_cientifica",
                usage="publico",
                source_url="https://vacunasaep.org/calendario",
                source_hash="h",
                n_words=30,
            )
        ],
        db,
    )
    engine = Engine(
        Retriever(
            Index(db),
            Synonyms(CONFIG / "synonyms.yaml"),
            taxonomy=Taxonomy(CONFIG / "taxonomia.yaml"),
        ),
        Triage(CONFIG / "red_flags.yaml"),
        FakeProvider("A los 18 meses toca la cuarta de hexavalente, según la AEP [1]."),
        EmergencyNumbers(CONFIG / "emergency_numbers.yaml"),
        drugs=DrugCatalog(CONFIG / "drugs.yaml"),
    )
    app = create_app(
        engine,
        OpsStore(tmp_path / "ops.db"),
        ApiConfig(
            allowed_origins=["http://localhost:4321"],
            rate_limit_per_10min=50,
            rate_limit_per_day=200,
            max_daily_llm_usd=2.0,
        ),
        family=FamilyStore(tmp_path / "familias.db"),
    )
    return TestClient(app, headers={"x-pedibot-client": "test"})
