"""La página que dice quién hay detrás, y lo que todavía no hay (11-sep-2026).

En salud, la señal de fondo que Google y un lector buscan es la misma: **quién hace esto y con
qué método**. El sitio no la tenía. Las guías llevan cita, fecha de publicación y fecha de
revisión, y ningún revisor — y ponerlo sin que un pediatra haya revisado nada sería mentir, que
es la línea que este proyecto no cruza.

La página se escribe con lo que es verdad hoy: la hace una persona que no es médico; el triaje
decide antes que la IA; las cifras salen de tablas publicadas y nunca de un modelo; se busca
sólo en el catálogo; cada frase lleva el número del pasaje del que sale; y **ningún pediatra ha
revisado estos textos**, dicho con esas palabras.

Esto fija las tres cosas que pueden pudrirse: que la página exista en las ocho lenguas, que la
frase incómoda esté en todas (y traducida, no heredada del inglés), y que **el marcado no diga
que hay revisor** mientras no lo haya.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"
LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


def _pagina(lang: str) -> str:
    p = DIST / ("about/index.html" if lang == "en" else f"{lang}/about/index.html")
    if not p.exists():
        pytest.skip("el sitio no está construido en esta copia")
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("lang", LANGS)
def test_la_pagina_existe_en_cada_lengua(lang: str):
    assert len(_pagina(lang)) > 2000, f"la página /about de {lang} está vacía o es un esqueleto"


@pytest.mark.parametrize("lang", [lg for lg in LANGS if lg != "en"])
def test_la_frase_incomoda_esta_traducida(lang: str):
    """«Ningún pediatra ha revisado estos textos» no puede salir en inglés en la página hindi."""
    ingles, otra = _pagina("en"), _pagina(lang)
    marca = "No paediatrician has reviewed"
    assert marca in ingles, "la versión inglesa ya no dice la frase; es el punto de la página"
    assert marca not in otra, (
        f"la página /about de {lang} deja la frase del revisor en inglés: es respaldo, no traducción"
    )


def test_ninguna_pagina_del_sitio_dice_que_hay_revisor():
    """`reviewedBy` y `lastReviewed` se ponen el día que un pediatra revise, y ni un día antes."""
    if not DIST.exists():
        pytest.skip("el sitio no está construido en esta copia")
    mienten = []
    for p in DIST.rglob("index.html"):
        h = p.read_text(encoding="utf-8")
        if re.search(r'"(reviewedBy|lastReviewed)"', h):
            mienten.append(str(p.parent.relative_to(DIST)).replace("\\", "/"))
    assert not mienten, f"estas páginas declaran un revisor que no existe: {mienten}"


def test_las_cifras_de_la_pagina_son_las_del_catalogo():
    """Un número inventado en la página del método se lleva por delante la página entera."""
    h = _pagina("en")
    fuentes = json.loads((ROOT / "web" / "site" / "src" / "data" / "sources.json").read_text("utf-8"))
    publicos = [f for f in fuentes if f.get("usage") != "excluido"]
    orgs = {f["org"] for f in publicos}
    assert str(len(publicos)) in h, f"la página no dice los {len(publicos)} documentos del catálogo"
    assert str(len(orgs)) in h, f"la página no dice los {len(orgs)} organismos del catálogo"


@pytest.mark.parametrize("lang", LANGS)
def test_se_llega_a_ella_desde_cualquier_pagina(lang: str):
    """Una página de confianza a la que no se llega no da confianza: va en el pie, en todas."""
    inicio = DIST / ("index.html" if lang == "en" else f"{lang}/index.html")
    if not inicio.exists():
        pytest.skip("el sitio no está construido en esta copia")
    h = inicio.read_text(encoding="utf-8")
    esperado = "/about" if lang == "en" else f"/{lang}/about"
    assert f'href="{esperado}"' in h, f"la portada {lang} no enlaza a {esperado}"
