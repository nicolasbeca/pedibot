"""El marcado de las páginas de dosis decía que el paracetamol es un producto (10-sep-2026).

Search Console lo cazó en /es/dose: «Debe especificarse "offers", "review" o "aggregateRating"».
No era un error de sintaxis. `Drug` tiene **dos** líneas de herencia en schema.org y una de ellas
es `Thing > Product > Drug`, así que el validador de productos de Google lo reclama como
mercancía y pide el precio o la valoración media de un jarabe para niños. Iban 168 páginas
construidas con ese tipo; Search Console solo había rastreado una.

La respuesta correcta no es la que sugiere el mensaje —inventar una valoración de un medicamento
infantil está prohibido por la política de Google y por la lista «nunca hacer esto» de este
proyecto— sino `Substance`, que es `Thing > MedicalEntity > Substance`, no pasa por `Product` y
admite `activeIngredient` exactamente igual.

En la misma línea vivía un segundo fallo que `check_lang_leak.py` no podía ver, porque mira los
titulares y no los datos estructurados: el índice `/dose` declaraba «Paracetamol, ibuprofen» en
inglés en los ocho idiomas, y además una sola entidad diciendo ser dos medicamentos.

Se comprueba contra el sitio **construido**, que es lo que Google lee.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"
LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")

#: Todo lo que hereda de Product en schema.org. Google reclama estos tipos para los fragmentos
#: de producto y les exige offers/review/aggregateRating; ninguno describe lo que hacemos.
PRODUCT_FAMILY = {
    "Product",
    "Drug",
    "DietarySupplement",
    "IndividualProduct",
    "ProductCollection",
    "ProductGroup",
    "ProductModel",
    "SomeProducts",
    "Vehicle",
}


def _pages() -> list[pathlib.Path]:
    return sorted(DIST.rglob("index.html"))


def _blocks(html: str) -> list[dict]:
    out: list[dict] = []
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        data = json.loads(b)
        out.extend(data if isinstance(data, list) else [data])
    return out


def _types(node: object) -> list[str]:
    """Todo @type a cualquier profundidad: el tipo prohibido vivía anidado en `about`."""
    found: list[str] = []
    if isinstance(node, dict):
        t = node.get("@type")
        if isinstance(t, str):
            found.append(t)
        elif isinstance(t, list):
            found.extend(x for x in t if isinstance(x, str))
        for v in node.values():
            found.extend(_types(v))
    elif isinstance(node, list):
        for v in node:
            found.extend(_types(v))
    return found


def _dose_index(lang: str) -> pathlib.Path:
    return (DIST / "dose" / "index.html") if lang == "en" else (DIST / lang / "dose" / "index.html")


def _generics(lang: str) -> list[str]:
    drugs = yaml.safe_load((ROOT / "config" / "drugs.yaml").read_text(encoding="utf-8"))["drugs"]
    return [d["generic"].get(lang) or d["generic"]["en"] for d in drugs.values()]


def test_no_page_claims_to_sell_a_product():
    pages = _pages()
    if not pages:
        pytest.skip("el sitio no está construido en esta copia")
    culpables: dict[str, set[str]] = {}
    for p in pages:
        malos = {t for t in _types(_blocks(p.read_text(encoding="utf-8"))) if t in PRODUCT_FAMILY}
        if malos:
            culpables[str(p.relative_to(DIST))] = malos
    assert not culpables, (
        f"{len(culpables)} páginas usan un tipo de la familia Product, y Google les exigirá "
        f"offers/review/aggregateRating: {sorted(culpables)[:5]}"
    )


@pytest.mark.parametrize("lang", LANGS)
def test_the_dose_index_names_both_medicines_in_its_own_language(lang: str):
    page = _dose_index(lang)
    if not page.exists():
        pytest.skip("el sitio no está construido en esta copia")
    med = [
        b for b in _blocks(page.read_text(encoding="utf-8")) if b.get("@type") == "MedicalWebPage"
    ]
    assert med, f"/{lang}/dose no lleva MedicalWebPage"
    about = med[0].get("about")
    assert isinstance(about, list), (
        f"/{lang}/dose describe los dos medicamentos como una sola entidad: {about!r}"
    )
    assert [a.get("name") for a in about] == _generics(lang), (
        f"/{lang}/dose nombra los medicamentos en otro idioma: "
        f"{[a.get('name') for a in about]!r} en vez de {_generics(lang)!r}"
    )


@pytest.mark.parametrize("lang", LANGS)
def test_every_brand_page_says_its_active_ingredient_in_its_own_language(lang: str):
    base = (DIST / "dose") if lang == "en" else (DIST / lang / "dose")
    paginas = [p for p in base.glob("*/index.html")] if base.exists() else []
    if not paginas:
        pytest.skip("el sitio no está construido en esta copia")
    genericos = set(_generics(lang))
    for p in paginas:
        med = [
            b for b in _blocks(p.read_text(encoding="utf-8")) if b.get("@type") == "MedicalWebPage"
        ]
        about = med[0].get("about") if med else None
        nodo = about[0] if isinstance(about, list) else about
        assert isinstance(nodo, dict), f"{p.relative_to(DIST)} sin `about`"
        assert nodo.get("activeIngredient") in genericos, (
            f"{p.relative_to(DIST)} dice que su principio activo es "
            f"{nodo.get('activeIngredient')!r}, que no es ninguno de {sorted(genericos)}"
        )
