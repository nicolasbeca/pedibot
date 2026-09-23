"""Si falta el peso, hay que pedirlo — como se pide la talla (23-sep-2026, octava tanda).

    «mi hijo tiene 4 años y mide 112 cm pero no sé cuánto pesa, ¿puedes decirme su percentil?»
    → «Talla para la edad: 112 cm → percentil 98.1 … Un solo dato dice poco.»

Con la talla suelta se calcula el percentil de talla, y eso está bien. Lo que no está bien es
callar lo que falta: el padre preguntó por el percentil de su hijo, dijo que no tenía el peso, y
la respuesta ni se lo pide ni le dice que sin él no hay percentil de peso. La frase existía en el
sentido contrario —«dime también la talla y calculo el peso para la talla»— desde el principio.
"""

from __future__ import annotations

from pedibot.bot.growth import Growth, explain
from pedibot.settings import ROOT


def _g() -> Growth:
    return Growth(ROOT / "config" / "who_growth.json")


def test_only_the_height_asks_for_the_weight() -> None:
    a = _g().assess("M", 48.0, height_cm=112.0)
    assert "weight" in a.missing
    texto = explain(a, "es", "M", 48.0)
    assert "peso" in texto.lower(), texto


def test_only_the_weight_still_asks_for_the_height() -> None:
    a = _g().assess("M", 48.0, weight_kg=17.0)
    texto = explain(a, "es", "M", 48.0)
    assert "talla" in texto.lower(), texto


def test_with_both_it_asks_for_nothing() -> None:
    a = _g().assess("M", 48.0, weight_kg=17.0, height_cm=104.0)
    assert a.missing == []


def test_the_question_is_asked_in_every_language() -> None:
    a = _g().assess("M", 48.0, height_cm=112.0)
    escritos = {
        lang: explain(a, lang, "M", 48.0)
        for lang in ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")
    }
    for lang, texto in escritos.items():
        assert "{" not in texto, (lang, texto)
    # y cada lengua escribe lo suyo: si una copiase el inglés, aquí se vería
    assert len({t.splitlines()[-2] for t in escritos.values()}) == len(escritos)
