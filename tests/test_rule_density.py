"""Cada regla tiene que tener la misma red en las cuatro escrituras (8-sep-2026).

El candado que ya existía (`test_every_rule_can_fire_in_every_script`) pregunta «¿hay al menos
un patrón en devanagari?». Con eso, `eating_disorder_signs` pasaba teniendo **un** patrón en
ruso frente a veintiséis latinos, y `neuro_deficit` —que es EMERGENCIA— pasaba con treinta
latinos y dos en cirílico y dos en árabe: catorce signos distintos en las lenguas latinas y dos
en ruso.

Presencia no es cobertura. Esto mide la proporción.

El alfabeto latino lo comparten SEIS de las nueve lenguas (inglés, castellano, francés, alemán,
portugués y, desde el 18-sep-2026, el suajili), así que la comparación justa es su cuenta
**dividida entre seis** frente a lo que tiene cada una de las otras tres. Al entrar el suajili
esta cuenta se quedó vieja y el candado señaló siete reglas que no habían empeorado: lo que había
subido era el numerador. El umbral es holgado a propósito —la mitad— porque una lengua
puede necesitar menos patrones que otra para decir lo mismo, y un candado que salta por gusto se
acaba silenciando. Lo que busca es el desierto, no el desnivel.

Al escribirlo señaló cuatro reglas y las cuatro tenían agujeros reales: de 96 combinaciones
probadas a mano sobre ellas, fallaron 39.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]

BLOQUES = {
    "cirílico": ("Ѐ", "ӿ"),
    "árabe": ("؀", "ۿ"),
    "devanagari": ("ऀ", "ॿ"),
}

#: Cuántas lenguas del producto escriben en alfabeto latino: en, es, fr, de, pt.
LENGUAS_LATINAS = 6

#: Por debajo de esta fracción de la media latina, esa escritura está desatendida.
SUELO = 0.5


def _reglas() -> list[dict]:
    crudo = yaml.safe_load((RAIZ / "config" / "red_flags.yaml").read_text(encoding="utf-8"))
    return list(crudo["rules"])


def _escritura(patron: str) -> str:
    for nombre, (lo, hi) in BLOQUES.items():
        if any(lo <= c <= hi for c in patron):
            return nombre
    return "latino"


def _cuenta(regla: dict) -> dict[str, int]:
    out = {"latino": 0, **{k: 0 for k in BLOQUES}}
    for p in regla.get("patterns", []):
        out[_escritura(str(p))] += 1
    return out


@pytest.mark.parametrize("regla", _reglas(), ids=lambda r: str(r["id"]))
def test_no_script_is_left_with_a_fraction_of_the_net(regla: dict) -> None:
    c = _cuenta(regla)
    por_lengua = c["latino"] / LENGUAS_LATINAS
    if por_lengua < 1:  # una regla pequeña no tiene margen que repartir
        return
    pobres = {k: c[k] for k in BLOQUES if c[k] < por_lengua * SUELO}
    assert not pobres, (
        f"{regla['id']} ({regla['level']}): {c['latino']} patrones latinos "
        f"(≈{por_lengua:.1f} por lengua) y "
        + ", ".join(f"{k}={v}" for k, v in pobres.items())
        + ". Presencia no es cobertura: escribe en esas escrituras los signos que sí están"
        " escritos en las latinas."
    )


def test_the_check_can_still_see_a_desert() -> None:
    """El candado del candado: si la medida deja de distinguir, deja de comprobar nada."""
    inventada = {
        "id": "prueba",
        "level": "urgent",
        "patterns": ["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
                     "не дышит", "لا يتنفس"],
    }
    c = _cuenta(inventada)
    assert c["latino"] == 8 and c["cirílico"] == 1 and c["árabe"] == 1
    assert c["devanagari"] == 0
    por_lengua = c["latino"] / LENGUAS_LATINAS
    assert c["devanagari"] < por_lengua * SUELO, "la medida ya no ve una escritura vacía"
