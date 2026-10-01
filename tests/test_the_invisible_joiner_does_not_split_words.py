"""El ZWJ invisible no parte las palabras en hindi (1-oct-2026).

Vikaspedia escribe «दस्‍त» (diarrea) con un ZERO WIDTH JOINER entre la media consonante y la
siguiente: se ve igual que «दस्त», pero el tokenizador no lo cuenta como letra y lo partía en
«दस्» + «त». Un padre que teclea «दस्त» no casaba nunca con esa página, que es justo la de cómo
evitar que un niño muera de diarrea. Lo mismo «बच्‍चों» (niños) y «स्‍वास्‍थ्‍य» (salud), que
están en casi todas.

El ZWJ y el ZWNJ sólo deciden cómo se DIBUJA la conjunción, nunca qué palabra es: se quitan al
limpiar el texto que entra al índice y al plegar la pregunta que lo busca.
"""

from __future__ import annotations

from pedibot.index.store import _TOKEN, fold, query_terms
from pedibot.ingest.clean import normalize_line

CON_ZWJ = "बच्‍चों में दस्‍त"
SIN_ZWJ = "बच्चों में दस्त"


def test_the_cleaned_text_has_no_joiner() -> None:
    assert normalize_line(CON_ZWJ) == SIN_ZWJ
    assert normalize_line("a‌b") == "ab"


def test_the_word_is_one_token() -> None:
    assert "दस्त" in _TOKEN.findall(fold(CON_ZWJ))


def test_the_question_and_the_page_meet() -> None:
    assert query_terms(CON_ZWJ) == query_terms(SIN_ZWJ)


def test_a_control_character_from_the_pdf_becomes_a_space() -> None:
    """La VIS de rotavirus en suajili salió citada en vivo como «5. \x07Na je, kukiwa…» (1-oct).

    El \x07 viene de la viñeta del PDF, y estaba en 221 pasajes de 48 documentos. Se cambia por
    un espacio y no se borra: «palabra\x07palabra» no puede convertirse en una sola palabra.
    """
    assert normalize_line("5. \x07Na je") == "5. Na je"
    assert normalize_line("homa\x0bkali") == "homa kali"
    assert normalize_line("a\tb") == "a b"
