"""El «modo app»: dentro de la app de Android no se ve lo que Google Play no admite (1-oct-2026).

La app de Play es la propia web abierta por Chrome (TWA, `appgoogle.md`). Así que lleva todo lo
que lleva la web, incluidas dos cosas que Play no deja: pedir dinero por fuera de su sistema de
cobro (las donaciones en cripto de /support) y el contenido de tokens. Y el cartel «la app, en
camino», que dentro de la app no tiene sentido.

La app abre la web con `?source=android`. Un guion en la cabecera de TODAS las páginas lo ve,
lo guarda en `sessionStorage` (no en `localStorage`: Chrome comparte el almacenamiento entre la app
y el navegador, y el modo app se colaría en la web normal) y pone `in-app` en `<html>`. El CSS
esconde todo enlace a /support y todo lo marcado con `data-no-app`. Por enlace y no por lista:
un botón de apoyo que alguien añada mañana en otra página queda escondido sin acordarse de nada.
"""

from __future__ import annotations

import re

import pytest

from pedibot.settings import ROOT

DIST = ROOT / "web" / "site" / "dist"
PAGINAS = ["index.html", "es/index.html", "hi/index.html", "support/index.html", "es/support/index.html"]


@pytest.mark.parametrize("pagina", PAGINAS)
def test_every_page_carries_the_switch(pagina: str) -> None:
    html = (DIST / pagina).read_text(encoding="utf-8")
    assert "source=android" in html and "in-app" in html and "sessionStorage" in html, pagina


def _css() -> str:
    return "".join(f.read_text(encoding="utf-8") for f in (DIST / "_astro").glob("*.css"))


def test_the_css_hides_support_links_and_marked_blocks() -> None:
    css = re.sub(r"\s+", "", _css())
    # el compresor de CSS escribe la barra escapada: a[href$=\/support]
    formas = ('html.in-appa[href$="/support"]', "html.in-appa[href$=/support]", r"html.in-appa[href$=\/support]")
    assert any(f in css for f in formas), css[:200]
    assert "html.in-app[data-no-app]" in css


@pytest.mark.parametrize(
    ("pagina", "que"),
    [
        ("index.html", 'class="block appsoon"'),
        ("index.html", 'id="support"'),
        ("support/index.html", 'id="donar"'),
    ],
)
def test_the_blocks_play_does_not_allow_are_marked(pagina: str, que: str) -> None:
    html = (DIST / pagina).read_text(encoding="utf-8")
    i = html.index(que)
    etiqueta = html[html.rindex("<", 0, i) : html.index(">", i)]
    assert "data-no-app" in etiqueta, etiqueta


def test_the_switch_does_not_use_localstorage_for_the_app_flag() -> None:
    html = (DIST / "index.html").read_text(encoding="utf-8")
    guion = html[html.index("source=android") - 300 : html.index("source=android") + 300]
    assert "localStorage.setItem('pb-app'" not in guion and 'localStorage.setItem("pb-app"' not in guion
