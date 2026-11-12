"""«¿Cuántos pañales mojados tiene que hacer?» llega a la cifra (12-nov-2026).

Visto el 9-nov al probar ganchos para los correos: el chat contestaba «no hay una cifra exacta»
y el corpus la tenía. MedlinePlus («An infant who is drinking enough will produce 6 to 8 wet
diapers in a 24-hour period») y el BIÖG («sechs- bis achtmal nasse Windeln»). La búsqueda en
castellano se iba a la deshidratación y a la gastroenteritis, y en inglés a cómo cambiar un pañal.
"""

from __future__ import annotations

import re

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

CON_CIFRA = re.compile(
    r"mlp_en_002004#behavior|bioeg_de_0_12_monate_verdauung|bioeg_de_babys_pflege_wickeln"
)

PREGUNTAS = [
    ("¿Cuántos pañales mojados tiene que hacer mi recién nacido al día?", "es"),
    ("cuantos pañales moja un bebé de 2 semanas", "es"),
    ("How many wet nappies should my newborn have a day?", "en"),
    ("How many wet diapers should a newborn have?", "en"),
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


@pytest.mark.parametrize("pregunta,lang", PREGUNTAS)
def test_the_count_comes_up(buscador: Retriever, pregunta: str, lang: str) -> None:
    hits, _ = buscador.search(pregunta, lang)
    ids = [h.chunk.chunk_id for h in hits]
    assert any(CON_CIFRA.search(i) for i in ids), ids
