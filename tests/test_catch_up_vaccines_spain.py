"""Vacunas atrasadas de un niño de España: el calendario acelerado del CAV-AEP (12-nov-2026).

Visto el 9-nov al probar ganchos para los correos: «Mi hijo de 3 años no tiene las vacunas
puestas, ¿se las pueden poner ahora?» contestaba con nidirect y el NHS («6 en 1 hasta los 10
años», regla del Reino Unido). Faltaba una fuente española de calendarios acelerados: el
capítulo 11 del Manual de Inmunizaciones del CAV-AEP, la misma licencia que el capítulo 10.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

PREGUNTAS = [
    "Mi hijo de 3 años no tiene las vacunas puestas, ¿se las pueden poner ahora?",
    "Mi hija de 5 años tiene vacunas atrasadas, ¿cómo se ponen al día?",
    "Venimos de otro país y al niño le faltan vacunas, ¿qué hacemos?",
]


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    s = get_settings()
    return Retriever(
        Index(s.index_db_path),
        Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
        llm=None,
        top_k=s.retrieval_top_k,
        taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
    )


@pytest.mark.parametrize("pregunta", PREGUNTAS)
def test_the_spanish_catch_up_chapter_comes_up(buscador: Retriever, pregunta: str) -> None:
    hits, _ = buscador.search(pregunta, "es")
    ids = [h.chunk.chunk_id for h in hits]
    assert any(i.startswith("cavaep_es_cap_11#") for i in ids), ids
