"""An answer points at the page that answers it better (5-sep-2026).

The chat already offered the guide written from the same sources. The rest of the site was
invisible from it: a parent asking about vaccines got the schedule as text with no way to the
table, and one asking about a dose got a single figure with no way to the calculator that would
give them the next one.

Two links, and only where the site genuinely has something better than prose. Not a row of
related pages: a health answer with a strip of buttons under it is one nobody reads to the end.

The URL is built here and the WORDS are not. Python sends the kind; the label comes from
i18n.ts, where it exists in eight languages. A Spanish string coming out of the engine would be
a ninth copy of a translation, waiting to drift from the other eight — which is the shape of most
of the bugs this project has had.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import SUPPORTED_LANGS, tool_link


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_the_link_lands_in_the_readers_own_edition(lang: str) -> None:
    prefix = "" if lang == "en" else f"/{lang}"
    assert tool_link("dose", lang).url == f"{prefix}/dose"
    assert tool_link("vaccines", lang).url == f"{prefix}/vaccines"


def test_a_known_country_goes_to_its_own_calendar() -> None:
    """The text answer lists the doses for one age. The country's page has the whole schedule,
    with the document it was transcribed from."""
    assert tool_link("vaccines", "es", "ES").url == "/es/vaccines/es"
    assert tool_link("vaccines", "en", "GB").url == "/vaccines/gb"
    assert tool_link("vaccines", "hi", "BR").url == "/hi/vaccines/br"


def test_no_country_still_reaches_the_tool() -> None:
    assert tool_link("vaccines", "fr", None).url == "/fr/vaccines"


def test_the_engine_sends_a_kind_and_not_a_label() -> None:
    """The words for these links live in i18n.ts in eight languages. If the engine ever starts
    sending text, that is a ninth translation nobody will remember to update."""
    link = tool_link("vaccines", "de", "DE")
    assert link.kind == "vaccines"
    assert not hasattr(link, "label"), "el motor ha empezado a traducir, que es cosa de la web"


@pytest.mark.parametrize("kind,expected", [("vaccines", "/es/vaccines"), ("dose", "/es/dose")])
def test_both_kinds_are_reachable_pages(kind: str, expected: str) -> None:
    """Both are real routes, in every edition: see tests/test_internal_links.py for the check
    that no link on the built site points at a page that does not exist."""
    assert tool_link(kind, "es").url == expected
