"""El prematuro: ¿edad real o corregida? (30-sep-2026).

«Nació de 32 semanas y tiene 4 meses: ¿qué edad uso para las vacunas y para el percentil?» se
quedaba en silencio: «no tengo información fiable». No era el motor: en 648 documentos sólo había
la ficha general de la OMS sobre el parto prematuro, que no dice nada de la edad corregida.

Y la respuesta no es una sola, que es justo por lo que un padre pregunta:

- **vacunas, con la edad REAL**: desde las 8 semanas tras nacer, «no matter how premature»
  (nidirect, OGL: el folleto del NHS y la UKHSA dice lo mismo);
- **hitos del desarrollo, con la CORREGIDA** si nació más de 3 semanas antes (CDC);
- **curvas de peso y talla, con la CORREGIDA hasta los 24 meses** (CDC, guía de las curvas).

Esto fija que cada una de las tres preguntas alcance su fuente.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

VACUNAS = "nidirect_en_childhood_immunisation_programme"
HITOS = "cdc_en_2_months"
CURVAS = "cdc_en_growth_charts_overview"

PREGUNTAS: dict[str, str] = {
    "My baby was born premature at 32 weeks. Does she get her vaccines at her actual age "
    "or her corrected age?": VACUNAS,
    "My son was born 6 weeks early. Should I use his corrected age for milestones?": HITOS,
    "How do I plot a preterm baby on the growth chart, with the corrected age?": CURVAS,
    "Premature baby weight percentile: gestation-adjusted age until what age?": CURVAS,
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
def test_la_pregunta_del_prematuro_llega_a_su_fuente(buscador: Retriever, pregunta: str):
    esperado = PREGUNTAS[pregunta]
    hits, _ = buscador.search(pregunta, "en")
    docs = [h.chunk.doc_id for h in hits[:6]]  # los 6 que usa el motor (retrieval_top_k)
    assert esperado in docs, f"«{pregunta}» no alcanza {esperado}; devuelve {docs}"


@pytest.mark.parametrize(
    "frase", ["My son was born 6 weeks early", "early signs of autism", "she wakes up early"]
)
def test_early_no_es_ear(frase: str):
    """«ear» se buscaba por prefijo y «early» empieza por «ear»: «born 6 weeks early» devolvía
    cuatro veces la hoja de otitis de la SEUP (30-sep-2026)."""
    s = get_settings()
    sin = Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml")
    assert "otitis" not in sin.expand(frase, "en")


@pytest.mark.parametrize("frase", ["my baby pulls her ear", "both ears hurt", "earache at night"])
def test_y_el_oido_se_sigue_encontrando(frase: str):
    s = get_settings()
    sin = Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml")
    assert "otitis" in sin.expand(frase, "en")
