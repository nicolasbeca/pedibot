"""«La caca de mi bebé es amarilla» (16-sep-2026).

Es de las preguntas que más se hacen los primeros meses y hasta hoy se contestaba con la
pregunta de aclaración —«¿qué le pasa?»— porque la taxonomía no reconocía ninguna palabra de la
frase, y en ruso, árabe e hindi no salía ni una ficha.

Además faltaba el material: la única página del corpus que lo explica es la del NHS sobre el
pañal, y estaba indexada como una página ÍNDICE de 49 palabras, con los nombres de sus pestañas
y nada más. Lo que dice, y que un padre necesita: el meconio es negro verdoso, a los pocos días
la caca pasa a amarilla o mostaza, la del pecho es líquida y no huele, la de fórmula es más
oscura y **la caca pálida puede ser señal de ictericia**.

Así que esto fija las tres cosas a la vez: que la pregunta tenga tema (sin tema, la puerta del
«fuente o silencio» sube de un término a tres y encima se pide aclaración), que el vocabulario
de las heces lleve a las fichas en las ocho lenguas, y que «cacahuete» siga sin ser caca.
"""

from __future__ import annotations

import re

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    return Retriever(
        Index(ROOT / "index" / "pedibot.db"),
        Synonyms(ROOT / "config" / "synonyms.yaml", ROOT / "config" / "drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(ROOT / "config" / "taxonomia.yaml"),
    )


#: las fichas que contestan: la del pañal del NHS y las dos de la Junta de Andalucía
FICHAS = r"nappy|cuidame|jaundice|ictericia"

CASOS = [
    ("es", "la caca de mi bebé es amarilla"),
    ("es", "mi bebé hace cacas verdes"),
    ("en", "my baby's poo is yellow"),
    ("fr", "les selles de mon bébé sont jaunes"),
    ("de", "der Stuhl meines Babys ist gelb"),
    ("ru", "у ребенка желтый стул"),
    ("ar", "براز طفلي أصفر"),
    ("hi", "मेरे बच्चे का मल पीला है"),
    ("pt", "o cocô do meu bebê está amarelo"),
]


@pytest.mark.parametrize(("lang", "pregunta"), CASOS)
def test_el_color_del_panal_encuentra_su_ficha(buscador: Retriever, lang: str, pregunta: str):
    hits, _ = buscador.search(pregunta, lang)
    ids = [h.chunk.chunk_id for h in hits]
    assert any(re.search(FICHAS, i) for i in ids[:3]), f"[{lang}] {pregunta} → {ids[:4]}"


@pytest.mark.parametrize(("lang", "pregunta"), CASOS)
def test_y_tiene_tema_asi_que_no_se_pide_aclaracion(buscador: Retriever, lang: str, pregunta: str):
    """Sin tema, `Engine.ask` devuelve las opciones de «cuéntame más» en vez de una respuesta."""
    tax = buscador.taxonomy
    assert tax is not None
    texto = pregunta + " " + " ".join(buscador.expand(pregunta, lang))
    assert tax.topic_for(texto) is not None, f"[{lang}] «{pregunta}» sigue sin tema"


def test_la_caca_palida_lleva_al_aviso_de_ictericia(buscador: Retriever):
    """Lo único de esta pregunta que puede ser grave: el NHS lo dice en esa misma página."""
    hits, _ = buscador.search("my baby's poo is pale and chalky", "en")
    ids = [h.chunk.chunk_id for h in hits]
    assert any(re.search(r"nappy|jaundice", i) for i in ids[:4]), ids[:4]


def test_el_cacahuete_no_es_caca(buscador: Retriever):
    """El candado del 14-sep: «caca» casaba por prefijo con «cacahuete» y mandaba una pregunta
    de alergia a las fichas de estreñimiento."""
    assert "deposiciones" not in buscador.expand("mi hijo es alérgico al cacahuete", "es")


def test_una_diarrea_sigue_siendo_digestivo(buscador: Retriever):
    """El vocabulario de heces no puede robarle el tema a lo que ya funcionaba: «deposiciones» y
    «heces» salen de la expansión de «diarrea», así que NO entran en la taxonomía."""
    tax = buscador.taxonomy
    assert tax is not None
    for pregunta in (
        "mi hijo de 6 años tiene diarrea y las cacas son líquidas",
        "mi niño lleva 4 días sin hacer caca y le duele",
    ):
        texto = pregunta + " " + " ".join(buscador.expand(pregunta, "es"))
        assert tax.topic_for(texto) == "digestivo", f"«{pregunta}» → {tax.topic_for(texto)}"
