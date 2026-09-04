"""Every page must be reachable by following links, not only by sitemap (4-sep-2026).

Measured against 45 days of Googlebot in the access log, crawling tracks the shape of the link
graph almost exactly: 100% of the homepage, 92% of pages one click away, ~50% at two and three
clicks — and **0% of orphan pages**, which were in the sitemap the whole time. A sitemap is a
hint. A link is an instruction.

The bug this guards against was real and had been live for a while: the 120 `/{lang}/dose/{brand}`
pages — Dalsy, Calpol, Apiretal, Doliprane, twenty brands in six languages — linked to each other
and nothing on the site linked to them. An island. They are also the pages a parent is most likely
to search for by name, and not one had ever been crawled.
"""

from __future__ import annotations

import collections
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"
HREF = re.compile(r'<a\b[^>]*?href="([^"]+)"', re.I)
EXTERNAL = re.compile(r"^(https?:|mailto:|tel:|#|javascript:)", re.I)

pytestmark = pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")


def canon(path: str) -> str:
    return ("/" + path.split("#")[0].split("?")[0].strip("/")) or "/"


def graph() -> tuple[dict[str, set[str]], collections.Counter]:
    pages: dict[str, pathlib.Path] = {}
    for f in DIST.rglob("index.html"):
        rel = f.relative_to(DIST).parent.as_posix()
        pages[canon("" if rel == "." else rel)] = f
    out: dict[str, set[str]] = {}
    inbound: collections.Counter = collections.Counter()
    for url, f in pages.items():
        html = f.read_text(encoding="utf-8", errors="replace")
        targets = {canon(h) for h in HREF.findall(html) if not EXTERNAL.match(h)}
        out[url] = (targets & set(pages)) - {url}
        for t in out[url]:
            inbound[t] += 1
    return out, inbound


def test_no_page_is_reachable_only_through_the_sitemap() -> None:
    out, _ = graph()
    seen = {"/"}
    queue = collections.deque(["/"])
    while queue:
        for nxt in out[queue.popleft()]:
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    stranded = sorted(set(out) - seen)
    assert not stranded, f"{len(stranded)} páginas inalcanzables, p.ej. {stranded[:6]}"


def test_no_page_is_left_without_a_single_link_to_it() -> None:
    out, inbound = graph()
    orphans = sorted(u for u in out if u != "/" and inbound[u] == 0)
    assert not orphans, f"{len(orphans)} páginas sin enlaces entrantes: {orphans[:6]}"


def test_the_brand_pages_are_linked_from_the_dose_page_in_every_language() -> None:
    """The specific island, named: if the way in disappears again, say so here rather than in the
    access log three weeks later."""
    for lang in ("en", "es", "fr", "de", "ru", "ar"):
        prefix = "" if lang == "en" else f"/{lang}"
        page = DIST / (f"{prefix}/dose".strip("/")) / "index.html"
        assert page.exists(), page
        html = page.read_text(encoding="utf-8", errors="replace")
        links = [h for h in HREF.findall(html) if h.startswith(f"{prefix}/dose/")]
        assert len(links) >= 15, f"[{lang}] solo {len(links)} enlaces a marcas desde /dose"
