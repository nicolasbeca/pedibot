"""Los títulos que Google corta se llevan por delante la parte que convence (11-sep-2026).

Un resultado de búsqueda muestra unos **60 caracteres** de título. Medido sobre el sitio
construido: **166 de 800 páginas** pasaban de ahí, y la mayoría por dos motivos evitables.

Uno: el sufijo de marca. Casi todas las páginas terminaban en «— PediBot», diez caracteres que
no dicen nada que el lector no vea ya en el dominio, y que empujaban fuera del corte la parte
útil. Dos: las páginas de calendario vacunal — «Portugal — Programa Nacional de Vacinação
(PNV 2025): quais vacinas e quando — PediBot», **86 caracteres**.

La regla que se fija aquí es de fondo y no un número: **si el título no cabe, lo primero que se
cae es la marca, y el corte se hace por una pausa del propio título** —dos puntos, raya,
interrogación— y no a mitad de palabra. El `<h1>` y la tarjeta social siguen llevando el título
entero: lo que se acorta es sólo lo que el buscador enseña.
"""

from __future__ import annotations

import html
import pathlib
import re

import pytest

DIST = pathlib.Path(__file__).resolve().parents[1] / "web" / "site" / "dist"
MARCA = " — PediBot"
CORTE = 60


def _titulos() -> list[tuple[str, str]]:
    fuera = []
    for p in sorted(DIST.rglob("index.html")):
        m = re.search(r"<title>(.*?)</title>", p.read_text(encoding="utf-8"), re.S)
        if m:
            ruta = str(p.parent.relative_to(DIST)).replace("\\", "/")
            fuera.append((ruta, html.unescape(m.group(1)).strip()))
    return fuera


def test_la_marca_nunca_es_lo_que_deja_el_titulo_fuera_del_corte():
    titulos = _titulos()
    if not titulos:
        pytest.skip("el sitio no está construido en esta copia")
    malos = [(r, len(t), t) for r, t in titulos if len(t) > CORTE and t.endswith(MARCA)]
    assert not malos, (
        "estos títulos se cortan en el resultado y lo último que llevan es la marca, que es "
        f"justo lo prescindible: {malos[:5]}"
    )


def _og(p: pathlib.Path) -> str:
    m = re.search(r'<meta property="og:title" content="(.*?)"', p.read_text(encoding="utf-8"), re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def test_ningun_titulo_se_corta_a_mitad_de_palabra():
    """Comparado con el título entero, que la tarjeta social sigue llevando: donde se corta
    tiene que haber un espacio, no media palabra."""
    if not DIST.exists():
        pytest.skip("el sitio no está construido en esta copia")
    partidos = []
    for p in sorted(DIST.rglob("index.html")):
        m = re.search(r"<title>(.*?)</title>", p.read_text(encoding="utf-8"), re.S)
        if not m:
            continue
        corto = html.unescape(m.group(1)).strip()
        if not corto.endswith("…"):
            continue
        entero, raiz = _og(p), corto[:-1]
        if not entero.startswith(raiz) or entero[len(raiz) : len(raiz) + 1] not in (" ", ""):
            partidos.append((str(p.parent.relative_to(DIST)).replace("\\", "/"), corto))
    assert not partidos, f"títulos cortados dentro de una palabra: {partidos[:5]}"


def test_las_paginas_del_propio_sitio_caben():
    """Las guías las titula un modelo; estas otras las titulamos nosotros y no hay excusa."""
    titulos = _titulos()
    if not titulos:
        pytest.skip("el sitio no está construido en esta copia")
    nuestras = [
        (r, len(t), t)
        for r, t in titulos
        if "/guides/" not in f"/{r}/" and not r.endswith("guides") and len(t) > CORTE
    ]
    assert not nuestras, f"páginas nuestras con el título fuera del corte: {nuestras[:6]}"


def test_y_siguen_diciendo_algo():
    """Un título recortado a cuatro palabras no sirve de nada: el corte tiene un suelo."""
    titulos = _titulos()
    if not titulos:
        pytest.skip("el sitio no está construido en esta copia")
    cortos = [(r, t) for r, t in titulos if len(t) < 18]
    assert not cortos, f"títulos que se han quedado en nada: {cortos[:5]}"
