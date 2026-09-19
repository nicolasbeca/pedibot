"""En el móvil tiene que haber un menú arriba (19-sep-2026).

Dicho por el operador con el teléfono en la mano: «no tiene sentido tener que buscar abajo del
todo este tipo de páginas». Y era verdad. Por debajo de 720 px la barra escondía sus pastillas
—están pensadas para caber en una fila— y a partir de ahí la única forma de llegar a las vacunas,
a las curvas, a las dosis o a la ficha de los hijos era **bajar por toda la portada hasta el
pie**: el chat, las lenguas, los avisos, las guías, los países, el cartel de la app y el porqué
del proyecto.

Un enlace que existe pero está a una pantalla y media de distancia es, para quien lo busca con
una mano y el niño en la otra, un enlace que no existe.

Lo que se comprueba:
  - que el menú esté en el HTML de todas las páginas, no sólo de la portada;
  - que lleve dentro las secciones que importan;
  - que sólo aparezca donde hace falta (por encima de 720 px la barra ya las enseña);
  - y que se pueda abrir **sin JavaScript**, porque es un `<details>` y no un menú de guion.
"""

from __future__ import annotations

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DIST = RAIZ / "web" / "site" / "dist"
BASE = (RAIZ / "web" / "site" / "src" / "layouts" / "Base.astro").read_text(encoding="utf-8")

pytestmark = pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")

#: Una de cada tipo de página, porque el menú vive en el layout y una página que no lo use se
#: quedaría sin él sin que nadie lo notara.
PAGINAS = [
    "index.html",
    "es/index.html",
    "ar/index.html",
    "es/vaccines/index.html",
    "es/emergency/ke/index.html",
    "es/family/index.html",
]


@pytest.mark.parametrize("rel", PAGINAS)
def test_the_menu_is_in_the_page(rel: str) -> None:
    html = (DIST / rel).read_text(encoding="utf-8")
    assert '<details class="navmenu"' in html, f"{rel}: sin menú, en el móvil no se llega a nada"
    trozo = html[html.index('<details class="navmenu"') :][:2000]
    assert "<summary" in trozo, f"{rel}: el menú no tiene con qué abrirse"


@pytest.mark.parametrize("rel", ["index.html", "es/index.html"])
def test_the_menu_carries_the_sections_that_matter(rel: str) -> None:
    html = (DIST / rel).read_text(encoding="utf-8")
    trozo = html[html.index('<details class="navmenu"') :]
    trozo = trozo[: trozo.index("</details>")]
    prefijo = "/es" if rel.startswith("es/") else ""
    for seccion in ("emergency", "vaccines", "growth", "dose", "family", "guides", "kit", "diary"):
        assert f'href="{prefijo}/{seccion}"' in trozo, f"{rel}: al menú le falta /{seccion}"


def test_the_menu_only_shows_where_it_is_needed() -> None:
    """Por encima de 720 px la barra ya enseña sus pastillas: dos menús para lo mismo confunden."""
    assert ".navmenu { position: relative; display: none; }" in BASE
    assert "@media (max-width: 720px) { .navmenu { display: block; } }" in BASE
    assert "@media (max-width: 720px) { .bar .hide-sm { display: none; } }" in BASE, (
        "esta prueba supone que la barra se esconde a 720; si cambia, el menú tiene que "
        "aparecer en el mismo punto o queda un hueco sin navegación"
    )


def test_it_opens_without_javascript() -> None:
    """Es un `<details>`, como el de los idiomas. Un menú que necesita un guion para abrirse no
    se abre en un teléfono al que se le cayó la conexión a mitad de carga."""
    assert '<details class="navmenu">' in BASE
    assert "navmenu" in BASE[BASE.index("details.langsel, details.navmenu") :][:200], (
        "el guion sólo lo mejora: cerrar al tocar fuera y con Escape"
    )


@pytest.mark.parametrize("rel", ["index.html", "es/index.html", "hi/index.html"])
def test_the_app_notice_says_what_can_be_done_today(rel: str) -> None:
    """El cartel de «la app, en camino» no promete fecha ni pide el correo —no tenemos por dónde
    mandarlo—: cuenta que la web ya se instala y ya funciona sin cobertura, que es cierto y es
    casi toda la app."""
    html = (DIST / rel).read_text(encoding="utf-8")
    assert 'class="block appsoon"' in html, f"{rel}: sin el cartel de la app"
    trozo = html[html.index('class="block appsoon"') :][:1400]
    limpio = re.sub(r"<[^>]*>", " ", trozo)
    assert len(limpio.split()) > 20, f"{rel}: el cartel está vacío"
