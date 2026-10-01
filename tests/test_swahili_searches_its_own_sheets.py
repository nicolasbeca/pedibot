"""Una pregunta en suajili busca también en suajili (1-oct-2026).

Hasta hoy no había un solo documento en suajili en el índice, y una pregunta en suajili se
buscaba sólo con su reescritura inglesa: era lo correcto, porque no había nada más que encontrar.
El 30-sep Immunize.org nos dio permiso para sus hojas de vacunas traducidas (ops/PERMISOS.md) y
entraron 21 en suajili. Si la búsqueda siguiera siendo sólo en inglés, un padre de Kisumu que
pregunta por «chanjo ya surua» seguiría recibiendo la hoja inglesa del sarampión, con la suya en
el índice sin que nadie la encontrase.

Así que, para una lengua que tiene corpus aunque la web no la hable todavía, la búsqueda lleva
las dos cosas: las palabras del padre, con su lengua para que el índice prefiera sus documentos,
y la reescritura inglesa, para que siga llegando a todo lo que sólo está en inglés.
"""

from __future__ import annotations

from test_the_ai_reads_the_question_first import _json, _motor

from pedibot.bot.answer import CORPUS_LANGS, SUPPORTED_LANGS

PREGUNTA = "mtoto wangu wa mwaka mmoja anahitaji chanjo ya surua lini"


def _suajili():  # noqa: ANN202
    return _motor(
        _json(
            lang="sw",
            lang_name="Swahili",
            query_en="When does my one-year-old need the measles vaccine?",
            query_es="¿Cuándo necesita mi hijo de un año la vacuna del sarampión?",
            keywords=["measles vaccine", "MMR", "vacuna sarampión"],
        )
    )


def test_swahili_has_a_corpus_but_not_a_website_yet() -> None:
    assert "sw" in CORPUS_LANGS
    assert "sw" not in SUPPORTED_LANGS, "la web en suajili es otra decisión, no ésta"


def test_a_swahili_question_searches_with_its_own_words_and_language() -> None:
    motor, visto = _suajili()
    motor.ask(PREGUNTA, lang="en")
    q, lang, push = visto["busquedas"][0]
    assert lang == "sw", "con su lengua, para que el índice prefiera las hojas en suajili"
    assert "surua" in q, f"buscó sin las palabras del padre: {q}"
    assert "measles" in q.lower(), f"y sin la reescritura inglesa: {q}"
    assert "MMR" in push


def test_it_is_still_answered_in_swahili() -> None:
    motor, visto = _suajili()
    motor.ask(PREGUNTA, lang="en")
    assert "ANSWER LANGUAGE: Swahili" in visto["redactor"][-1]


def test_a_language_without_a_corpus_is_searched_in_english_as_before() -> None:
    """El italiano no tiene ni web ni documentos: sigue buscando sólo con la reescritura."""
    motor, visto = _motor(
        _json(
            query_en="My 4-year-old son has had a fever for two days.",
            keywords=["fever", "fiebre"],
        )
    )
    motor.ask("Mio figlio di 4 anni ha la febbre da due giorni", lang="en")
    q, lang, _ = visto["busquedas"][0]
    assert lang == "en"
    assert "febbre" not in q


def test_surua_finds_the_mmr_sheet_that_says_ukambi() -> None:
    """La madre escribe «surua»; la hoja de la triple vírica de Immunize.org dice «ukambi».

    Medido el 1-oct: la hoja salía quinta, por detrás de la varicela y la gripe. Contra el índice
    de verdad, con la misma búsqueda que hace el motor para el suajili.
    """
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.index.store import Index
    from pedibot.ingest.classify import Taxonomy
    from pedibot.settings import get_settings

    s = get_settings()
    r = Retriever(
        Index(s.index_db_path),
        Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
    )
    hits, _ = r.search(
        f"{PREGUNTA} When does my one-year-old need the measles vaccine?",
        "sw",
        push=["measles vaccine", "MMR"],
    )
    top = [h.chunk.doc_id for h in hits[:3]]
    assert any(d in ("cdcvis_sw_mmr", "cdcvis_sw_mmrv") for d in top), top
