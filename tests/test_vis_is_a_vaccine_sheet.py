"""«VIS» es la hoja de información de una vacuna (2-oct-2026).

Consulta real, EE. UU., 30-sep: «Vis translations». Con dos palabras y ningún tema conocido, el
chat contestó «¿qué te pasa?», y otra vez «no puedo confirmarlo». Teníamos 40 hojas de
Immunize.org. «VIS» es como llaman en EE. UU. a las Vaccine Information Statements de los CDC:
es una palabra del tema de vacunas y la pregunta tiene que llegar a ellas.
"""

from __future__ import annotations

import pytest

from pedibot.eval import fake_engine_from_settings


@pytest.fixture(scope="module")
def engine():
    return fake_engine_from_settings()


@pytest.mark.parametrize("q", ["Vis translations", "VIS in Swahili", "vis sheets"])
def test_a_short_question_about_vis_is_not_vague(engine, q):
    a = engine.ask(q, country="US", lang="en")
    assert a.verification != "clarify", a.text


def test_vis_does_not_catch_other_words(engine):
    from pedibot.bot.retrieval import Synonyms
    from pedibot.settings import ROOT

    syn = Synonyms(ROOT / "config" / "synonyms.yaml", ROOT / "config" / "drugs.yaml")
    assert not any("vaccine information" in t for t in syn.expand("he has a visible rash", "en"))


def test_the_taxonomy_knows_vis_is_about_vaccines():
    """En vivo, 2-oct: «VIS in Swahili» desde Kenia recibió «eso no es de PediBot». El filtro de
    fuera de tema mira la taxonomía, y la taxonomía no conocía la palabra."""
    from pedibot.ingest.classify import Taxonomy
    from pedibot.settings import ROOT

    tax = Taxonomy(ROOT / "config" / "taxonomia.yaml")
    assert tax.topic_for("VIS in Swahili") == "vacunas"
    assert tax.topic_for("a visible rash after the visit") != "vacunas"


# En vivo, 2-oct, tras los dos arreglos de arriba: «VIS in Swahili» recibió «no tengo información
# fiable». Quien pregunta así quiere la lista de hojas, y una lista con enlaces no la redacta el
# modelo: sale del catálogo, como el calendario de vacunas.


def test_asking_for_vis_in_a_language_lists_those_sheets(engine):
    a = engine.ask("VIS in Swahili", country="KE", lang="en")
    assert a.verification == "vis_list"
    assert a.text.count("https://www.immunize.org/") >= 20
    assert "/swahili_" in a.text and "/arabic_" not in a.text
    assert "Immunize.org" in a.text


def test_asking_for_vis_without_a_language_lists_the_three(engine):
    a = engine.ask("Vis translations", country="US", lang="en")
    assert a.verification == "vis_list"
    for name in ("Swahili", "Arabic", "Hindi"):
        assert name in a.text


def test_a_vaccine_question_is_not_a_vis_list(engine):
    a = engine.ask("is the rotavirus vaccine safe for my baby?", country="US", lang="en")
    assert a.verification != "vis_list"


def test_the_list_is_in_the_parents_language(engine):
    a = engine.ask("hojas VIS en árabe", country="ES", lang="es")
    assert a.verification == "vis_list"
    assert "Immunize.org" in a.text and "/arabic_" in a.text
    assert "hojas" in a.text.lower()
