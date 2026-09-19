"""Las bandas de percentiles, para poder dibujarlas (19-sep-2026).

El operador mandó dos capturas de otra aplicación: el nombre del hijo arriba con su edad, y
debajo **sus puntos sobre las bandas de la OMS**, esas cinco líneas de colores. Eso es lo que
falta para dibujar la curva de cada niño, porque hasta hoy el sitio sabía decir «percentil 63» y
no sabía dibujar por dónde pasa el 63.

No es un cálculo nuevo: son las mismas tablas LMS que ya usa `/api/growth`, invertidas. La
fórmula es la de siempre, al revés: x = M·(1 + L·S·z)^(1/L), con z fijo en los cinco percentiles
que dibuja la OMS en sus propias láminas (P3, P15, P50, P85, P97).

Lo que se comprueba aquí es lo que haría falsa la curva: que las bandas suban, que estén
ordenadas de abajo arriba y que el P50 sea de verdad la mediana de la tabla, la M.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def cliente(app_con_familia):  # noqa: ANN001, ANN201
    return app_con_familia


def test_the_bands_come_back_for_a_baby(cliente) -> None:  # noqa: ANN001
    r = cliente.get("/api/growth/bands", params={"sex": "f", "indicator": "wfa", "to_months": 24})
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["indicator"] == "wfa"
    assert datos["unit"] == "kg"
    assert len(datos["ages"]) > 20, "una banda de dos años con menos de veinte puntos es un palo"
    assert set(datos["bands"]) == {"p3", "p15", "p50", "p85", "p97"}


def test_the_bands_are_in_order_at_every_age(cliente) -> None:  # noqa: ANN001
    """Si el P15 cruza al P50, el dibujo miente y nadie lo va a comprobar a ojo."""
    datos = cliente.get(
        "/api/growth/bands", params={"sex": "m", "indicator": "wfa", "to_months": 60}
    ).json()
    b = datos["bands"]
    for i in range(len(datos["ages"])):
        valores = [b["p3"][i], b["p15"][i], b["p50"][i], b["p85"][i], b["p97"][i]]
        assert valores == sorted(valores), f"las bandas se cruzan a los {datos['ages'][i]} meses"


#: Lo que la OMS publica en sus propias láminas, leído de ahí y no de nuestro código:
#: (sexo, indicador, meses, mediana, tolerancia). Son los valores con los que cualquiera puede
#: comprobar esto sin abrir el repositorio.
MEDIANAS_OMS = [
    ("f", "wfa", 0, 3.2, 0.15),
    ("f", "wfa", 12, 8.9, 0.2),
    ("f", "wfa", 24, 11.5, 0.3),
    ("m", "wfa", 0, 3.3, 0.15),
    ("m", "wfa", 12, 9.6, 0.2),
    ("m", "wfa", 60, 18.3, 0.5),
    ("f", "lhfa", 12, 74.0, 0.6),
    ("m", "lhfa", 24, 87.1, 0.8),
]


@pytest.mark.parametrize(("sexo", "indicador", "meses", "mediana", "tol"), MEDIANAS_OMS)
def test_the_middle_band_is_what_the_who_publishes(
    cliente, sexo, indicador, meses, mediana, tol
) -> None:  # noqa: ANN001
    """El P50 tiene que coincidir con la mediana que publica la OMS. Contra SUS cifras, no
    contra las nuestras.

    La primera versión de esta prueba comparaba el P50 con la M de nuestra propia tabla, pasada
    con la misma unidad que usaba el código. Y el código estaba mal —las tablas de 0 a 5 años
    van en DÍAS y se les pasaban meses—, así que la prueba confirmaba el error: el P50 a los 18
    meses salía 3,72 kg, el peso de un bebé de dieciocho días, y la prueba pasaba. Una prueba
    que comparte la suposición del código no comprueba nada.
    """
    datos = cliente.get(
        "/api/growth/bands",
        params={"sex": sexo, "indicator": indicador, "to_months": max(meses, 24)},
    ).json()
    i = datos["ages"].index(float(meses))
    assert datos["bands"]["p50"][i] == pytest.approx(mediana, abs=tol)


def test_the_bands_are_not_all_the_same_number(cliente) -> None:  # noqa: ANN001
    """El otro lado del mismo fallo: con la unidad equivocada la curva era casi plana —de 3,23
    a 3,95 kg en cinco años— y a ojo, en un gráfico reescalado, no se notaba."""
    datos = cliente.get(
        "/api/growth/bands", params={"sex": "f", "indicator": "wfa", "to_months": 60}
    ).json()
    p50 = datos["bands"]["p50"]
    assert p50[-1] > p50[0] * 4, (
        f"de {p50[0]} a {p50[-1]} kg en cinco años: eso no es una curva de crecimiento"
    )


def test_a_growing_child_grows(cliente) -> None:  # noqa: ANN001
    datos = cliente.get(
        "/api/growth/bands", params={"sex": "f", "indicator": "lhfa", "to_months": 36}
    ).json()
    assert datos["unit"] == "cm"
    p50 = datos["bands"]["p50"]
    assert p50 == sorted(p50), "la talla mediana no puede bajar con la edad"


def test_an_indicator_that_does_not_exist_is_refused(cliente) -> None:  # noqa: ANN001
    assert (
        cliente.get("/api/growth/bands", params={"sex": "f", "indicator": "peso"}).status_code
        == 422
    )


def test_the_first_two_years_are_drawn_finely(cliente) -> None:  # noqa: ANN001
    """El paso tiene que cambiar DENTRO de la curva, no según dónde acabe.

    La primera versión elegía un paso para toda la curva: si el niño tenía tres años, dibujaba
    también su primer año a saltos de tres meses, que es justo el tramo donde la línea se dobla.
    Una curva de peso del primer año con cuatro puntos es un palo.
    """
    datos = cliente.get(
        "/api/growth/bands", params={"sex": "f", "indicator": "wfa", "to_months": 60}
    ).json()
    primeros = [e for e in datos["ages"] if e < 24]
    assert len(primeros) >= 24, f"sólo {len(primeros)} puntos en los dos primeros años"
    saltos = {round(b - a, 2) for a, b in zip(primeros, primeros[1:], strict=False)}
    assert saltos == {1.0}, f"el primer tramo no va de mes en mes: {saltos}"
