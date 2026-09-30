"""Dos preguntas que se contestaban con una fuente que no decía lo contestado (30-sep-2026).

«¿Es igual de fiable la axila que el oído?» citaba la ficha de infecciones de oído, y «tengo
fiebre yo: ¿puedo seguir dándole el pecho?» afirmaba «no hay ningún problema» citando la ficha
de fiebre de MedlinePlus, que no habla de lactancia. Las dos respuestas eran plausibles y las
dos estaban sin fuente, que es lo único que el proyecto no se permite.

Faltaban las páginas del NHS que lo dicen: cómo tomar la temperatura (axila con termómetro
digital; el oído no es fiable en un bebé) y qué medicinas se pueden tomar dando el pecho, más
la de seguir dando el pecho cuando la madre se encuentra mal.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

TEMP_BEBE = "nhs_en_how_to_take_your_babys_temperature"

ENFERMA = "nhs_en_having_covid_19_symptoms_or_vaccine"

PREGUNTAS: dict[str, set[str]] = {
    "Is an ear thermometer as accurate as the armpit for my baby's temperature?": {
        TEMP_BEBE,

    },
    "How do I take my baby's temperature with a digital thermometer under the arm?": {
        TEMP_BEBE,

    },
    "I'm feeling unwell. Should I carry on breastfeeding or express instead?": {ENFERMA},
}


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    s = get_settings()
    return Retriever(
        Index(s.index_db_path),
        Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
    )


@pytest.mark.parametrize("pregunta", sorted(PREGUNTAS))
def test_la_pregunta_llega_a_la_pagina_que_lo_dice(buscador: Retriever, pregunta: str):
    esperados = PREGUNTAS[pregunta]
    hits, _ = buscador.search(pregunta, "en")
    docs = [h.chunk.doc_id for h in hits[:6]]  # los 6 que usa el motor (retrieval_top_k)
    assert esperados & set(docs), f"«{pregunta}» no alcanza {esperados}; devuelve {docs}"
