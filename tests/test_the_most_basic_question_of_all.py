"""«¿Qué número de emergencias tengo que llamar?», sin país elegido (23-sep-2026).

Está escrito en el propio código, del 20-sep: «un padre en Nigeria preguntaba el número y el
chat contestaba "no tengo información fiable sobre esto en mis fuentes" mientras el aviso de
arriba llevaba el 112 escrito». Se arregló para quien ha elegido país. Para quien no, seguía
igual, y así salió en la séptima tanda:

    «que numero de emergencias tengo que llamar?»               → no tengo información
    «estamos de viaje en un pais y no se que numero hay»        → no tengo información
    «mi movil no tiene cobertura, como contacto con emergencias?» → no tengo información

Sin país no se puede dar un número, y eso no es lo mismo que no saber nada: se dice cuáles son
los generales, se pide el país en una línea y se enlaza la página que los tiene todos.
"""

from __future__ import annotations

import pytest
from test_the_ai_reads_the_question_first import _json, _motor


@pytest.mark.parametrize(
    "q",
    [
        "que numero de emergencias tengo que llamar?",
        "estamos de viaje en un pais y no se que numero de emergencias hay",
        "a que numero llamo si se pone peor?",
        "what emergency number should I call?",
    ],
)
def test_without_a_country_it_still_answers(q: str) -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    a = motor.ask(q, lang="es", country=None)
    assert a.verification == "emergency_number", a.text
    assert "112" in a.text and "911" in a.text
    assert "no tengo información" not in a.text.lower()


def test_with_a_country_it_gives_that_country() -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    a = motor.ask("que numero de emergencias tengo que llamar?", lang="es", country="ES")
    assert a.verification == "emergency_number"
    assert "112" in a.text
