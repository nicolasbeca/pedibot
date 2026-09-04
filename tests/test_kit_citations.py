"""Every citation on the kit page must name a document that exists (4-sep-2026).

The page was written from searches of the index, so its sources are real — but the titles were
typed by hand into i18n.ts, and a hand-typed citation is exactly the kind of thing that drifts
from the catalogue it claims to quote. The site's whole promise is that a reader can follow a
citation and check us. A citation naming a document nobody can find is worse than no citation,
because it looks like evidence.

Shortened titles are allowed and normal — "Sueroral Hiposódico" for "Prospecto: Sueroral
Hiposódico polvo para solución oral (CIMA 59877)" — as long as what is printed leads to exactly
one real document.
"""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
I18N = ROOT / "web" / "site" / "src" / "i18n.ts"
SOURCES = ROOT / "web" / "site" / "public" / "sources.json"


def catalogue() -> list[tuple[str, str]]:
    docs = json.loads(SOURCES.read_text(encoding="utf-8"))
    return [(d.get("org", ""), d.get("title", "")) for d in docs if d.get("usage") != "excluido"]


def cited_pairs() -> set[tuple[str, str]]:
    text = I18N.read_text(encoding="utf-8")
    cites = re.findall(r'cite: "([^"]+)"', text)
    cites += re.findall(r'(?:store|expiry)_cite: "([^"]+)"', text)
    pairs: set[tuple[str, str]] = set()
    for c in cites:
        for part in c.split(" · "):
            m = re.match(r"\s*(.+?)\s*—\s*[“\"](.+?)[”\"]\s*$", part)
            assert m, f"cita que no se puede leer: {part!r}"
            pairs.add((m.group(1).strip(), m.group(2).strip()))
    return pairs


def test_the_kit_page_cites_documents_that_are_in_the_catalogue() -> None:
    docs = catalogue()
    pairs = cited_pairs()
    assert len(pairs) >= 15, f"solo {len(pairs)} citas distintas; ¿se ha vaciado la página?"
    missing = []
    for org, title in sorted(pairs):
        hits = [t for o, t in docs if o == org and title.lower() in t.lower()]
        if not hits:
            missing.append(f"{org} — “{title}”")
    assert not missing, f"citas que no corresponden a ningún documento: {missing}"


def test_no_citation_is_so_vague_it_matches_several_documents() -> None:
    """A citation has to lead somewhere specific. "Cuídame" matching two different Junta de
    Andalucía booklets would send a reader to the wrong one half the time."""
    docs = catalogue()
    ambiguous = {}
    for org, title in sorted(cited_pairs()):
        hits = {t for o, t in docs if o == org and title.lower() in t.lower()}
        exact = {t for o, t in docs if o == org and t == title}
        if len(hits) > 1 and not exact:
            ambiguous[f"{org} — “{title}”"] = sorted(hits)
    assert not ambiguous, f"citas ambiguas: {ambiguous}"
