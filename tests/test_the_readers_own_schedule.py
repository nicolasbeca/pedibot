"""El calendario de vacunas es el del país del lector, no el de otro (3-oct-2026).

Consulta real, Reino Unido, 2-oct 09:28: «should I vaccinate my child polio vaccine?» →
«In Spain's routine schedule, the polio vaccine is given… at 2, 4 and 11 months». Al padre
británico se le dio el calendario español: la pregunta no pide un calendario (no entra en la
tabla), va a las guías, y la búsqueda no sabía que el PDF del Ministerio de Sanidad sólo vale para
España. El modelo tampoco sabía dónde vive el lector.

Tres cosas, para cualquier país:
- el documento de calendario de OTRO país no entra entre las fuentes;
- el del país del lector, si está en el índice, entra;
- el modelo sabe el país del lector, y la respuesta enlaza su tabla si la tenemos.
"""

from __future__ import annotations

import pytest

from pedibot.eval import fake_engine_from_settings

ES_DOC = "msan_calendario_vacunacion_2025"
GB_DOC = "nhs_en_nhs_vaccinations_and_when_to_have_them"


@pytest.fixture(scope="module")
def engine():
    return fake_engine_from_settings()


def _docs(a) -> set[str]:
    return {c.split("#")[0] for c in a.chunk_ids}


def test_a_british_parent_gets_the_nhs_schedule_and_not_spains(engine):
    a = engine.ask("should I vaccinate my child polio vaccine?", country="GB", lang="en")
    assert ES_DOC not in _docs(a), a.chunk_ids
    assert GB_DOC in _docs(a), a.chunk_ids


def test_the_model_is_told_where_the_reader_lives(engine):
    engine.llm.calls.clear()
    engine.ask("should I vaccinate my child polio vaccine?", country="GB", lang="en")
    redactor = [u for _, u in engine.llm.calls if "PARENT MESSAGE:" in u]
    assert redactor and "READER'S COUNTRY: United Kingdom" in redactor[-1]


def test_the_answer_links_the_readers_table(engine):
    a = engine.ask("should I vaccinate my child polio vaccine?", country="GB", lang="en")
    assert a.tool is not None and a.tool.url.endswith("/vaccines/gb"), a.tool


def test_a_spanish_parent_still_gets_the_ministry(engine):
    a = engine.ask("¿hay que vacunar a mi hijo de la polio?", country="ES", lang="es")
    assert GB_DOC not in _docs(a), a.chunk_ids


@pytest.mark.parametrize("country", ["US", "KE", "IN"])
def test_nobody_else_gets_spain_or_britain_as_their_schedule(engine, country):
    a = engine.ask("should I vaccinate my child polio vaccine?", country=country, lang="en")
    assert not _docs(a) & {ES_DOC, GB_DOC}, (country, a.chunk_ids)


def test_without_a_country_nothing_is_removed(engine):
    """Sin país no hay a quién no corresponder: la búsqueda queda como estaba."""
    engine.llm.calls.clear()
    engine.ask("should I vaccinate my child polio vaccine?", country=None, lang="en")
    redactor = [u for _, u in engine.llm.calls if "PARENT MESSAGE:" in u]
    assert not any("READER'S COUNTRY" in u for u in redactor)


def test_a_question_that_is_not_about_vaccines_is_untouched(engine):
    engine.llm.calls.clear()
    engine.ask("my child has a cough at night", country="GB", lang="en")
    redactor = [u for _, u in engine.llm.calls if "PARENT MESSAGE:" in u]
    assert not any("READER'S COUNTRY" in u for u in redactor)


@pytest.mark.parametrize(
    "pregunta,doc",
    [
        ("should I vaccinate my child polio vaccine?", "nhs_en_polio"),
        ("side effects of the MMR vaccine", "nhs_en_mmr_vaccine"),
        ("does my baby need the rotavirus vaccine?", "nhs_en_rotavirus_vaccine"),
    ],
)
def test_each_nhs_vaccine_has_its_page(engine, pregunta, doc):
    a = engine.ask(pregunta, country="GB", lang="en")
    assert doc in _docs(a), a.chunk_ids
