"""Run the mixed-language scan over the last build, if there is one (3-sep-2026).

The deploy always builds before it runs the suite, so in the path that matters this is enforced;
on a bare checkout with no dist there is nothing to scan and the test skips.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_lang_leak import DIST, MARKERS, leaks, scan  # noqa: E402


@pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")
def test_no_page_shipped_in_the_wrong_language() -> None:
    bad = scan(DIST)
    assert not bad, {k: v[:2] for k, v in list(bad.items())[:5]}


def test_the_scan_actually_catches_a_leak() -> None:
    """A checker that never fires is worse than none: prove it fires."""
    spanish_on_a_french_page = "<title>¿Debo llevar a mi hijo a urgencias?</title>"
    assert leaks(spanish_on_a_french_page, "fr")
    assert not leaks(spanish_on_a_french_page, "es")


def test_every_language_has_markers() -> None:
    """A language with no markers of its own can never be caught leaking into another."""
    from check_lang_leak import ROOT as SCRIPT_ROOT

    text = (SCRIPT_ROOT / "web" / "site" / "src" / "i18n.ts").read_text(encoding="utf-8")
    import re

    # anchored on `export const LANGS`: unanchored it matched RTL_LANGS, which lists only Arabic
    langs = re.findall(
        r"'(\w+)'", re.search(r"export const LANGS: Lang\[\] = \[(.*?)\]", text).group(1)
    )
    assert set(langs) == set(MARKERS), f"añade marcadores para {set(langs) ^ set(MARKERS)}"


def test_the_scan_now_catches_the_title_that_slipped_past_it() -> None:
    """It did not, for weeks. The German home page carried the French title and none of the
    French markers — enfant, urgences, posologie — appear in it, so the scan said the site was
    clean. A word list is never finished; this pins the words that were missing.
    """
    french_on_a_german_page = (
        "<title>PediBot — des réponses pédiatriques sourcées</title>"
        '<meta name="description" content="Assistant gratuit pour les parents : il répond '
        'uniquement à partir de recommandations pédiatriques publiées.">'
    )
    assert leaks(french_on_a_german_page, "de")
    assert leaks("<title>Guides pour les parents — PediBot</title>", "ru")
    assert leaks(
        "<title>Soutenir PediBot — gratuit pour toutes les familles</title>", "ar"
    )
    # and none of it fires on the page it actually belongs to
    assert not leaks(french_on_a_german_page, "fr")


def test_the_spanish_word_for_free_is_not_read_as_french() -> None:
    """`gratuit` was added as a French marker and matched inside the Spanish `gratuito`, which
    flagged the Spanish home page. Markers have to end where the word ends."""
    spanish = '<meta name="description" content="Asistente gratuito para padres.">'
    assert not leaks(spanish, "es")
