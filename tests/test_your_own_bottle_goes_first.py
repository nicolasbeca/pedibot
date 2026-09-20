"""Si el padre dice su marca, su bote va el primero (21-sep-2026).

Probando las marcas africanas recién metidas: «how much Emzor paracetamol syrup for a 10 kg
baby?» devolvía la dosis correcta y ocho líneas de concentraciones, con la suya —125 mg/5 ml— en
segundo lugar y sin nombre. El sitio **sabía** que había dicho Emzor: lo resolvía para elegir la
molécula y después tiraba el dato.

Por qué importa más de lo que parece: «6,2 ml» y «6 ml» están una encima de otra y son dos botes
distintos. Ocho líneas de mililitros parecidos, de madrugada, es exactamente donde se lee la que
no es.

Y lo que NO se hace, que es la otra mitad de la decisión: **no se esconden las demás**. La misma
marca vende más de un bote y el padre puede tener otro; lo que se hace es poner el suyo delante
y con su nombre, como al explicárselo en voz alta.
"""

from __future__ import annotations

import pytest

from pedibot.bot.dose import calculate, format_result
from pedibot.bot.drugs import DrugCatalog
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def catalogo() -> DrugCatalog:
    return DrugCatalog(ROOT / "config" / "drugs.yaml")


@pytest.mark.parametrize(
    ("escrito", "molecula", "kg", "concentracion"),
    [
        # la de Nigeria: 125 y no 120, y esos cinco miligramos son justo los que confunden
        ("emzor", "paracetamol", 10, "125 mg/5 ml"),
        ("panado", "paracetamol", 14, "120 mg/5 ml"),
        ("doliprane", "paracetamol", 12, "120 mg/5 ml"),
        ("calpol", "paracetamol", 10, "120 mg/5 ml"),
        # y una de las de siempre, que son gotas y no jarabe: la diferencia más gorda de todas
        ("apiretal", "paracetamol", 12, "100 mg/ml"),
    ],
)
def test_el_bote_que_ha_dicho_va_el_primero(
    catalogo: DrugCatalog, escrito: str, molecula: str, kg: float, concentracion: str
) -> None:
    resuelto = catalogo.resolve(escrito)
    assert resuelto, f"el catálogo no reconoce «{escrito}»"
    _, marca = resuelto
    assert marca is not None

    texto = format_result(calculate(molecula, kg, 24), "en", brand=marca)
    filas = [line for line in texto.split("\n") if line.strip().startswith("–")]
    assert filas, texto
    assert marca.name in filas[0], f"la primera fila no es la suya:\n{texto}"
    assert concentracion.replace(" ", "") in filas[0].replace(" ", ""), filas[0]


def test_las_demas_siguen_estando(catalogo: DrugCatalog) -> None:
    """La misma marca vende más de un bote, y el padre puede tener otro. Esconderlas sería
    cambiar un riesgo por otro."""
    _, marca = catalogo.resolve("emzor")
    texto = format_result(calculate("paracetamol", 10, 24), "en", brand=marca)
    filas = [line for line in texto.split("\n") if line.strip().startswith("–")]
    assert len(filas) > 1, "se han escondido las demás presentaciones"
    sin_marca = format_result(calculate("paracetamol", 10, 24), "en")
    assert len(filas) == len([x for x in sin_marca.split("\n") if x.strip().startswith("–")])


def test_sin_marca_no_cambia_nada(catalogo: DrugCatalog) -> None:
    """Quien pregunta por «paracetamol» a secas recibe exactamente lo de siempre."""
    antes = format_result(calculate("paracetamol", 10, 24), "es")
    assert ", " not in antes.split("\n")[2].split(":")[0], antes.split("\n")[2]


def test_una_marca_de_otra_molecula_no_se_cuela(catalogo: DrugCatalog) -> None:
    """Dalsy es ibuprofeno. Si alguien pregunta por paracetamol nombrando Dalsy, la etiqueta no
    puede aparecer sobre una fila de paracetamol: sería decirle que su bote lleva otra cosa."""
    _, dalsy = catalogo.resolve("dalsy")
    texto = format_result(
        calculate("paracetamol", 10, 24), "en", brand=dalsy, brand_key="ibuprofen"
    )
    primera = next(line for line in texto.split("\n") if line.strip().startswith("–"))
    # Dalsy es 20 y 40 mg/ml; el paracetamol no tiene ninguna de esas, así que no debe marcarse
    assert "Dalsy" not in primera, texto


def test_el_motor_le_pasa_la_marca() -> None:
    """De nada sirve la mejora si la rama de la dosis no le da la marca al formateador."""
    from pedibot.bot.answer import brand_in_query

    catalogo = DrugCatalog(ROOT / "config" / "drugs.yaml")
    clave, marca = brand_in_query("how much emzor syrup for a 10 kg baby?", catalogo)
    assert clave == "paracetamol" and marca.name == "Emzor Paracetamol"
    assert brand_in_query("how much paracetamol for 10 kg?", catalogo) is None
