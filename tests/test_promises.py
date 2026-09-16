"""The promises the site makes in six languages, checked mechanically (4-sep-2026).

A promise that lives only in prose erodes. These are the three the project cannot afford to lose
quietly, so they are assertions now:

  * **No affiliate links, anywhere.** The operator considered a commission-earning buying guide on
    4-sep and decided against it: the arithmetic was about one euro a month, an affiliate link is
    by construction the third-party tracker the site promises not to have, and a commission turns
    a clinical recommendation into something that can no longer be defended by citing the
    guideline. If that decision is ever reversed it should be reversed on purpose.
  * **No ads, in every language.** A promise kept in five languages and dropped in the sixth is
    the shape of every bug this project has had.
  * **No network announced but undeployed.** The token page said for a day that it was "going to"
    Solana and HyperEVM after both had launched.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "web" / "site"
DIST = SITE / "dist"

#: What "shows no ads" is in each language, as the site actually words it.
NO_ADS = {
    "en": "no ads",
    "es": "anuncios",
    "fr": "publicité",
    "de": "Werbung",
    "ru": "рекламу",
    "ar": "إعلانات",
}

#: Affiliate links, as they actually look. Amazon tags, shortened Amazon links, and any bare
#: product page — a /dp/ URL with no tag today is a /dp/ URL with a tag tomorrow.
AFFILIATE = re.compile(
    r"amazon\.[a-z.]{2,6}/[^\"']*\btag=|amzn\.to/|/dp/[A-Z0-9]{10}|[?&]tag=[\w-]+-\d\d", re.I
)


@pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")
def test_not_one_affiliate_link_anywhere_on_the_site() -> None:
    guilty = []
    for f in DIST.rglob("*.html"):
        m = AFFILIATE.search(f.read_text(encoding="utf-8", errors="replace"))
        if m:
            guilty.append(f"{f.relative_to(DIST)}: {m.group(0)}")
    assert not guilty, f"enlaces de afiliado encontrados: {guilty[:5]}"


@pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")
@pytest.mark.parametrize("lang,word", sorted(NO_ADS.items()))
def test_the_no_ads_promise_survives_in_every_language(lang: str, word: str) -> None:
    prefix = "" if lang == "en" else lang
    page = DIST / prefix / "support" / "index.html" if prefix else DIST / "support" / "index.html"
    assert page.exists(), page
    assert word in page.read_text(encoding="utf-8", errors="replace"), (
        f"[{lang}] la página de apoyo ya no promete que no hay anuncios"
    )


@pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")
def test_el_sitio_no_menciona_el_token() -> None:
    """16-sep-2026, decisión del operador: fuera del sitio toda mención al token de Base/Virtuals.

    La regla de antes vigilaba que no se anunciara una red sin desplegar; ésta vigila que no
    vuelva ninguna. Lo de dentro —las alertas de compra y venta— no es el sitio y sigue.
    """
    sospechosas = []
    for f in DIST.rglob("*.html"):
        texto = f.read_text(encoding="utf-8", errors="replace")
        for palabra in ("PDBT", "Virtuals", "basescan"):
            if palabra.lower() in texto.lower():
                sospechosas.append(f"{f.relative_to(DIST)}: {palabra}")
    assert not sospechosas, f"el token ha vuelto a la web: {sospechosas[:5]}"


def test_y_tampoco_en_las_traducciones() -> None:
    """El HTML se construye; las cadenas son la fuente."""
    i18n = (SITE / "src" / "i18n.ts").read_text(encoding="utf-8")
    assert "PDBT" not in i18n and "Virtuals" not in i18n
    # «session token» es el identificador de sesión y no tiene nada que ver
    for linea in i18n.splitlines():
        if "token" in linea.lower():
            assert "session token" in linea, f"mención al token: {linea.strip()[:90]}"


def test_the_catalogue_is_the_same_in_every_place_it_is_published() -> None:
    """The site imports one copy, serves another and the open dataset is a third. They drifted
    once already, when a YAML comma truncated three publisher names in only some of them."""
    pub = json.loads((SITE / "public" / "sources.json").read_text(encoding="utf-8"))
    src = json.loads((SITE / "src" / "data" / "sources.json").read_text(encoding="utf-8"))
    assert len(pub) == len(src)
    live = [d for d in pub if d.get("usage") != "excluido"]
    dataset = ROOT / "dataset" / "sources.json"
    if dataset.exists():
        assert len(json.loads(dataset.read_text(encoding="utf-8"))) == len(live)
    unbalanced = [
        d.get("title")
        for d in pub
        if (d.get("org_full") or "").count("(") != (d.get("org_full") or "").count(")")
    ]
    assert not unbalanced, f"nombres de organismo truncados: {unbalanced[:3]}"
