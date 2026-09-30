"""El buscador de números de urgencias (30-sep-2026).

La página de antes era una rejilla de 95 tarjetas («infumable, todo ahí al mogollón», el
operador). Ahora: el número del lector arriba, un desplegable doble continente → país y, en
pantallas anchas, el mapamundi. Esto fija que ningún país con número se quede fuera de ninguna
de las tres puertas, y que las 95 páginas de país sigan enlazadas desde la portada.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest
import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
SITE = RAIZ / "web" / "site"
PAISES = {k for k in yaml.safe_load((RAIZ / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8")) if k != "default"}


def test_cada_pais_tiene_continente() -> None:
    cont = json.loads((SITE / "src" / "data" / "continents.json").read_text(encoding="utf-8"))
    assert PAISES <= set(cont), f"sin continente: {sorted(PAISES - set(cont))}; corre scripts/build_world_map.py"
    assert set(cont.values()) <= {"africa", "asia", "europe", "north_america", "south_america", "oceania"}


def test_el_mapa_marca_los_paises_con_numero() -> None:
    svg = (SITE / "public" / "world.svg").read_text(encoding="utf-8")
    en_mapa = set(re.findall(r'data-cc="([A-Z]{2})"', svg))
    assert en_mapa <= PAISES
    # los pequeños no salen en el mapa de 110 m; para eso está el desplegable
    assert len(en_mapa) >= 80, len(en_mapa)
    assert len(svg) < 120_000, "el mapa ha engordado: se descarga en cada visita de escritorio"


@pytest.mark.parametrize("lang", ["", "es", "ar", "hi"])
def test_la_portada_ofrece_cada_pais_y_lo_enlaza(lang: str) -> None:
    f = SITE / "dist" / lang / "emergency" / "index.html"
    if not f.exists():
        pytest.skip("el sitio no está construido en esta copia")
    html = f.read_text(encoding="utf-8")
    pref = f"/{lang}" if lang else ""
    opciones = set(re.findall(r'<option value="([A-Z]{2})"', html))
    assert opciones == PAISES, sorted(PAISES ^ opciones)
    faltan = [cc for cc in PAISES if f'href="{pref}/emergency/{cc.lower()}"' not in html]
    assert not faltan, f"páginas de país sin enlace desde la portada: {faltan[:6]}"


@pytest.mark.parametrize("lang", ["", "es", "ar"])
def test_vacunas_usa_el_mismo_buscador(lang: str) -> None:
    """30-sep-2026: vacunas pasó al mismo buscador (continente → país y mapamundi) y su
    rejilla de enlaces a cada país quedó plegada."""
    f = SITE / "dist" / lang / "vaccines" / "index.html"
    if not f.exists():
        pytest.skip("el sitio no está construido en esta copia")
    html = f.read_text(encoding="utf-8")
    vac = set(yaml.safe_load((RAIZ / "config" / "vaccines.yaml").read_text(encoding="utf-8"))["countries"])
    pick = html[html.index('id="vx-pick"') :]
    opciones = set(re.findall(r'<option value="([A-Z]{2})"', pick))
    assert opciones == vac, sorted(opciones ^ vac)
    assert 'class="allc"' in html, "los enlaces a cada país ya no están plegados"
    pref = f"/{lang}" if lang else ""
    faltan = [cc for cc in vac if f'href="{pref}/vaccines/{cc.lower()}"' not in html]
    assert not faltan, faltan[:6]
