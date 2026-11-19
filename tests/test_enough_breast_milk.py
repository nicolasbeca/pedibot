"""«¿Cómo sé si mi bebé de pecho toma suficiente leche?» llega a la cifra (19-nov-2026).

Visto al probar ganchos para la tanda del 19-nov (prueba 1318, EE. UU.): «How do I know my
breastfed newborn is getting enough milk?» traía las fórmulas infantiles de MedlinePlus y la
hoja de la OMS, y el redactor contestaba que ningún pasaje lo dice, con la marca «NO_SOURCE»
a la vista del padre. El corpus sí lo tiene: «An infant who is drinking enough will produce 6 to
8 wet diapers in a 24-hour period» (MedlinePlus) y «sechs- bis achtmal nasse Windeln» (BIÖG).
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
    ("How do I know my breastfed newborn is getting enough milk?", "en"),
    ("How can I tell if my baby is getting enough breast milk?", "en"),
    ("¿Cómo sé si mi bebé toma suficiente leche del pecho?", "es"),
    ("Como sei se meu bebê está mamando o suficiente?", "pt"),
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


def test_a_cited_text_that_ends_in_the_signal_is_the_signal() -> None:
    """La 1318 citaba dos pasajes y acababa en «NO_SOURCE»: eso es la señal, no una respuesta."""
    from pedibot.bot.answer import _dice_sin_fuente

    texto = (
        "I can't tell you from these pages how to know your newborn is getting enough milk. "
        "The WHO recommends exclusive breastfeeding for the first 6 months [2]. But none of "
        "the passages describes the signs of adequate intake. NO_SOURCE"
    )
    assert _dice_sin_fuente(texto)
    assert _dice_sin_fuente(texto + ".")
    # en medio de una frase con cita sigue sin serlo (test_a_second_search_with_the_ai_words)
    assert not _dice_sin_fuente("Según el NHS [1], NO_SOURCE no aplica.")
