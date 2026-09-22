"""Las dos «gotas» de la lista, y cuál es la tuya (22-sep-2026).

El operador lo contó en CHIFA el 22 de septiembre, con su propio error delante: las gotas de
paracetamol son **100 mg/5 ml en Etiopía** y **100 mg/ml en España**, cinco veces más fuertes.
Un padre en Adís Abeba lee «drops» en su bote, mira la lista de la calculadora y encuentra dos
líneas que empiezan igual:

    – drops 100 mg/5 ml: 9 ml
    – drops 100 mg/ml: 1.8 ml

Desde el 20-sep las de su país van primero, que ayuda y no basta: **nada dice cuál es la suya**.
Nueve líneas de mililitros parecidos a las tres de la madrugada es justo donde se lee la que no
es, y aquí equivocarse es dar cinco veces la dosis o la quinta parte.

Así que las de su país se agrupan y se dicen por su nombre, con el país escrito.
"""

from __future__ import annotations

from pedibot.bot.dose import calculate, format_result
from pedibot.bot.drugs import DrugCatalog
from pedibot.settings import ROOT

CATALOGO = DrugCatalog(ROOT / "config" / "drugs.yaml")


NOMBRES = {"ET": "Ethiopia", "ES": "Spain"}


def _texto(country: str, lang: str = "en") -> str:
    """Lo mismo que hace el motor: las formas de su país y el nombre del país."""
    from pedibot.bot.dose import bottles_in_country

    return format_result(
        calculate("paracetamol", 12.0, None),
        lang,
        country_forms=bottles_in_country(CATALOGO, "paracetamol", country),
        country_name=NOMBRES.get(country),
    )


def test_the_ethiopian_bottles_are_named_as_such() -> None:
    t = _texto("ET")
    assert "Ethiopia" in t, t
    # la línea de SUS gotas está en el grupo de su país, y la española no
    suyas = t.split("Sold in Ethiopia:")[1].split("Other strengths:")[0]
    assert "drops 100 mg/5 ml" in suyas
    assert "drops 100 mg/ml" not in suyas


def test_the_spanish_bottles_are_the_spanish_ones() -> None:
    t = _texto("ES")
    suyas = t.split("Sold in Spain:")[1].split("Other strengths:")[0]
    assert "drops 100 mg/ml" in suyas


def test_without_a_country_nothing_is_marked() -> None:
    t = _texto("")
    assert "Ethiopia" not in t and "Spain" not in t
    assert "drops 100 mg/5 ml" in t and "drops 100 mg/ml" in t


def test_every_strength_is_still_there() -> None:
    """Marcar las de su país no puede esconder las demás: el bote de un viaje, el que trajo la
    abuela, el que compró en la farmacia de al lado del aeropuerto."""
    con = _texto("ET")
    sin = _texto("")
    for linea in sin.splitlines():
        if linea.strip().startswith("–"):
            assert linea.strip() in con, linea
