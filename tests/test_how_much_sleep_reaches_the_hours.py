"""«How much should my baby sleep?» llega a las horas (22-oct-2026).

Consulta real desde el Reino Unido el 21-oct, dos veces seguidas (1067 y 1068): la respuesta no
daba ni una cifra y la segunda, desde el manual chileno, decía que los padres «should not
intervene» cuando el bebé se despierta. El corpus tenía la respuesta —el NHS: un recién nacido
«around 18 hours», de 6 a 12 meses «around 15 hours»; la OMS: 14–17 h de 0 a 3 meses y 12–16 h
de 4 a 11— pero la búsqueda no llegaba: «sleep» en inglés sólo tendía el puente al castellano
(«sueño», «dormir»), y se traía el manual chileno y la hoja de la cefalea. «dormir» sí llevaba a
«hours of sleep»; la misma pregunta en inglés, no.
"""

from __future__ import annotations

import re

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

#: los pasajes que dan las horas de sueño por edad
CON_HORAS = re.compile(
    r"nhs_en_helping_your_baby_to_sleep#(newborn_sleep_needs|baby_sleep_at_\d)"
    r"|who_physical_activity_under5#(14_17hours|summary_of_evidence)"
)

PREGUNTAS = [
    "How much should my baby sleep?",
    "how many hours should a newborn sleep",
    "how much sleep does a 4 month old need",
    "how long should my baby sleep at night",
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
def test_the_hours_by_age_come_up(buscador: Retriever, pregunta: str) -> None:
    hits, _ = buscador.search(pregunta, "en")
    ids = [h.chunk.chunk_id for h in hits]
    assert any(CON_HORAS.search(i) for i in ids), ids


def test_the_chilean_manual_does_not_lead(buscador: Retriever) -> None:
    hits, _ = buscador.search("How much should my baby sleep?", "en")
    assert hits and hits[0].chunk.lang == "en", [h.chunk.chunk_id for h in hits]
    assert not any("seup_cefalea" in h.chunk.chunk_id for h in hits)
