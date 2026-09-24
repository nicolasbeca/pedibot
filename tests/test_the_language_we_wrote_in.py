"""Una respuesta en suajili no se apunta como inglesa (24-sep-2026).

Las consultas se guardan de forma anónima con su idioma, y ese campo es el único sitio donde se
ve en qué lenguas escribe la gente. Para las ocho que el sitio habla, dice la verdad. Para el
resto, no: el motor busca en inglés —porque el corpus está en inglés— y **apuntaba «en» aunque
hubiera contestado en suajili o en urdu**.

Lo que se pierde no es un detalle de registro. Es la única señal de que alguien está
escribiendo en una lengua que la web no ofrece todavía, que es justo el dato que diría en qué
idioma merece la pena crecer. Se vio revisando la octava tanda, con las respuestas en suajili y
en urdu apuntadas como inglesas.

`lang` sigue siendo el idioma con el que se buscó, porque eso es lo que explica qué fuentes
salieron. `written_lang` dice en cuál se escribió la respuesta, que es lo que leyó el padre.
"""

from __future__ import annotations

from pedibot.bot.answer import Answer


def test_the_answer_carries_the_language_it_was_written_in() -> None:
    a = Answer(
        text="x",
        level="routine",
        banner=None,
        sources=[],
        lang="en",
        prompt_version=None,
        llm=None,
        chunk_ids=[],
        verification="ok",
    )
    assert a.written_lang == "en", "sin nada dicho, lo escrito es el idioma de búsqueda"

    b = Answer(
        text="x",
        level="routine",
        banner=None,
        sources=[],
        lang="en",
        prompt_version=None,
        llm=None,
        chunk_ids=[],
        verification="ok",
        wrote_in="Swahili",
    )
    assert b.written_lang == "sw", b.written_lang


def test_the_languages_the_site_does_not_speak_have_a_code() -> None:
    """Si no sabemos el código, se guarda el nombre y no una mentira corta."""
    for nombre, codigo in (
        ("Swahili", "sw"),
        ("Urdu", "ur"),
        ("Bengali", "bn"),
        ("Italian", "it"),
        ("Polish", "pl"),
        ("Turkish", "tr"),
        ("Romanian", "ro"),
        ("Ukrainian", "uk"),
        ("Chinese", "zh"),
        ("Japanese", "ja"),
    ):
        a = Answer(
            text="x",
            level="routine",
            banner=None,
            sources=[],
            lang="en",
            prompt_version=None,
            llm=None,
            chunk_ids=[],
            verification="ok",
            wrote_in=nombre,
        )
        assert a.written_lang == codigo, (nombre, a.written_lang)


def test_an_unknown_language_is_not_silently_english() -> None:
    a = Answer(
        text="x",
        level="routine",
        banner=None,
        sources=[],
        lang="en",
        prompt_version=None,
        llm=None,
        chunk_ids=[],
        verification="ok",
        wrote_in="Quechua",
    )
    assert a.written_lang != "en", "una lengua que no conocemos no puede pasar por inglés"
    assert "quechua" in a.written_lang.lower(), a.written_lang


def test_a_swahili_question_is_not_logged_as_english() -> None:
    """De punta a punta: lo que se guarda es la lengua en que lo lee el padre.

    El motor busca en inglés cuando la lengua no es una de las ocho —el corpus está en inglés—,
    y eso está bien y no cambia. Lo que cambia es lo que se apunta.
    """
    from pedibot.bot.answer import Answer

    a = Answer(
        text="Homa ya mtoto…",
        level="routine",
        banner=None,
        sources=[],
        lang="en",
        prompt_version=None,
        llm=None,
        chunk_ids=[],
        verification="ok",
        wrote_in="Swahili",
    )
    assert a.lang == "en", "la búsqueda sigue siendo en inglés, que es donde está el corpus"
    assert a.written_lang == "sw", "pero lo que se guarda es la lengua del padre"


def test_the_eight_languages_keep_their_code() -> None:
    """Y para las ocho de la casa no cambia nada: `wrote_in` va vacío."""
    from pedibot.bot.answer import Answer

    for codigo in ("en", "es", "fr", "de", "ru", "ar", "pt", "hi"):
        a = Answer(
            text="x",
            level="routine",
            banner=None,
            sources=[],
            lang=codigo,
            prompt_version=None,
            llm=None,
            chunk_ids=[],
            verification="ok",
        )
        assert a.written_lang == codigo
