"""Una llave abierta en el CSS no se ve: se ve el estilo que falta (19-sep-2026).

Repasando la web el día de MetaDAO encontré esto en la portada de números de emergencia, y
llevaba ahí desde que se escribió el generador:

    .ncard b {
    .ncard b.sin { color: var(--ink-3); font-weight: 600; }
      font-family: 'JetBrains Mono', ui-monospace, monospace; color: var(--coral);
    }

La regla de `.sin` se había colado DENTRO de la de `.ncard b`, antes de las declaraciones. Nadie
lo vio porque el sitio sigue construyendo sin una queja: el minificador lo interpreta como CSS
anidado y lo escribe como `& .ncard b.sin`, un selector que no casa con nada nunca.

Lo que se perdía: los ocho países cuya fuente dice que NO hay número nacional enseñaban su raya
en el mismo coral y la misma tipografía que un teléfono de verdad. Justo lo contrario de lo que
esa clase existía para decir.

**En este proyecto no se anida CSS.** Así que cualquier regla dentro de otra regla es este fallo
otra vez. Las arrobas sí abren un bloque con reglas dentro —`@media`, `@supports`,
`@keyframes`— y esas son las únicas que pueden.
"""

from __future__ import annotations

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
SRC = RAIZ / "web" / "site" / "src"

ASTRO = sorted(SRC.rglob("*.astro"))
#: `<style>` con lo que lleva dentro; `is:inline` o no, da igual.
BLOQUE = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
#: una línea que abre un bloque: lo que haya y una llave al final.
ABRE = re.compile(r"^\s*([^{}]+?)\s*\{\s*$")
#: una regla entera en una sola línea, que es como estaba escrita la que se coló.
ENTERA = re.compile(r"^\s*([^{}]+?)\s*\{[^{}]*\}\s*$")


def _reglas_anidadas(css: str) -> list[str]:
    """Los selectores que abren un bloque teniendo otro bloque abierto que no es una arroba."""
    pila: list[str] = []
    malas: list[str] = []
    for linea in css.splitlines():
        # los comentarios de una línea no cuentan, y las llaves de una línea cerrada tampoco
        limpia = re.sub(r"/\*.*?\*/", "", linea)
        entera = ENTERA.match(limpia)
        if entera:
            # la que se coló estaba escrita así, entera en su línea, y por eso pasó
            # desapercibida: no descuadra ninguna llave, sólo se mete donde no debe
            if pila and not pila[-1].startswith("@"):
                malas.append(f"«{entera.group(1)}» dentro de «{pila[-1]}»")
            continue
        if "}" in limpia and "{" in limpia:
            continue  # otra cosa en una línea, con llaves por los dos lados
        abre = ABRE.match(limpia)
        if abre:
            selector = abre.group(1)
            if pila and not pila[-1].startswith("@"):
                malas.append(f"«{selector}» dentro de «{pila[-1]}»")
            pila.append(selector)
        elif limpia.strip().startswith("}") and pila:
            pila.pop()
    return malas


@pytest.mark.parametrize("ruta", ASTRO, ids=lambda p: str(p.relative_to(SRC)))
def test_no_rule_hides_inside_another_rule(ruta: pathlib.Path) -> None:
    for css in BLOQUE.findall(ruta.read_text(encoding="utf-8")):
        malas = _reglas_anidadas(css)
        assert not malas, (
            f"{ruta.relative_to(SRC)}: regla dentro de regla, que aquí siempre ha sido una "
            f"llave que se quedó abierta: {malas}"
        )


def test_every_style_block_closes_what_it_opens() -> None:
    """Y la comprobación tonta, que es la que habría pillado el mismo fallo escrito de otra
    manera: las llaves que se abren y las que se cierran, contadas."""
    descuadres = []
    for ruta in ASTRO:
        for css in BLOQUE.findall(ruta.read_text(encoding="utf-8")):
            sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
            if sin_comentarios.count("{") != sin_comentarios.count("}"):
                descuadres.append(str(ruta.relative_to(SRC)))
    assert not descuadres, f"bloques <style> descuadrados: {descuadres}"
