"""Guides are the only pages earning traffic, so they carry the SEO work (2-sep-2026).

Measured over fourteen days: every single visit Google sent landed on a guide or a home page,
never on one of the 1,442 dose pages. So the two things done to guides are locked here — the
links between them and the FAQ data — against the built site, which is what Google actually reads.

The FAQ count is compared with the markdown on purpose: the first version of the parser used
`\\Z`, which is Python and not JavaScript, and silently dropped the last question of every guide.
Nothing failed; the data was just quietly incomplete.
"""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"
CONTENT = ROOT / "web" / "content"


def _built(lang: str) -> list[tuple[pathlib.Path, pathlib.Path]]:
    """(markdown, built html) for every published guide, or nothing if the site is not built."""
    base = DIST / "guides" if lang == "en" else DIST / "es" / "guides"
    out = []
    for md in sorted((CONTENT / lang).glob("*.md")):
        html = base / md.stem / "index.html"
        if html.exists():
            out.append((md, html))
    return out


def _jsonld(html: str) -> list[dict]:
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    )
    found: list[dict] = []
    for b in blocks:
        data = json.loads(b)
        found.extend(data if isinstance(data, list) else [data])
    return found


def test_every_question_in_a_guide_reaches_the_faq_data():
    pairs = _built("en") + _built("es")
    if not pairs:
        return  # site not built in this checkout
    for md, html in pairs:
        text = md.read_text(encoding="utf-8")
        # only the bold lines INSIDE the questions section: guides also use bold as a label in
        # the body ("Límites de pantalla por edad:"), which is not a question and must not count
        section = re.search(
            r"^##\s+(?:Common questions|Preguntas (?:frecuentes|habituales))\s*$(.*?)(?=^##\s|\Z)",
            text,
            re.M | re.S,
        )
        if not section:
            continue
        asked = len(re.findall(r"^\*\*.+?\*\*", section.group(1), re.M))
        if not asked:
            continue
        faq = [d for d in _jsonld(html.read_text(encoding="utf-8")) if d.get("@type") == "FAQPage"]
        assert faq, f"{md.stem}: {asked} questions in the guide and no FAQ data"
        assert len(faq[0]["mainEntity"]) == asked, f"{md.stem}: questions lost on the way"


def test_no_guide_is_an_island():
    """There were zero links between guides: a reader arriving from a search had nowhere to go."""
    for lang, prefix in (("en", "/guides/"), ("es", "/es/guides/")):
        pairs = _built(lang)
        if len(pairs) < 2:
            continue
        for md, html in pairs:
            body = html.read_text(encoding="utf-8")
            links = {
                m for m in re.findall(rf'href="{prefix}([a-z0-9_]+)"', body) if m != md.stem
            }
            assert links, f"{md.stem} does not link to any other guide"
