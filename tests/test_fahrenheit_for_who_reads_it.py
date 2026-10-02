"""Los grados en las unidades del padre (2-oct-2026).

Del panel, 30-sep y 1-oct, desde EE. UU.: «my 2-year-old has had a fever of 39» recibió «38 °C or
more counts as a high temperature», y «my 3 year old has a temperature of 110 degree celsius»
recibió «110 °C is not a real body temperature». Las guías están en Celsius; un padre de EE. UU.
piensa en Fahrenheit, y 110 sólo tiene sentido en °F (43,3 °C). Las cifras se convierten aquí,
sin modelo: una conversión es aritmética y no se le pide a nadie que la redacte.
"""

from __future__ import annotations

from pedibot.bot.temperature import con_fahrenheit, lee_en_fahrenheit, nota_de_conversion


def test_us_parents_read_fahrenheit_too() -> None:
    assert lee_en_fahrenheit("my 2-year-old has had a fever of 39", "US")
    assert lee_en_fahrenheit("fever", "LR")
    assert not lee_en_fahrenheit("fièvre de 39", "FR")
    assert not lee_en_fahrenheit("fever of 39", None)


def test_writing_in_fahrenheit_counts_anywhere() -> None:
    assert lee_en_fahrenheit("fever of 101 F", "GB")
    assert lee_en_fahrenheit("temp 102.5°F", None)
    assert lee_en_fahrenheit("he has 101 fahrenheit", "ES")
    assert lee_en_fahrenheit("a temperature of 110 degree celsius", None)  # 110 °C no existe
    assert not lee_en_fahrenheit("he weighs 101 pounds", None)  # no es una temperatura
    assert not lee_en_fahrenheit("fiebre de 39,5", "ES")


def test_every_celsius_figure_gets_its_fahrenheit() -> None:
    t = "A high temperature is 38°C or more, and 37.5 °C under the arm [3]."
    assert con_fahrenheit(t) == (
        "A high temperature is 38°C (100.4 °F) or more, and 37.5 °C (99.5 °F) under the arm [3]."
    )


def test_a_decimal_comma_stays_a_comma() -> None:
    assert con_fahrenheit("fiebre de 38,5 °C") == "fiebre de 38,5 °C (101,3 °F)"


def test_it_is_not_converted_twice() -> None:
    t = con_fahrenheit("38 °C")
    assert con_fahrenheit(t) == t


def test_impossible_celsius_is_read_as_fahrenheit() -> None:
    assert nota_de_conversion("my 3 year old has a temperature of 110 degree celsius") == (
        "110 °F = 43.3 °C"
    )
    assert nota_de_conversion("fever of 101") == "101 °F = 38.3 °C"
    assert nota_de_conversion("fiebre de 39") is None
    assert nota_de_conversion("he weighs 101 pounds") is None


def _engine_que_dice(texto: str):
    from pedibot.bot.answer import Answer
    from pedibot.eval import fake_engine_from_settings

    eng = fake_engine_from_settings()
    eng._ask = lambda *a, **k: Answer(texto, "routine", None, [], "en", None, None, [], "ok")
    return eng


def test_the_engine_converts_for_a_us_parent() -> None:
    eng = _engine_que_dice("A high temperature is 38 °C or more [2].")
    a = eng.ask("my 2 year old has a fever of 39 since yesterday", country="US", lang="en")
    assert "38 °C (100.4 °F)" in a.text
    a = eng.ask("my 2 year old has a fever of 39 since yesterday", country="GB", lang="en")
    assert "°F" not in a.text


def test_the_engine_opens_with_the_conversion() -> None:
    eng = _engine_que_dice("110 °C is not a real body temperature; measure again [1].")
    a = eng.ask("my 3 year old has a temperature of 110 degree celsius", country="US", lang="en")
    assert a.text.startswith("110 °F = 43.3 °C")


def test_celsius_written_without_the_degree_sign() -> None:
    """En vivo, 2-oct: el modelo escribió «A temperature of 39C» y se quedó sin su °F."""
    assert con_fahrenheit("A temperature of 39C is high") == "A temperature of 39C (102.2 °F) is high"
    assert con_fahrenheit("38 degrees C or more") == "38 degrees C (100.4 °F) or more"
    assert con_fahrenheit("give 10C of water") == "give 10C of water"  # no es del cuerpo
