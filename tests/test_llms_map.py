"""The map we hand to answer engines has to point at pages that exist (4-sep-2026).

`llms.txt` is generated from the collections at build time precisely so it cannot drift into
describing a site that no longer exists — every hand-written index this project has had did drift.
This is the guard on that promise: every link it publishes must resolve to a page that was
actually built, and it must list every language.

Why it is worth having at all: over the 30 days to 4-sep the answer engines were the second
largest group of legitimate crawlers after Google — Anthropic 83 fetches, OpenAI 55, Perplexity
26. They already read the site. llms.txt is a proposed convention rather than a standard and no
crawler is known to weigh it, but it costs one generated file and it cannot lie.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"
LLMS = DIST / "llms.txt"

pytestmark = pytest.mark.skipif(not LLMS.exists(), reason="no hay build en web/site/dist")


def links() -> list[str]:
    return re.findall(r"\]\((https://pedibot\.xyz[^)]*)\)", LLMS.read_text(encoding="utf-8"))


def built(url: str) -> bool:
    rel = url.replace("https://pedibot.xyz", "").lstrip("/")
    if not rel:
        return (DIST / "index.html").exists()
    return (DIST / rel).exists() or (DIST / rel / "index.html").exists()


def test_every_link_in_the_map_points_at_a_page_that_was_built() -> None:
    broken = [u for u in links() if not built(u)]
    assert not broken, f"{len(broken)} enlaces rotos, p.ej. {broken[:5]}"


def test_the_map_covers_every_language_and_all_the_guides() -> None:
    text = LLMS.read_text(encoding="utf-8")
    sections = re.findall(r"^## Guides — (.+?) \((\d+)\)$", text, re.M)
    assert len(sections) == 6, f"idiomas listados: {sections}"
    assert sum(int(n) for _, n in sections) == len(list((ROOT / "web" / "content").rglob("*.md")))


def test_the_map_states_the_rules_that_make_the_site_worth_quoting() -> None:
    """If the promise ever leaves the page, it should leave this file too — loudly, not quietly."""
    text = LLMS.read_text(encoding="utf-8")
    for claim in ("names the document it came from", "never from a language model", "it says so"):
        assert claim in text, f"falta la regla: {claim}"
