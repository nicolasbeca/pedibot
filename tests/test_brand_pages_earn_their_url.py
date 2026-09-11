"""Una página de marca tiene que decir algo suyo (11-sep-2026).

Search Console, 28 días: de las veinte consultas que traen impresiones al sitio, **nueve son de
marca con dosis** —«calculadora apiretal», «apiretal bebe 10 kilos», «dosis dalsy 40
calculadora»—. Es lo que más se busca de aquí con diferencia. Y esas páginas no tenían **ni un
solo `<h2>`**: título, calculadora y una tabla de 36 filas. Los números estaban; la pregunta,
tal y como la escribe un padre, no aparecía en ninguna parte.

Medido además el solapamiento entre ellas con 5-gramas sobre el texto visible: 28 parejas por
encima del 70 %, y las de arriba —Cetal ↔ Metacin, 96 %— **son literalmente el mismo medicamento
con las mismas concentraciones**. La tentación es rellenarlas con texto distinto para que no se
parezcan. Eso es paja, y aquí no se hace: lo que se ha añadido es lo que es verdad y sí cambia
—las preguntas respondidas con los números de esa marca, y en qué país se vende con qué otros
nombres—, que además es la duda real del padre que tiene otra caja en la mano.

Lo que este fichero fija no es un umbral de parecido —dos marcas del mismo fármaco se PARECEN, y
está bien— sino que cada página **se gane su URL**: que nombre su marca, que responda con sus
propios botes y que diga de qué país habla.
"""

from __future__ import annotations

import html
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"


def _marcas() -> list[dict]:
    datos = json.loads((ROOT / "web" / "site" / "src" / "data" / "drugs.json").read_text("utf-8"))
    return [b for d in datos.values() for b in d["brands"] if b.get("forms")]


def _pagina(slug: str, lang: str = "en") -> str:
    p = DIST / ("dose" if lang == "en" else f"{lang}/dose") / slug / "index.html"
    if not p.exists():
        pytest.skip("el sitio no está construido en esta copia")
    return p.read_text(encoding="utf-8")


def _texto(h: str) -> str:
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))


SLUGS = sorted({b["slug"] for b in _marcas()})


@pytest.mark.parametrize("slug", SLUGS)
def test_la_pagina_responde_la_pregunta_que_se_escribe(slug: str):
    """Un `<h2>` como mínimo, y la pregunta con el nombre de la marca dentro."""
    h = _pagina(slug)
    h2 = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<h2[^>]*>(.*?)</h2>", h, re.S)]
    assert h2, f"/dose/{slug} no tiene ni un encabezado: es un título y una tabla"
    nombre = next(b["name"] for b in _marcas() if b["slug"] == slug)
    primera = nombre.split(" ")[0].split("/")[0]
    assert any(primera.lower() in x.lower() for x in h2), (
        f"/dose/{slug}: ningún encabezado nombra «{primera}»; la página no es sobre esta marca"
    )


@pytest.mark.parametrize("slug", SLUGS)
def test_responde_con_los_botes_de_esa_marca(slug: str):
    """Los mililitros que se enseñan tienen que ser los de SUS presentaciones, no los de todas."""
    marca = next(b for b in _marcas() if b["slug"] == slug)
    texto = _texto(_pagina(slug))
    for f in marca["forms"]:
        cifra = re.search(r"\d+(?:[.,]\d+)?\s*mg\s*/\s*\d*\s*ml", f["label"])
        assert cifra, f["label"]
        assert cifra.group(0).replace(" ", "") in texto.replace(" ", ""), (
            f"/dose/{slug} no menciona «{cifra.group(0)}», que es una presentación suya"
        )


@pytest.mark.parametrize("slug", SLUGS)
def test_dice_de_que_pais_habla(slug: str):
    """Es lo único que distingue de verdad dos marcas del mismo fármaco, y la duda del padre."""
    marca = next(b for b in _marcas() if b["slug"] == slug)
    if not marca.get("countries"):
        pytest.skip(f"{slug} no tiene país en el catálogo")
    h = _pagina(slug)
    assert 'class="samemed"' in h, f"/dose/{slug} no dice en qué país se vende"
