"""Una alternativa escrita en la escritura equivocada no casa nunca (18-sep-2026).

Escribiendo las reglas africanas se me coló esto dentro de la regla del sarampión:

    ...|boca|mouth|bouche|mund|рот|фم|फम|مुँह|मुँह|مुंह)

«فم» es «boca» en árabe. Ahí estaba escrito **dos veces mal**: «фم» con letras cirílicas y «फम»
con devanagari. Ninguna de las dos es una palabra de ninguna lengua, así que eran dos alternativas
muertas: no pueden casar jamás, y nadie se entera, porque una regla con una alternativa de menos
no falla — sólo deja de encontrar.

Es la misma familia que L164 («una expresión escrita para una escritura se rompe en silencio en
las otras») y se caza igual de mecánicamente: **una alternativa no puede mezclar dos alfabetos**.
Ni el árabe con el cirílico, ni el devanagari con el latino. Las únicas mezclas legítimas son las
que el propio regex mete —`\\w`, `[^.]`— y los números, que son de todos.
"""

from __future__ import annotations

import pathlib
import re

import pytest
import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
REGLAS = yaml.safe_load((RAIZ / "config" / "red_flags.yaml").read_text(encoding="utf-8"))["rules"]

#: Los bloques Unicode que el producto habla, y el nombre con el que se dicen en el informe.
BLOQUES = {
    "árabe": (0x0600, 0x06FF),
    "cirílico": (0x0400, 0x04FF),
    "devanagari": (0x0900, 0x097F),
}
#: Lo que hay que quitar antes de mirar: las clases del propio regex llevan letras latinas que no
#: son palabras («\w», «\d», «\s»), y los separadores parten las alternativas.
_ESCAPES = re.compile(r"\\[A-Za-z]")
_SEPARADORES = re.compile(r"[()|\[\]{}?*+.^$\\]")


def _escritura(c: str) -> str | None:
    for nombre, (lo, hi) in BLOQUES.items():
        if lo <= ord(c) <= hi:
            return nombre
    if c.isascii() and c.isalpha():
        return "latino"
    return None


def _alternativas(patron: str) -> list[str]:
    limpio = _ESCAPES.sub(" ", patron)
    return [a.strip() for a in _SEPARADORES.split(limpio) if len(a.strip()) >= 2]


IDS = [r["id"] for r in REGLAS]


def test_there_are_rules_to_look_at() -> None:
    assert len(IDS) > 50, "no se están leyendo las reglas"


@pytest.mark.parametrize("rid", IDS)
def test_no_alternative_mixes_two_scripts(rid: str) -> None:
    regla = next(r for r in REGLAS if r["id"] == rid)
    mezclas: list[str] = []
    for patron in regla.get("patterns") or []:
        for alt in _alternativas(str(patron)):
            escrituras = {e for e in (_escritura(c) for c in alt) if e}
            if len(escrituras) > 1:
                mezclas.append(f"«{alt}» mezcla {sorted(escrituras)}")
    assert not mezclas, (
        f"{rid}: alternativas que mezclan dos alfabetos y por tanto no casan con nada. "
        "Casi siempre es una palabra tecleada con el teclado equivocado: " + "; ".join(mezclas[:4])
    )
