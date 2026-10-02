"""La vacuna del VPH tiene su página (2-oct-2026).

Consulta real, Reino Unido: «what are the side effects of HPV vaccine to females. Tell me the
risks as well as benefits from research data». Primero recibió una falsa alarma de convulsión
(«bene-fits», L250) y, quitada ésa, «no tengo información fiable». No había ni una página en
inglés sobre la vacuna del VPH: entran la del NHS (efectos secundarios, quién la recibe) y la del
NHS sobre por qué las vacunas son seguras, para «he leído que perjudica…».
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    s = get_settings()
    return Retriever(
        Index(s.index_db_path),
        Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
    )


@pytest.mark.parametrize(
    "pregunta",
    [
        "what are the side effects of HPV vaccine to females. Tell me the risks as well as "
        "benefits from research data",
        "Should I vaccinate HPV vaccine to my daughter? I have read the myths about it.",
        "is the HPV vaccine safe for my 12 year old?",
    ],
)
def test_the_question_reaches_the_hpv_page(buscador: Retriever, pregunta: str) -> None:
    hits, _ = buscador.search(pregunta, "en")
    docs = [h.chunk.doc_id for h in hits[:6]]
    assert "nhs_en_hpv_vaccine" in docs, docs
