"""Si hay una página en la lengua del padre que habla de lo que pregunta, sube (1-oct-2026).

Con Vikaspedia en el índice, «बच्चे को दस्त हो रहे हैं क्या करें» (diarrea) seguía trayendo
seis pasajes de la OMS en inglés, y la página en hindi sobre cómo evitar que un niño muera de
diarrea quedaba en el puesto 12, con la mitad de puntos que la sexta (L248). No es que puntúe mal:
la pregunta en hindi casa con UNA palabra de la página hindi y con las cinco que la expansión
añade en inglés en la página inglesa. Y el índice ni siquiera la tenía entre los candidatos:
sólo mira los 30 mejores por BM25 antes de aplicar los impulsos.

Lo mismo que `_one_readable_up_front` hace con la lengua que el padre puede abrir, pero un paso
antes: se busca aparte en la lengua del padre y, si hay un pasaje del MISMO TEMA que casa con sus
palabras, el mejor sube al segundo puesto. Uno sólo; el resto no se toca. Si no hay tema o el
pasaje es de otro, no sube nada: «करता» sola trajo tres páginas ajenas a la enuresis.
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
    ("pregunta", "esperado"),
    [
        ("बच्चे को दस्त हो रहे हैं क्या करें", "vikaspedia_hi_5791"),
        ("मेरे बच्चे को दमा है", "vikaspedia_hi_7255"),
    ],
)
def test_the_hindi_page_reaches_the_top_three(buscador: Retriever, pregunta: str, esperado: str):
    hits, _ = buscador.search(pregunta, "hi")
    top = [h.chunk.doc_id for h in hits[:3]]
    assert any(d.startswith(esperado) or d.startswith("vikaspedia_hi_") for d in top), top


def test_only_one_comes_up_and_the_rest_keeps_its_order(buscador: Retriever) -> None:
    hits, _ = buscador.search("बच्चे को दस्त हो रहे हैं क्या करें", "hi")
    propias = [h for h in hits if h.chunk.lang == "hi"]
    assert hits[0].chunk.lang != "hi", "el primero sigue siendo el que más puntúa"
    assert len(propias) >= 1


def test_a_page_on_another_subject_does_not_come_up(buscador: Retriever) -> None:
    hits, _ = buscador.search("बच्चा रात को बिस्तर गीला करता है", "hi")
    assert not [h.chunk.doc_id for h in hits[:3] if h.chunk.doc_id.startswith("vikaspedia")]


def test_spanish_is_not_touched(buscador: Retriever) -> None:
    """El castellano no es lengua pequeña: nada cambia para él."""
    hits, _ = buscador.search("mi hijo tiene diarrea que hago", "es")
    assert all(h.chunk.lang != "hi" for h in hits)


@pytest.mark.parametrize(
    ("pregunta", "lang", "fuera"),
    [
        # medido sobre la batería del operador: sólo con «mismo tema» subían éstas
        ("mon bebe a 3 mois et a 38 de fievre, cest grave?", "fr", "who_fr_malaria"),
        ("Малышу 2 месяца, температура 38,0 ректально", "ru", "who_ru_dengue"),
        ("o meu filho vomitou verde", "pt", "govbr_pt_hepatites"),
        ("Мой ребенок упал с кровати и теперь его вырвало", "ru", "who_ru_burns"),
        ("मेरा बच्चा 8 महीने का है और शहद खाने के बाद उल्टी कर रहा है", "hi", "vikaspedia_hi_5791"),
    ],
)
def test_the_page_has_to_be_about_what_they_ask(
    buscador: Retriever, pregunta: str, lang: str, fuera: str
) -> None:
    """Del mismo tema no basta: la fiebre de un bebé de dos meses no es la malaria. La página
    sube sólo si una palabra DEL PADRE —no de la expansión— está en su título."""
    hits, _ = buscador.search(pregunta, lang)
    assert not [h.chunk.doc_id for h in hits if h.chunk.doc_id.startswith(fuera)]
