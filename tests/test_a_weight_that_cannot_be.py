"""Catorce kilos a los seis meses no es «dentro de lo normal» (23-sep-2026, octava tanda).

    «mi hijo tiene 6 meses y pesa 14 kilos, dime el percentil»
    → «Peso para la edad: 14 kg → percentil 100 (z 5.77), dentro de lo normal.»

El peso para la edad sólo tenía cortes por abajo, porque es así como lo usa la OMS: ese indicador
no sirve para clasificar el sobrepeso —para eso están el peso para la talla y el IMC—. Pero «no
clasifica» no es «es normal». Un z de 5,77 con la coletilla tranquilizadora es la peor de las dos
respuestas posibles: o el padre se equivocó al teclear, o su hijo tiene algo que mirar, y en los
dos casos lo que hay que decir es que ese número se sale de la gráfica.
"""

from __future__ import annotations

from pedibot.bot.growth import Growth, describe, explain
from pedibot.settings import ROOT


def _g() -> Growth:
    return Growth(ROOT / "config" / "who_growth.json")


def test_a_weight_off_the_chart_is_not_normal() -> None:
    a = _g().assess("M", 6.0, weight_kg=14.0)
    wfa = next(i for i in a.indicators if i.name == "wfa")
    assert wfa.z > 3
    assert wfa.flag != "normal", wfa

    texto = explain(a, "es", "M", 6.0)
    linea = next(x for x in texto.split("\n") if "Peso para la edad" in x)
    assert "dentro de lo normal" not in linea, linea


def test_a_height_off_the_chart_is_not_normal_either() -> None:
    a = _g().assess("M", 6.0, height_cm=85.0)
    lhfa = next(i for i in a.indicators if i.name == "lhfa")
    assert lhfa.z > 3
    assert lhfa.flag != "normal", lhfa


def test_an_ordinary_child_still_reads_as_normal() -> None:
    a = _g().assess("M", 6.0, weight_kg=7.9, height_cm=67.6)
    for i in a.indicators:
        assert i.flag == "normal", i
    assert "dentro de lo normal" in explain(a, "es", "M", 6.0)


def test_the_new_label_is_written_in_every_language() -> None:
    a = _g().assess("M", 6.0, weight_kg=14.0)
    for lang in ("en", "es", "fr", "de", "ru", "ar", "pt", "hi"):
        d = describe(a, lang)
        lineas = d["indicators"]
        assert isinstance(lineas, list)
        etiqueta = str(lineas[0]["flag_label"])
        assert etiqueta and "{" not in etiqueta, (lang, etiqueta)
        assert etiqueta != str(describe(a, "en")["indicators"][0]["flag_label"]) or lang == "en"
