"""La manzanilla «para los gases» llega a la hoja de cólicos de la SEUP (9-nov-2026).

Probando ganchos para la decimonovena tanda: «¿Puedo darle manzanilla a mi bebé de 3 semanas
para los gases?» salía sin fuente («no tengo información fiable»), y la búsqueda traía
prematuros y cuidados del recién nacido. Con «tiene gases, ¿le puedo dar manzanilla?» (1226) sí
llegaba a seup_colico, que es la que dice que no se dé nada de farmacia, parafarmacia o
herbolario. Era la misma pregunta del correo a Alba Lactancia del 6-nov.

«gases» y los remedios de infusión no tendían ningún puente a «cólico del lactante» en
config/synonyms.yaml; sólo «llora» y «llanto» lo hacían.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

PREGUNTAS = [
    ("¿Puedo darle manzanilla a mi bebé de 3 semanas para los gases?", "es"),
    ("¿Le doy agua de anís a mi bebé de un mes para los gases?", "es"),
    ("Mi bebé de 3 semanas tiene muchos gases, ¿qué hago?", "es"),
    ("Posso dar chá de erva-doce para os gases do meu bebê de 3 semanas?", "pt"),
    ("Posso dar chá de camomila para cólica de recém-nascido?", "pt"),
    ("Can I give chamomile tea to my 3 week old baby for gas?", "en"),
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


@pytest.mark.parametrize(("pregunta", "lang"), PREGUNTAS)
def test_gas_and_herbal_remedies_reach_the_colic_sheet(
    buscador: Retriever, pregunta: str, lang: str
) -> None:
    hits, _ = buscador.search(pregunta, lang)
    ids = [h.chunk.chunk_id for h in hits]
    assert any(i.startswith("seup_colico#") for i in ids), ids


def test_gastroenteritis_is_not_gas() -> None:
    """«gas» por prefijo cogería «gastroenteritis»: el disparador va con palabra entera."""
    s = get_settings()
    syn = Synonyms(s.config_dir / "synonyms.yaml")
    assert "colic" not in " ".join(syn.expand("my baby has gastroenteritis", "en")).lower()
    assert "cólico" not in " ".join(syn.expand("tiene gastroenteritis", "es")).lower()
