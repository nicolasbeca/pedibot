"""Los organismos de la portada, descritos en el idioma de la página (11-sep-2026).

La banda de organismos dice qué es cada fuente —«Servicio Nacional de Salud, Inglaterra»,
«Biblioteca Nacional de Medicina de EE. UU.»—, y esas descripciones sólo existían en inglés,
castellano y francés. En las portadas **alemana, rusa, árabe, portuguesa e hindi, cinco de las
ocho casillas salían en inglés**: justo en la página que más presume de hablar ocho lenguas, y
justo en el bloque que existe para dar confianza.

Es la fuga de siempre en este proyecto —se escribe en dos o tres idiomas y los demás heredan el
respaldo inglés sin que nada falle—, y el detector de fugas no la ve porque mira titulares.

Se comprueba contra el sitio **construido**: para cada lengua que no sea el inglés, ninguna
descripción puede ser idéntica a la inglesa del mismo organismo.
"""

from __future__ import annotations

import html
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"
LANGS = ("es", "fr", "de", "ru", "ar", "pt", "hi")


def _band(lang: str) -> dict[str, str]:
    """{organismo: qué es}, leído de la banda de la portada de esa lengua."""
    p = DIST / ("index.html" if lang == "en" else f"{lang}/index.html")
    if not p.exists():
        pytest.skip("el sitio no está construido en esta copia")
    h = p.read_text(encoding="utf-8")
    m = re.search(r'<div class="orgs"[^>]*>(.*?)</div>\s*<p', h, re.S)
    assert m, f"la portada {lang} no tiene banda de organismos"
    pares = re.findall(
        r'<b[^>]*>([^<]+)</b>\s*<span class="que"[^>]*>([^<]*)', m.group(1)
    )
    return {html.unescape(n): html.unescape(q) for n, q in pares}


@pytest.mark.parametrize("lang", LANGS)
def test_ninguna_descripcion_se_queda_en_ingles(lang: str):
    ingles, otra = _band("en"), _band(lang)
    comunes = set(ingles) & set(otra)
    assert comunes, f"la portada {lang} no comparte ningún organismo con la inglesa"
    sin_traducir = sorted(o for o in comunes if otra[o] == ingles[o])
    assert not sin_traducir, (
        f"en la portada {lang} estos organismos se describen en inglés: {sin_traducir}"
    )


@pytest.mark.parametrize("lang", ("en", *LANGS))
def test_toda_casilla_dice_que_es_su_organismo(lang: str):
    """Una casilla sin descripción es peor que ninguna: la cifra sola no dice nada."""
    vacias = sorted(o for o, q in _band(lang).items() if not q.strip())
    assert not vacias, f"casillas sin descripción en {lang}: {vacias}"
