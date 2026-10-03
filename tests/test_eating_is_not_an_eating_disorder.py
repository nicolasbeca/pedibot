"""«After eating» no es un trastorno de la conducta alimentaria (3-oct-2026).

Desde el primer commit, «eating» se ampliaba a «conducta alimentaria»: «my daughter has swollen
lips after eating egg» salía con la ficha de anorexia de la SEUP y el tema de salud mental, sin
una sola de alergia. Siete preguntas de las baterías cambiaban, las siete a mejor.
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


def _docs(buscador, q, lang="en"):
    hits, _ = buscador.search(q, lang)
    return {h.chunk.doc_id for h in hits}


@pytest.mark.parametrize(
    "q",
    [
        "my daughter has swollen lips after eating egg",
        "my toddler's stool is orange after eating lots of carrots",
        "my toddler hasnt pooped in three days but is eating normally",
        "my toddler keeps coughing while eating meat",
    ],
)
def test_eating_something_does_not_bring_eating_disorders(buscador, q):
    assert "seup_tca" not in _docs(buscador, q)


def test_the_egg_brings_the_allergy(buscador):
    docs = _docs(buscador, "my daughter has swollen lips after eating egg")
    assert docs & {"nhs_en_food_allergy", "mlp_es_foodallergy", "nhs_en_allergies"}, docs


@pytest.mark.parametrize(
    "q,lang",
    [
        ("I think my teenage daughter has an eating disorder", "en"),
        ("my 14 year old might have anorexia", "en"),
        ("creo que mi hija tiene anorexia", "es"),
        ("my son is making himself sick after meals, could it be bulimia?", "en"),
    ],
)
def test_a_real_eating_disorder_still_finds_it(buscador, q, lang):
    docs = _docs(buscador, q, lang)
    assert docs & {"seup_tca", "mlp_en_eatingdisorders", "who_es_adolescent_mental_health"}, docs
