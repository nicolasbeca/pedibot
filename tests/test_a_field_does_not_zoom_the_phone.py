"""Un campo de menos de 16 px amplía la página en un iPhone (19-sep-2026).

Safari en iOS hace zoom sobre toda la página cuando enfocas un `input`, `select` o `textarea`
cuyo texto mide menos de 16 px. No es un capricho: es su manera de decir «esto no se lee». El
efecto para quien escribe es que la página se agranda sola, se descoloca y al salir del campo se
queda así.

Medido sobre los componentes del sitio antes de arreglarlo, había **once** por debajo:

    13,4 px  el selector de país de la portada
    14,4 px  la herramienta de vacunas
    13,8 px  el buscador de guías, en las ocho lenguas
    13,6 px  la ficha de los hijos (recién escrita ese mismo día)

Todos son campos que se tocan con el dedo, que es justo donde duele. Se arregló en `global.css`
en una regla y sólo bajo `pointer: coarse`, para no tocar el diseño con ratón.

Esta prueba mira la regla y además vuelve a medir: un componente nuevo puede fijarle a su campo
un tamaño propio por debajo de 16 y saltarse la regla general sin que nadie lo note.
"""

from __future__ import annotations

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[1]
SRC = RAIZ / "web" / "site" / "src"
GLOBAL = (SRC / "styles" / "global.css").read_text(encoding="utf-8")

#: 1rem en este sitio son 16 px: no se toca el tamaño de raíz en ninguna parte.
BASE_PX = 16
REGLA = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
TAMANO = re.compile(r"font-size:\s*([\d.]+)(rem|px|em)")
CAMPO = re.compile(r"\b(input|select|textarea)\b")


def test_the_global_rule_is_there() -> None:
    assert "pointer: coarse" in GLOBAL, "sin esto, cada campo del sitio amplía la página en iOS"
    m = re.search(r"@media \(pointer: coarse\)\s*\{([^}]*\{[^}]*\})", GLOBAL, re.S)
    assert m, "la regla existe pero no cubre ningún selector"
    assert CAMPO.search(m.group(1)), "la regla no alcanza a los campos"
    assert "16px" in m.group(1), "el umbral de iOS son 16 px exactos"


def test_the_root_font_size_is_still_sixteen() -> None:
    """Toda la cuenta de arriba supone que 1rem son 16 px. Si alguien toca el tamaño de raíz,
    esta prueba tiene que enterarse antes que un iPhone."""
    raiz = re.search(r"(?:^|\n)(?:html|:root)\s*\{([^}]*)\}", GLOBAL, re.S)
    if raiz and (t := TAMANO.search(raiz.group(1))):
        px = float(t.group(1)) * (BASE_PX if t.group(2) in ("rem", "em") else 1)
        assert px >= BASE_PX, f"la raíz mide {px}px y toda la regla de los 16 se va al suelo"


def test_no_component_sets_its_own_field_smaller() -> None:
    """La regla general la puede pisar un componente que le fije el tamaño a su propio campo.
    Eso es legítimo para subir y nunca para bajar de 16."""
    culpables: list[str] = []
    # sólo dentro de <style>: fuera hay marcado, y `</select></label>` seguido de una llave de
    # JavaScript pasaba por un selector de CSS de lo más convincente
    bloque_estilo = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
    for fichero in sorted(SRC.rglob("*.astro")):
        texto = "\n".join(bloque_estilo.findall(fichero.read_text(encoding="utf-8")))
        for m in REGLA.finditer(texto):
            selector = " ".join(m.group(1).split())
            if not CAMPO.search(selector) or selector.startswith("@"):
                continue
            t = TAMANO.search(m.group(2))
            if not t:
                continue  # hereda: de eso se encarga la regla global
            px = float(t.group(1)) * (BASE_PX if t.group(2) in ("rem", "em") else 1)
            if px < BASE_PX:
                culpables.append(f"{fichero.relative_to(SRC)}: «{selector[:50]}» a {px:g}px")
    assert not culpables, (
        "campos por debajo de 16 px con tamaño propio, que se saltan la regla global: "
        + "; ".join(culpables[:5])
    )
