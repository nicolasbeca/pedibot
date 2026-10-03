"""Un padre que escribe en inglés recibe la página inglesa que existe (3-oct-2026).

De 385 preguntas en inglés de las baterías, 107 no traían ni una fuente en inglés, y en muchas
la página del NHS estaba en el índice: la expansión a castellano («fiebre», «cefalea») daba más
coincidencias a la SEUP. Ahora, fuera del castellano, un pasaje en la lengua del padre sube al
segundo puesto si su título lleva una palabra del padre que diga de QUÉ trata —no «baby» ni
«crying»— y que el padre no niegue («no fever»). Medido sobre las 2.688 preguntas: 17 cambian, las
17 a mejor; la referencia sigue en 103 de 106.
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
    return [h.chunk.doc_id for h in hits]


@pytest.mark.parametrize(
    "q,doc",
    [
        # consulta real, 1-oct-2026
        ("My 2-year-old has had a fever of 39 since yesterday, what should I do?", "nhs_en_fever_in_children"),
        ("my son complains about headaches every afternoon", "nhs_en_headaches"),
        ("my toddler fell and his wrist looks slightly bent", "nhs_en_broken_arm_or_wrist"),
        ("can i give ibuprofen if my child hasnt eaten anything?", "nhs_en_ibuprofen_for_children"),
        # el término inglés en los sinónimos (antes sólo tendían puente al castellano)
        ("my toddler hasnt pooped in three days but is eating normally", "nhs_en_constipation"),
        ("my breastfed baby hasnt pooped in 8 days but seems comfortable", "nhs_en_constipation"),
        ("my toddler was outside in the heat and now has a temperature of 39", "nhs_en_heat_exhaustion_heatstroke"),
        ("my toddler choked on a grape but coughed it out", "mlp_en_choking"),
    ],
)
def test_the_english_page_comes_up(buscador, q, doc):
    assert doc in _docs(buscador, q)


@pytest.mark.parametrize(
    "q,no_doc",
    [
        ("my child got shampoo in his eye and is crying", "nhs_en_soothing_a_crying_baby"),
        ("my baby is 2 months old and has 100.8 F", "nhs_en_baby_teething_symptoms"),
        ("my 2 year old is breathing very fast but has no fever", "nhs_en_fever_in_children"),
    ],
)
def test_not_by_who_or_by_what_the_parent_denies(buscador, q, no_doc):
    assert no_doc not in _docs(buscador, q)

