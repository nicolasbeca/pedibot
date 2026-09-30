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
VACUNAS_ES = "cavaep_es_cap_10"  # Manual de Inmunizaciones de la AEP, cap. 10: el prematuro

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


@pytest.fixture(scope="module")
def motor():
    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.drugs import DrugCatalog
    from pedibot.bot.growth import Growth
    from pedibot.bot.llm import FakeProvider
    from pedibot.bot.triage import Triage
    from pedibot.bot.vaccines import Vaccines

    s = get_settings()
    llm = FakeProvider(lambda sys_, user: "Fake draft based on the sources [1].")
    return Engine(
        Retriever(
            Index(s.index_db_path),
            Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
            top_k=s.retrieval_top_k,
            taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
        ),
        Triage(s.config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(s.config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(s.config_dir / "drugs.yaml"),
        vaccines=Vaccines(s.config_dir / "vaccines.yaml"),
        growth=Growth(s.config_dir / "who_growth.json"),
    )


@pytest.mark.parametrize(
    "pregunta",
    [
        "Mi hija nació prematura de 32 semanas y ahora tiene 4 meses. ¿Qué edad uso para las "
        "vacunas, la real o la corregida?",
        "My daughter was born at 32 weeks and is now 4 months old. Do I use her actual age or "
        "corrected age for vaccines?",
    ],
)
def test_el_motor_entero_llega_a_la_ficha_del_prematuro(motor, pregunta: str):
    """El buscador solo la encontraba; el motor, con su desvío a los calendarios de vacunas
    («vaccines» + «age»), no la veía, y en producción el verificador acababa en silencio."""
    a = motor.ask(pregunta)
    docs = {c.split("#")[0] for c in a.chunk_ids}
    assert docs & {VACUNAS, VACUNAS_ES}, f"no llega a la ficha del prematuro; usa {sorted(docs)}"
