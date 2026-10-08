"""Las páginas de un país se indexan en las lenguas que se hablan allí (8-oct-2026).

Lo mismo que las marcas (test_brand_pages_index_where_sold.py), a mayor escala. De las 2.965
URLs del sitemap, 2.216 eran tablas país × lengua: 107 números de urgencia, 92 calendarios y 78
curvas de crecimiento, cada uno en ocho lenguas. Inspeccionadas en Search Console: fuera
/es/vaccines/es (el calendario español en castellano), /pt/vaccines/br y /vaccines/us; dentro
/es/vaccines/gb y /pt/vaccines/fr. Google elegía al azar entre páginas casi iguales.

La regla: un país se indexa en inglés (la edición por defecto) y en las lenguas del sitio que se
hablan allí (`src/countrylangs.mjs`). Las demás ediciones siguen abiertas para quien llegue por el
selector de idioma, con `noindex`, fuera del sitemap y del hreflang.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"
NOINDEX = re.compile(r'<meta name="robots" content="noindex', re.I)


def _html(path: str) -> str:
    if not DIST.exists():
        pytest.skip("el sitio no está construido en esta copia")
    p = DIST / path.strip("/") / "index.html"
    assert p.exists(), path
    return p.read_text(encoding="utf-8")


def _sitemap() -> set[str]:
    f = DIST / "sitemap-0.xml"
    if not f.exists():
        pytest.skip("el sitio no está construido en esta copia")
    return {u.replace("https://pedibot.xyz", "") for u in re.findall(r"<loc>([^<]+)", f.read_text("utf-8"))}


INDEXADAS = [
    "/vaccines/us", "/vaccines/br", "/growth/af",  # inglés: siempre
    "/es/vaccines/es", "/es/vaccines/us", "/es/vaccines/mx",
    "/pt/vaccines/br", "/pt/emergency/mz", "/fr/vaccines/sn", "/fr/growth/ca",
    "/de/emergency/ch", "/ru/emergency/kz", "/ar/vaccines/ma", "/fr/vaccines/ma", "/hi/vaccines/in",
]
FUERA = [
    "/de/vaccines/br", "/es/vaccines/fr", "/ru/vaccines/us", "/hi/emergency/us",
    "/pt/growth/de", "/ar/vaccines/br", "/ru/emergency/sn",
]


@pytest.mark.parametrize("path", INDEXADAS)
def test_a_country_in_a_language_spoken_there_is_indexed(path):
    assert not NOINDEX.search(_html(path)), f"{path} no debería llevar noindex"
    assert path in _sitemap(), f"{path} debería estar en el sitemap"


@pytest.mark.parametrize("path", FUERA)
def test_a_country_in_a_language_not_spoken_there_is_not(path):
    assert NOINDEX.search(_html(path)), f"{path} debería llevar noindex"
    assert path not in _sitemap(), f"{path} no debería estar en el sitemap"


def test_hreflang_of_a_country_names_only_its_indexed_editions():
    h = _html("/vaccines/br")
    langs = set(re.findall(r'<link rel="alternate" hreflang="([a-z-]+)"', h))
    assert {"en", "pt", "x-default"} <= langs
    assert not langs & {"es", "de", "ru", "hi", "ar", "fr"}, langs


def test_every_country_page_knows_its_languages():
    """Un país que se añada a los datos sin entrar en el mapa sólo tendría el inglés: que se note."""
    import json

    mapa = (ROOT / "web" / "site" / "src" / "countrylangs.mjs").read_text("utf-8")
    conocidos = set(re.findall(r"\b([A-Z]{2}):\s*\[", mapa))
    datos = ROOT / "web" / "site" / "src" / "data"
    paises = set(json.loads((datos / "vaccines.json").read_text("utf-8")))
    paises |= set(json.loads((datos / "growth_charts.json").read_text("utf-8")))
    paises |= set(json.loads((datos / "emergency.json").read_text("utf-8")))
    faltan = sorted(p for p in paises if p.upper() not in conocidos)
    assert not faltan, f"países sin lenguas en src/countrylangs.mjs: {faltan}"
