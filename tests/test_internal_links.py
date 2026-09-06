"""Every internal link and every hreflang points at a page that was built (5-sep-2026).

Written after walking them for the first time: 27.635 links, 74 dead, all of them the language
switcher on a medicine page.

A generic drug is not spelled the same everywhere — ibuprofeno / ibuprofen / ibuprofène — so each
edition builds its page at its own slug, and the switcher derived the other editions by swapping
the prefix on the current path. From /ar/dose/ibuprofen it offered /pt/dose/ibuprofen, which
Portuguese had built as /pt/dose/ibuprofeno.

The hreflang half is the one that mattered more: the same list feeds those tags, so on every one
of those pages Google was being told about translations that return 404. Nothing failed, nothing
logged, and no test looked — the guide templates had four separate locks and the dose pages had
none, which is how the same clone rot lived here after being cleaned out there.

Skipped when there is no build: `npm run build` in web/site makes one.
"""

from __future__ import annotations

import collections
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"

pytestmark = pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")

HREF = re.compile(r'href="(/[^"#?]*)')
ALT = re.compile(r'hreflang="[a-z-]+" href="https://pedibot\.xyz(/[^"]*)')


def built() -> set[str]:
    """Everything the build produced, by the URL that reaches it."""
    out: set[str] = set()
    for f in DIST.rglob("*"):
        if not f.is_file():
            continue
        rel = "/" + f.relative_to(DIST).as_posix()
        out.add(rel)
        if f.name == "index.html":
            out.add(rel[: -len("index.html")].rstrip("/") or "/")
    return out


def reachable(url: str, have: set[str]) -> bool:
    u = url.rstrip("/") or "/"
    return u in have or f"{u}/" in have or f"{u}/index.html" in have


@pytest.fixture(scope="module")
def have() -> set[str]:
    return built()


def test_no_internal_link_is_dead(have: set[str]) -> None:
    bad: collections.Counter[str] = collections.Counter()
    where: dict[str, str] = {}
    for f in DIST.rglob("*.html"):
        src = "/" + f.relative_to(DIST).parent.as_posix()
        for m in HREF.finditer(f.read_text(encoding="utf-8", errors="replace")):
            if not reachable(m.group(1), have):
                bad[m.group(1)] += 1
                where.setdefault(m.group(1), src)
    assert not bad, "\n".join(
        f"{n}× {u}  (p.ej. desde {where[u]})" for u, n in bad.most_common(10)
    )


def test_no_hreflang_promises_a_page_that_does_not_exist(have: set[str]) -> None:
    """Worse than a dead link in a menu: this is what the search engines are told."""
    bad: collections.Counter[str] = collections.Counter()
    for f in DIST.rglob("*.html"):
        for m in ALT.finditer(f.read_text(encoding="utf-8", errors="replace")):
            if not reachable(m.group(1), have):
                bad[m.group(1)] += 1
    assert not bad, "\n".join(f"{n}× {u}" for u, n in bad.most_common(10))


def test_a_medicine_offers_the_right_name_in_each_language(have: set[str]) -> None:
    """The concrete case, kept by name so a regression is recognisable: the same drug, eight
    editions, three different spellings, and every switch link has to land."""
    page = DIST / "ar" / "dose" / "ibuprofen" / "index.html"
    assert page.exists(), "la página árabe del ibuprofeno cambió de sitio"
    alts = ALT.findall(page.read_text(encoding="utf-8", errors="replace"))
    assert len(alts) >= 8, f"solo {len(alts)} alternativas"
    assert any(a.endswith("/ibuprofeno") for a in alts), "ninguna alternativa usa el slug español"
    for a in alts:
        assert reachable(a, have), a


#: the eight guide templates: one per language, identical apart from their language wiring
_TPLS = sorted((ROOT / "web" / "site" / "src" / "pages").glob("**/guides/[[]...slug[]].astro"))


def _lang_of(tpl: pathlib.Path) -> str:
    """English lives at the root, every other language under its own folder."""
    parts = tpl.relative_to(ROOT / "web" / "site" / "src" / "pages").parts
    return "en" if parts[0] == "guides" else parts[0]


def test_every_guide_offers_the_chat_at_the_top_and_the_bottom() -> None:
    """A guide's way into the chat used to be one button below the whole article. Somebody who
    arrives from a search reads a paragraph and leaves without ever scrolling to it, so the same
    door is offered again under the opening line (6-sep-2026).

    Source-level on purpose: this one runs without a build.
    """
    assert len(_TPLS) == 8, f"esperaba 8 plantillas de guía, hay {len(_TPLS)}"
    for tpl in _TPLS:
        src = tpl.read_text(encoding="utf-8")
        assert src.count('class="ask-top"') == 1, f"{tpl.name} [{_lang_of(tpl)}]: falta el de arriba"
        assert src.count("s.ask_about") == 1, f"{tpl.name} [{_lang_of(tpl)}]: falta el de abajo"


def test_a_guide_never_sends_its_reader_to_another_language_chat() -> None:
    """The clone rot, in the place it would hurt most: a Spanish guide whose button opens the
    English chat. Both links in a file must carry that file's own prefix."""
    bad: list[str] = []
    for tpl in _TPLS:
        lang = _lang_of(tpl)
        want = "/?q=" if lang == "en" else f"/{lang}?q="
        found = re.findall(r"href=\{`(/[a-z]{0,2}\?q=)\$\{encodeURIComponent", tpl.read_text(encoding="utf-8"))
        assert len(found) == 2, f"{tpl.name}: esperaba dos enlaces al chat, hay {len(found)}"
        bad += [f"[{lang}] apunta a {f}, debería ser {want}" for f in found if f != want]
    assert not bad, "\n".join(bad)


def test_the_map_for_language_models_is_not_an_orphan() -> None:
    """/llms.txt is written for the assistants that answer questions from the web, and in thirty
    days not one of them had ever fetched it: it was mentioned only in a robots.txt COMMENT,
    which no crawler reads, and nothing on the site linked to it.

    The law measured on 4-sep is that crawling follows the link graph — 92% of pages one click
    from the homepage, 0% of orphans — so it now hangs off every page, in the head and the foot.
    """
    base = (ROOT / "web" / "site" / "src" / "layouts" / "Base.astro").read_text(encoding="utf-8")
    assert 'href="/llms.txt"' in base, "la cabecera ya no declara llms.txt"
    assert ">llms.txt</a>" in base, "el pie ya no lo enlaza"
