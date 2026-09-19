"""Ningún desplegable de idioma puede abrirse vacío (11-sep-2026).

Tres guías del sitio existen **sólo en inglés y a propósito**: `asthma_en`, `ibuprofen_en` y
`paracetamol_en` llevan el sufijo `_en` justamente porque en las demás lenguas producirían un
duplicado de una guía que ya existe, y `pending_topics` las excluye de esos idiomas.

Lo que estaba mal no era eso, era lo que veía el lector: en esas tres páginas el selector se
abría **para ofrecerse a sí mismo**. Pulsabas «EN ▾» y dentro sólo estaba «English». Un menú que
se abre vacío es peor que no tener menú — promete algo y no lo cumple, en un sitio cuyo argumento
central es que habla ocho idiomas.

Ahora, cuando no hay hermanas, sale la etiqueta del idioma y ya está: sin flecha y sin abrir.
"""

from __future__ import annotations

import pathlib
import re

import pytest

DIST = pathlib.Path(__file__).resolve().parents[1] / "web" / "site" / "dist"


def _paginas() -> list[pathlib.Path]:
    return sorted(DIST.rglob("index.html"))


def test_ningun_desplegable_se_abre_sin_ofrecer_nada():
    paginas = _paginas()
    if not paginas:
        pytest.skip("el sitio no está construido en esta copia")
    vacios = []
    for p in paginas:
        m = re.search(
            r'<details class="langsel"[^>]*>(.*?)</details>', p.read_text(encoding="utf-8"), re.S
        )
        if m and not re.search(r"<a[^>]*hreflang=", m.group(1)):
            vacios.append(str(p.parent.relative_to(DIST)).replace("\\", "/"))
    assert not vacios, (
        "estas páginas abren el selector de idioma y dentro no hay ningún otro idioma; "
        f"debe salir la etiqueta, no el menú: {vacios}"
    )


def test_la_pagina_sin_hermanas_sigue_diciendo_en_que_idioma_esta():
    """Quitar el menú no puede llevarse por delante el dato: el lector tiene que saber dónde está."""
    paginas = _paginas()
    if not paginas:
        pytest.skip("el sitio no está construido en esta copia")
    sin_nada = []
    for p in paginas:
        h = p.read_text(encoding="utf-8")
        if "<header" not in h:  # páginas sin cabecera: nada que comprobar
            continue
        # el atributo real es `class="pill langsel-solo"`: se busca la clase, no la cadena entera
        if "langsel-solo" not in h and '<details class="langsel"' not in h:
            sin_nada.append(str(p.parent.relative_to(DIST)).replace("\\", "/"))
    assert not sin_nada, f"páginas que no dicen en qué idioma están: {sin_nada}"
