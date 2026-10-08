"""Una marca se indexa en las lenguas de los países donde se vende (8-oct-2026).

Inspeccionadas con la API de Search Console 297 URLs: de las páginas de dosis, 34 «rastreadas
pero no indexadas» y 40 indexadas, y el reparto era al revés de lo que sirve. Fuera: /dose/tylenol,
/dose/calpol, /dose/nurofen, /es/dose/ibuprofeno. Dentro: /de/dose/apirofeno (una marca que sólo
se vende en España, en alemán), /fr/dose/tachipirina. 32 marcas por ocho lenguas son 256 páginas
que se parecen entre un 60 y un 90 % (medido), y Google se queda con las que le tocan.

Lo que se fija aquí: la edición de una marca en una lengua que no se habla en ninguno de sus
países sigue abierta para quien llegue, pero lleva `noindex`, no va al sitemap y ningún hreflang
la anuncia. El inglés es la edición por defecto del sitio y se indexa siempre; los genéricos,
en todas las lenguas.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"
NOINDEX = re.compile(r'<meta name="robots" content="noindex', re.I)


def _html(path: str) -> str:
    p = DIST / path.strip("/") / "index.html"
    if not DIST.exists():
        pytest.skip("el sitio no está construido en esta copia")
    assert p.exists(), path
    return p.read_text(encoding="utf-8")


def _sitemap() -> set[str]:
    f = DIST / "sitemap-0.xml"
    if not f.exists():
        pytest.skip("el sitio no está construido en esta copia")
    return {u.replace("https://pedibot.xyz", "") for u in re.findall(r"<loc>([^<]+)", f.read_text("utf-8"))}


@pytest.mark.parametrize(
    "path",
    ["/ru/dose/tylenol", "/de/dose/apirofeno", "/fr/dose/tachipirina", "/hi/dose/doliprane", "/pt/dose/crocin"],
)
def test_a_brand_in_a_language_where_it_is_not_sold_is_not_indexed(path):
    assert NOINDEX.search(_html(path)), f"{path} debería llevar noindex"
    assert path not in _sitemap(), f"{path} no debería estar en el sitemap"


@pytest.mark.parametrize(
    "path",
    [
        "/dose/tylenol", "/dose/tachipirina",  # inglés: siempre
        "/es/dose/tempra", "/es/dose/dalsy", "/fr/dose/doliprane", "/de/dose/ben-u-ron",
        "/pt/dose/alivium", "/pt/dose/tylenol", "/ar/dose/adol", "/hi/dose/crocin",
        "/fr/dose/advil",  # Canadá y el Magreb también hablan francés
        "/ru/dose/paracetamol", "/hi/dose/ibuprofen",  # genéricos: en todas
    ],
)
def test_a_brand_where_it_is_sold_and_every_generic_are_indexed(path):
    assert not NOINDEX.search(_html(path)), f"{path} no debería llevar noindex"
    assert path in _sitemap(), f"{path} debería estar en el sitemap"


def test_hreflang_does_not_point_at_an_edition_that_is_not_indexed():
    h = _html("/dose/tylenol")
    langs = set(re.findall(r'rel="alternate" hreflang="([a-z-]+)"', h))
    assert "es" in langs and "pt" in langs and "fr" in langs
    assert "ru" not in langs and "de" not in langs and "hi" not in langs


def test_the_language_switch_still_reaches_every_edition():
    # quien está en la página inglesa y lee ruso tiene que poder pasar a la rusa
    assert 'href="/ru/dose/tylenol"' in _html("/dose/tylenol")


def test_nothing_in_the_sitemap_asks_not_to_be_indexed():
    malas = [p for p in _sitemap() if (DIST / p.strip("/") / "index.html").exists()
             and NOINDEX.search((DIST / p.strip("/") / "index.html").read_text("utf-8")[:4000])]
    assert not malas, malas[:10]
