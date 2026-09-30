"""Cada página enseña su tarjeta al compartirse, y la tarjeta existe (30-sep-2026).

Hasta hoy las 2.900 páginas compartían una sola imagen. Ahora hay una por tipo de página y
lengua (scripts/make-og-cards.mjs, ops/TARJETAS.md). Lo que no puede pasar es que una página
anuncie una tarjeta que no se ha generado: WhatsApp y X enseñarían el enlace sin imagen.
"""

from __future__ import annotations

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DIST = RAIZ / "web" / "site" / "dist"
PUBLIC = RAIZ / "web" / "site" / "public"
LANGS = ["en", "es", "fr", "de", "ru", "ar", "pt", "hi"]
TIPOS = ["home", "tools", "emergency", "warning-signs", "numbers", "dose", "growth", "vaccines",
         "muac", "diary", "family", "kit", "guides", "sources", "about"]


@pytest.mark.parametrize("lang", LANGS)
def test_estan_todas_las_tarjetas(lang: str) -> None:
    faltan = [t for t in TIPOS if not (PUBLIC / "og" / lang / f"{t}.jpg").exists()]
    assert not faltan, f"{lang}: faltan tarjetas {faltan}; corre node scripts/make-og-cards.mjs"


def test_ninguna_pagina_anuncia_una_tarjeta_que_no_existe() -> None:
    if not DIST.exists():
        pytest.skip("el sitio no está construido en esta copia")
    rotas = []
    for p in DIST.rglob("index.html"):
        m = re.search(r'property="og:image" content="https://pedibot\.xyz/([^"]+)"', p.read_text(encoding="utf-8"))
        if m and not (PUBLIC / m.group(1)).exists():
            rotas.append((str(p.parent.relative_to(DIST)), m.group(1)))
    assert not rotas, rotas[:5]


@pytest.mark.parametrize(
    "ruta,tarjeta",
    [("es/tools", "og/es/tools.jpg"), ("tools", "og/en/tools.jpg"), ("es/emergency/ke", "og/es/numbers.jpg"),
     ("ar/dose", "og/ar/dose.jpg"), ("es", "og/es/home.jpg")],
)
def test_cada_tipo_lleva_la_suya(ruta: str, tarjeta: str) -> None:
    f = DIST / ruta / "index.html"
    if not f.exists():
        pytest.skip("el sitio no está construido en esta copia")
    assert f'content="https://pedibot.xyz/{tarjeta}"' in f.read_text(encoding="utf-8")
