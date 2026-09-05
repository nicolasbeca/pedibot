"""Each edition of the site must introduce itself in its own language (4-sep-2026).

The German folder was cloned from the French one and the `title=` / `description=` strings, typed
by hand into each page rather than taken from the language catalogue, came with it. Russian and
Arabic were cloned in turn. So `/de`, `/ru` and `/ar` — and their guides and support pages —
carried `PediBot — des réponses pédiatriques sourcées` for weeks. Fifteen strings across three
languages, in the one tag Google prints in its results, and nothing failed.

The word-list scanner did not catch it either: its French markers were `enfant`, `urgences`,
`posologie` and the like, none of which appear in that sentence. A vocabulary is never complete,
so the guard here is structural instead — two editions sharing a title byte for byte is a clone,
whatever the words are.
"""

from __future__ import annotations

import collections
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"
LANGS = tuple(
    x
    for x in re.findall(
        r"'(\w+)'",
        re.search(
            r"export const LANGS: Lang\[\] = \[(.*?)\];",
            (ROOT / "web" / "site" / "src" / "i18n.ts").read_text(encoding="utf-8"),
        ).group(1),
    )
    if x != "en"  # English lives at the root, where there is no prefix to compare
)

pytestmark = pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")

TITLE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
DESC = re.compile(r'<meta name="description" content="([^"]*)"', re.I)


def pages() -> dict[str, str]:
    out = {}
    for f in DIST.rglob("index.html"):
        rel = f.relative_to(DIST).parent.as_posix()
        out["/" + ("" if rel == "." else rel)] = f.read_text(encoding="utf-8", errors="replace")
    return out


def lang_of(url: str) -> str:
    first = url.strip("/").split("/")[0]
    return first if first in LANGS else "en"


@pytest.mark.parametrize("what,pattern", [("título", TITLE), ("descripción", DESC)])
def test_no_two_language_editions_share_the_same_line(what: str, pattern: re.Pattern) -> None:
    seen: dict[str, set[str]] = collections.defaultdict(set)
    where: dict[str, list[str]] = collections.defaultdict(list)
    for url, html in pages().items():
        m = pattern.search(html)
        if not m:
            continue
        text = " ".join(m.group(1).split())
        seen[text].add(lang_of(url))
        where[text].append(url)
    shared = {t: sorted(where[t])[:5] for t, langs in seen.items() if len(langs) > 1}
    assert not shared, f"{what} compartido entre idiomas (clon sin traducir): {shared}"


def test_the_french_titles_are_gone_from_the_other_editions() -> None:
    """The exact strings that shipped, named so this cannot come back quietly."""
    gone = [
        "des réponses pédiatriques sourcées",
        "Guides pour les parents",
        "Soutenir PediBot",
    ]
    for url, html in pages().items():
        if lang_of(url) == "fr":
            continue
        head = TITLE.search(html)
        text = head.group(1) if head else ""
        for phrase in gone:
            assert phrase not in text, f"{url} sigue titulando en francés: {text}"


def test_every_page_says_which_edition_is_the_default() -> None:
    """x-default tells Google what to serve a reader it cannot place by language; it was missing
    from all 571 pages. A page with no English counterpart claims none rather than lying."""
    for url, html in pages().items():
        has_default = 'hreflang="x-default"' in html
        has_english = 'hreflang="en"' in html
        assert has_default == has_english, (
            f"{url}: x-default={has_default} pero alternativa inglesa={has_english}"
        )
