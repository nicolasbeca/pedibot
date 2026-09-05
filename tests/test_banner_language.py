r"""The banner is the one line that has to be readable (5-sep-2026).

It sits above the answer and tells a frightened parent to phone for help. Two things were wrong
with it, both found by asking the live site the questions the golden set had just started to ask:

  * With no country chosen, the number is not a number — it is a phrase — and there was one
    phrase, in English, interpolated into all eight languages:

        🚨 Rufen Sie jetzt your local emergency number (112 in the EU, 911 in the Americas) an…

    That is the fallback for every Telegram user before they set a country and every visitor
    whose browser locale is not on the list.

  * The mental-health banner names two numbers, "call {mental} (or {emergency} if there is
    immediate danger)". Where a country has no separate line for suicide — or where none was
    chosen — those are the same string, and it said it twice, in nested brackets, above a parent
    who had just typed that their child wants to die.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from pedibot.bot.answer import SUPPORTED_LANGS, EmergencyNumbers, build_banner
from pedibot.bot.triage import Triage

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Words that only belong in the English banner. Any of them elsewhere is the fallback leaking.
ENGLISH_ONLY = re.compile(
    r"your local emergency number|in the Americas|immediate danger|emergency department", re.I
)


@pytest.fixture(scope="module")
def parts() -> tuple[Triage, EmergencyNumbers]:
    return (
        Triage(ROOT / "config" / "red_flags.yaml"),
        EmergencyNumbers(ROOT / "config" / "emergency_numbers.yaml"),
    )


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_no_country_still_speaks_the_readers_language(lang, parts) -> None:
    triage, numbers = parts
    tr = triage.assess("mi hijo no puede respirar")
    assert tr.level == "emergency", "el caso de prueba dejó de disparar"
    banner = build_banner(tr, lang, numbers.get(None, lang))
    assert banner
    if lang != "en":
        found = ENGLISH_ONLY.search(banner)
        assert not found, f"[{lang}] la banda dice «{found.group(0)}» en inglés: {banner[:110]}"


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_the_mental_health_banner_does_not_repeat_itself(lang, parts) -> None:
    triage, numbers = parts
    tr = triage.assess("mi hijo quiere morir")
    assert tr.level == "mental_health"
    nums = numbers.get(None, lang)
    banner = build_banner(tr, lang, nums)
    assert banner
    phrase = str(nums["emergency"])
    assert banner.count(phrase) == 1, f"[{lang}] repite «{phrase}»: {banner[:160]}"
    if lang != "en":
        assert not ENGLISH_ONLY.search(banner), f"[{lang}] inglés en la banda: {banner[:110]}"


def test_two_different_numbers_are_still_both_given(parts) -> None:
    """The bracket is not noise where it earns its place: Spain has a suicide line of its own and
    a parent needs both it and 112."""
    triage, numbers = parts
    tr = triage.assess("mi hijo quiere morir")
    banner = build_banner(tr, "es", numbers.get("ES", "es"))
    assert banner and "024" in banner and "112" in banner


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_every_language_has_its_own_fallback_phrase(lang) -> None:
    """A language missing from the map falls back to English, which is exactly the bug."""
    import yaml

    raw = yaml.safe_load((ROOT / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8"))
    phrases = raw["default"]["emergency"]
    assert isinstance(phrases, dict), "la reserva volvió a ser una sola cadena"
    assert lang in phrases, f"[{lang}] sin frase de reserva propia"
