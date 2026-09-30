"""La página de herramientas y la barra de arriba (30-sep-2026, operador).

«No entiendo tener duplicadas herramientas en el menú superior y en el desplegable», y el
desplegable con barra de desplazamiento «es incomodísimo». Desde hoy la barra lleva sólo
Herramientas, Guías y Urgencias; todas las herramientas viven en /tools (el bot en el centro, el
chat es el logo) y en el panel del menú, en tres columnas.

Esto fija lo que se decidió, sobre el sitio construido: que la página existe en las ocho lenguas
y enlaza cada herramienta y el chat, que la barra no vuelve a llenarse de herramientas y que el
panel no se desplaza en el ordenador.
"""

from __future__ import annotations

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DIST = RAIZ / "web" / "site" / "dist"
LANGS = ["", "es", "fr", "de", "ru", "ar", "pt", "hi"]
HERRAMIENTAS = ["/emergency", "/warning-signs", "/dose", "/growth", "/vaccines", "/muac",
                "/diary", "/family", "/kit", "/emergency#by-country", "/#composer"]


def _html(ruta: str) -> str:
    f = DIST / ruta / "index.html"
    if not f.exists():
        pytest.skip("el sitio no está construido en esta copia")
    return f.read_text(encoding="utf-8")


@pytest.mark.parametrize("lang", LANGS)
def test_la_pagina_existe_y_enlaza_cada_herramienta(lang: str) -> None:
    pref = f"/{lang}" if lang else ""
    html = _html(f"{lang}/tools" if lang else "tools")
    hub = html[html.index("data-hub") :]
    for h in HERRAMIENTAS:
        assert f'href="{pref}{h}"' in hub, f"/tools ({lang or 'en'}) no enlaza {h}"


@pytest.mark.parametrize("lang", LANGS)
def test_la_barra_solo_lleva_lo_principal(lang: str) -> None:
    html = _html(lang or ".")
    barra = re.search(r'<nav class="mid"[^>]*>(.*?)</nav>', html, re.S)
    assert barra, "la barra no tiene la zona central"
    enlaces = re.findall(r'href="([^"]+)"', barra.group(1))
    pref = f"/{lang}" if lang else ""
    assert enlaces == [f"{pref}/tools", f"{pref}/guides", f"{pref}/emergency"], enlaces


def test_el_panel_no_se_desplaza_en_el_ordenador() -> None:
    base = (RAIZ / "web" / "site" / "src" / "layouts" / "Base.astro").read_text(encoding="utf-8")
    regla = re.search(r"\.navmenu > \.panel \{(.*?)\}", base, re.S)
    assert regla and "overflow" not in regla.group(1), "el panel vuelve a tener barra de desplazamiento"


@pytest.mark.parametrize("lang", LANGS)
def test_los_numeros_tienen_su_ancla(lang: str) -> None:
    html = _html(f"{lang}/emergency" if lang else "emergency")
    assert 'id="by-country"' in html
