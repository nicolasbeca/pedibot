"""Una palabra española suelta dentro de una respuesta en otra lengua (9-oct-2026).

Consulta real 1053, un padre de EE. UU.: «My 5-year-old says he has a fever in his legs». La
respuesta, buena en lo demás, decía «it is common for the temperature not to come all the way
down after an antitérmico». Venía de la hoja de fiebre de la SEUP, traducida por el modelo, que
se dejó la palabra sin traducir. Aquí se cambia por la de la lengua del padre. En portugués
«antitérmico» es palabra propia y se deja.
"""

from __future__ import annotations

from pedibot.bot.stray_words import sin_palabras_sueltas


def test_the_real_answer_of_9_oct() -> None:
    t = "it is common for the temperature not to come all the way down after an antitérmico — that"
    assert sin_palabras_sueltas(t, "en") == (
        "it is common for the temperature not to come all the way down after a fever medicine — that"
    )


def test_plural_and_capital() -> None:
    assert sin_palabras_sueltas("Antitérmicos lower the fever.", "en") == "Fever medicines lower the fever."
    assert sin_palabras_sueltas("give antitermicos only if", "en") == "give fever medicines only if"


def test_french_and_german() -> None:
    assert "antipyrétique" in sin_palabras_sueltas("après un antitérmico", "fr")
    assert "antitérmico" not in sin_palabras_sueltas("après un antitérmico", "fr")
    assert "fiebersenkend" in sin_palabras_sueltas("nach einem Antitérmico", "de")


def test_spanish_and_portuguese_keep_their_word() -> None:
    for lang in ("es", "pt"):
        assert sin_palabras_sueltas("tras un antitérmico", lang) == "tras un antitérmico"


def test_the_engine_cleans_the_answer() -> None:
    from pedibot.bot.answer import Answer
    from pedibot.eval import fake_engine_from_settings

    eng = fake_engine_from_settings()
    eng._ask = lambda *a, **k: Answer(
        "It may not come all the way down after an antitérmico [4].",
        "routine", None, [], "en", None, None, [], "ok",
    )
    a = eng.ask("My 5-year-old says he has a fever in his legs. Is that possible?", country="US", lang="en")
    assert "antitérmico" not in a.text
    assert "after a fever medicine [4]" in a.text
