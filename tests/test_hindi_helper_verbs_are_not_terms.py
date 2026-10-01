"""En hindi, el verbo auxiliar no es un término de búsqueda (1-oct-2026).

Con las 19 páginas de Vikaspedia, la primera prosa en hindi del índice, «बच्चा रात को बिस्तर
गीला करता है» (el niño moja la cama por la noche) trajo tres páginas de Vikaspedia que no hablan
de eso: las tres casaban sólo con «करता» («hace»), y el impulso a las lenguas pequeñas las subía
por encima de la hoja de la enuresis. Hasta ese día no había texto en hindi con el que casar y
nadie lo vio. Son las palabras que acompañan a cualquier frase, como «does» o «hace».
"""

from __future__ import annotations

import pytest

from pedibot.index.store import query_terms


@pytest.mark.parametrize(
    "palabra",
    ["करता", "करती", "करते", "करें", "चाहिए", "सकता", "सकते", "अपने", "अपना", "कोई", "कुछ", "जब"],
)
def test_the_helper_word_is_not_a_term(palabra: str) -> None:
    assert palabra not in query_terms(f"बिस्तर {palabra}")


def test_the_bedwetting_question_keeps_its_words() -> None:
    terms = query_terms("बच्चा रात को बिस्तर गीला करता है")
    assert "बिस्तर" in terms and "गीला" in terms
    assert "करता" not in terms
