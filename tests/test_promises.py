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
AFFILIATE = re.compile(r"amazon\.[a-z.]{2,6}/[^\"']*\btag=|amzn\.to/|/dp/[A-Z0-9]{10}|[?&]tag=[\w-]+-\d\d", re.I)


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


def test_no_network_is_announced_without_being_deployed() -> None:
    """Checked against the data, not the type: `address: string | null` is the declaration and
    will always be there; what must not exist is an entry whose address is actually null."""
    text = (SITE / "src" / "tokens.ts").read_text(encoding="utf-8")
    start = text.index("export const TOKENS")
    # only the array: `shortAddress(address: string)` further down matches otherwise
    body = text[start : text.index(chr(93) + chr(59), start)]  # up to the closing ];
    entries = re.findall(r"address:\s*([^,\n]+)", body)
    assert entries, "no encuentro ninguna dirección en TOKENS"
    pending = [e for e in entries if e.strip() == "null"]
    assert not pending, f"{len(pending)} red(es) anunciadas sin desplegar"
    # trimmed to Base on 5-sep: the other two deployments still exist on their chains,
    # but three addresses on one page is three chances to send to the wrong one
    assert len(entries) == 1, f"se esperaba una sola red, hay {len(entries)}"


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
        d.get("title") for d in pub
        if (d.get("org_full") or "").count("(") != (d.get("org_full") or "").count(")")
    ]
    assert not unbalanced, f"nombres de organismo truncados: {unbalanced[:3]}"
