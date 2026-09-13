"""«No gana peso» no es un trastorno de la conducta alimentaria (13-sep-2026).

Visto en vivo tras publicar los percentiles: «mi hijo de 3 años está muy delgado y no gana peso»
recibía el enlace a la curva de su país y un texto que decía «no tengo información fiable». Medido
en las ocho lenguas, la pregunta llegaba a donde no era:

- castellano → **trastornos de la conducta alimentaria** del SEUP (la clave «peso» se expande a
  «conducta alimentaria» y «obesidad», que es razonable para un adolescente y no para un niño de 3);
- inglés y alemán → **reflujo y cólicos**; francés → **drepanocitosis**; portugués → **polio**;
- «mi bebé no engorda» → **nada**.

Las fichas existían: la del NHS sobre el peso del bebé («la ganancia de peso», «cruzar dos líneas de
centil: habla con tu visitador de salud») y la de la OMS sobre malnutrición en cinco lenguas.
Faltaban las palabras con que lo dice un padre.
"""

from __future__ import annotations

import pytest

from pedibot.bot.growth import is_growth_question
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import ROOT

BUENAS = ("nhs_en_baby_height_and_weight", "_malnutrition", "_child_growth_standards")
MALAS = ("seup_tca", "reflux", "colic", "colico", "sickle", "poliomielite", "eatingdisorder")

QS = [
    ("es", "mi hijo de 3 años está muy delgado y no gana peso"),
    ("es", "mi bebé no engorda"),
    ("en", "my baby is not gaining weight"),
    ("en", "my toddler is very skinny, should I worry?"),
    ("fr", "mon bébé ne prend pas de poids"),
    ("de", "mein Baby nimmt nicht zu"),
    ("ru", "ребёнок плохо набирает вес"),
    ("ar", "طفلي نحيف جدا ولا يزداد وزنه"),
    ("pt", "o meu bebé não ganha peso"),
    ("hi", "मेरा बच्चा बहुत दुबला है और वजन नहीं बढ़ रहा"),
]


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    return Retriever(
        Index(ROOT / "index/pedibot.db"),
        Synonyms(ROOT / "config/synonyms.yaml", ROOT / "config/drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(ROOT / "config/taxonomia.yaml"),
    )


@pytest.mark.parametrize(("lang", "q"), QS)
def test_llega_a_la_ficha_del_peso_y_no_a_otra_cosa(buscador: Retriever, lang: str, q: str):
    hits, _ = buscador.search(q, lang)
    top = [h.chunk.doc_id for h in hits[:3]]
    assert any(any(b in d for b in BUENAS) for d in top), f"«{q}» ({lang}) → {top}"
    assert not any(m in top[0] for m in MALAS), f"«{q}» ({lang}) abre con {top[0]}"


@pytest.mark.parametrize(("lang", "q"), QS)
def test_y_el_chat_enlaza_la_curva(lang: str, q: str):
    assert is_growth_question(q), (lang, q)
