"""La calculadora en todo su rango, por invariantes (9-sep-2026).

Los tests que había comprueban casos concretos y que las dos calculadoras —la de Python y la del
TypeScript de la web— dicen lo mismo. Ninguno preguntaba si ALGUNA combinación de peso y edad
rompe una de las reglas que impone la guía.

Aquí un número es una instrucción: cuántos mililitros se le echan a un niño en una jeringa.

Medido sobre 30.966 combinaciones (1,0–120,0 kg en pasos de 100 g × trece edades × dos
fármacos): cero. Este fichero usa una rejilla más gruesa para no alargar la suite, y las mismas
seis reglas.
"""

from __future__ import annotations

import pytest

from pedibot.bot.dose import DRUGS, DoseError, calculate

FARMACOS = ("paracetamol", "ibuprofeno")
PESOS = [round(1.0 + 0.5 * i, 1) for i in range(239)]  # 1,0 – 120,0 kg
#: Las edades que importan son las de los bordes: 3 meses es el corte del ibuprofeno y del
#: «menor de 3 meses», así que se prueban los dos lados y el punto exacto.
EDADES = (None, 0, 1, 2, 2.9, 3, 3.1, 6, 12, 24, 60, 120, 216)


@pytest.mark.parametrize("clave", FARMACOS)
def test_no_dose_exceeds_what_the_guide_allows(clave: str) -> None:
    d = DRUGS[clave]
    for kg in PESOS:
        for edad in EDADES:
            r = calculate(clave, kg, edad)
            assert r.mg <= d.max_single_dose_mg + 1e-9, f"{kg} kg / {edad} m: {r.mg} mg"
            if r.mg < d.max_single_dose_mg - 1e-9:  # salvo cuando manda el tope duro
                assert r.mg <= d.mg_per_kg_max * kg + 1e-9, (
                    f"{kg} kg / {edad} m: {r.mg} mg > {d.mg_per_kg_max}·{kg}"
                )
            assert r.mg_min - 1e-9 <= r.mg <= r.mg_max + 1e-9, (
                f"{kg} kg / {edad} m: {r.mg} fuera de [{r.mg_min}, {r.mg_max}]"
            )


@pytest.mark.parametrize("clave", FARMACOS)
def test_the_day_never_adds_up_to_more_than_the_daily_maximum(clave: str) -> None:
    d = DRUGS[clave]
    for kg in PESOS:
        for edad in EDADES:
            r = calculate(clave, kg, edad)
            tope = min(d.max_mg_per_kg_day * kg, d.max_daily_mg)
            assert r.mg * r.max_doses_per_day <= tope + 1e-6, (
                f"{kg} kg / {edad} m: {r.mg}·{r.max_doses_per_day} > {tope}"
            )


@pytest.mark.parametrize("clave", FARMACOS)
def test_no_millilitre_is_worth_more_than_the_milligrams_behind_it(clave: str) -> None:
    """El redondeo de los mililitros va SIEMPRE hacia abajo: quedarse corto con un antitérmico no
    hace daño y pasarse sí. Esto lo comprueba bote a bote en todo el rango."""
    d = DRUGS[clave]
    for kg in PESOS:
        for edad in EDADES:
            r = calculate(clave, kg, edad)
            for p in d.presentations:
                ml = r.ml[p.name]
                assert ml * p.mg_per_ml <= r.mg + 1e-9, (
                    f"{kg} kg / {edad} m / {p.name}: {ml} ml son {ml * p.mg_per_ml} mg > {r.mg}"
                )


@pytest.mark.parametrize("clave", FARMACOS)
def test_refer_is_set_exactly_when_it_should_be(clave: str) -> None:
    """Ni de más ni de menos: `refer` es lo que decide si se enseña una cifra o no."""
    d = DRUGS[clave]
    for kg in PESOS:
        for edad in EDADES:
            r = calculate(clave, kg, edad)
            debe = bool(
                (edad is not None and edad < 3)
                or (edad is not None and edad < d.min_age_months)
                or kg < d.min_weight_kg
            )
            assert bool(r.refer) is debe, f"{kg} kg / {edad} m: refer={r.refer}, esperado {debe}"


@pytest.mark.parametrize("kg", (0.5, 0.99, 120.1, 200.0))
def test_a_weight_outside_the_range_is_refused_and_not_guessed(kg: float) -> None:
    """Fuera de rango la respuesta correcta es negarse. Un número inventado para un peso que la
    guía no cubre se lee igual que uno bueno."""
    with pytest.raises(DoseError):
        calculate("paracetamol", kg, 24)
