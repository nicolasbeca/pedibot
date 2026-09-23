"""La octava tanda, 500 preguntas más (23-sep-2026).

Escritas contra las mismas costuras, y esta vez el bloque grande es el de preguntas sobre la
propia herramienta mezcladas con signos de alarma:

    «¿puedo mandarte una foto de labios azules?»          → EMERGENCIA
    «¿puedo mandarte una foto de manchas que no desaparecen al presionar?» → EMERGENCIA
    «¿cómo distingues "hace ruido" de "le cuesta respirar"?»               → EMERGENCIA
    «si digo "no respira bien" pero luego digo que corre, ¿cuál manda?»    → EMERGENCIA
    «q hago si se atraganta algún día? no está atragantado ahora»          → EMERGENCIA

Ninguna es un niño. Son preguntas sobre cómo funciona esto, con las palabras del peligro
dentro — que es exactamente lo que un evaluador escribe cuando prueba el producto.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT

TRIAJE = Triage(ROOT / "config" / "red_flags.yaml")

PREGUNTAN_POR_LA_HERRAMIENTA = [
    "¿puedo mandarte una foto de labios azules?",
    "¿puedo mandarte una foto de manchas que no desaparecen al presionar?",
    "¿puedo mandarte una foto de unos párpados hinchados?",
    "¿puedes saber si está deshidratado por una foto?",
    "¿cómo distingues «hace ruido» de «le cuesta respirar»?",
    "si digo «no respira bien» pero luego digo que corre, ¿cuál dato manda?",
    "si digo «se ahoga» pero en realidad solo tose, ¿qué haces?",
    "q hago si se atraganta algun dia? no esta atragantado ahora",
    "¿qué hago si un niño se pone azul? no está azul ahora",
]

DE_VERDAD = [
    "mi hijo tiene los labios azules ahora mismo",
    "tiene manchas que no desaparecen al presionar",
    "se está atragantando y no puede respirar",
    "se ha puesto azul",
]


@pytest.mark.parametrize("q", PREGUNTAN_POR_LA_HERRAMIENTA)
def test_asking_about_the_tool_is_not_an_emergency(q: str) -> None:
    r = TRIAJE.assess(q)
    assert r.level == "routine", f"{[x.id for x in r.matched]}: {q}"


@pytest.mark.parametrize("q", DE_VERDAD)
def test_the_real_thing_still_rings(q: str) -> None:
    assert TRIAJE.assess(q).level in ("urgent", "emergency"), q


def test_the_nose_is_a_cold() -> None:
    """«Se despertó llorando y parece que no puede respirar POR LA NARIZ» salía emergencia.
    La exclusión de la nariz existía desde el principio, pero no alcanzaba: el patrón que casaba
    era «no puede respirar» y la nariz quedaba fuera de su ventana."""
    assert (
        TRIAJE.assess(
            "mi hijo se despertó llorando y parece que no puede respirar por la nariz"
        ).level
        == "routine"
    )


def test_the_fever_threshold_is_the_one_the_source_gives() -> None:
    """40,1 daba «fiebre muy alta» y la regla dice 40,5 — su propio motivo lo escribe."""
    assert TRIAJE.assess("40.1 sin mas datos, ¿me puedes decir que hago?").level == "routine"
    assert TRIAJE.assess("tiene 40,6 de fiebre").level in ("urgent", "emergency")
    assert TRIAJE.assess("tiene 41,2 de fiebre").level in ("urgent", "emergency")
