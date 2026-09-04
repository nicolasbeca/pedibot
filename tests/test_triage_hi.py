"""The safety layer reads Hindi before any Hindi page exists (5-sep-2026).

Yesterday the Portuguese pages shipped onto a safety layer that could not read Portuguese, and
only a review of the live site caught it. The order is reversed here: the rule-based check learns
the language first.

Both scripts, deliberately. A great many people in India type Hindi in Latin letters — "bukhar",
"saans nahi le raha", "behosh" — and nobody switches keyboards while their child is struggling to
breathe. A pattern that only matched Devanagari would miss most of what it exists for.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.retrieval import detect_lang
from pedibot.bot.triage import Triage

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


@pytest.mark.parametrize(
    "question,level",
    [
        ("मेरा बच्चा बेहोश है", "emergency"),
        ("दौरा पड़ा है", "emergency"),
        ("बच्चा साँस नहीं ले रहा", "emergency"),
        ("सिर में चोट लगी और बेहोश हो गया", "emergency"),
        ("बैटरी निगल ली", "urgent"),
        ("बहुत सुस्त है", "urgent"),
        ("आँखें धँसी हैं और पेशाब नहीं कर रहा", "urgent"),
        ("मेरा बेटा मरना चाहता है", "mental_health"),
        ("हल्की खाँसी दो दिन से", "routine"),
        # the same emergencies typed in Latin letters, which is how many will arrive
        ("bachcha saans nahi le raha", "emergency"),
        ("behosh ho gaya hai", "emergency"),
        ("mera beta marna chahta hai", "mental_health"),
    ],
)
def test_the_hindi_warning_signs_fire(triage: Triage, question: str, level: str) -> None:
    assert triage.assess(question).level == level


def test_every_rule_can_explain_itself_in_hindi(triage: Triage) -> None:
    """A rule that fires and then explains itself in English answers an Indian parent in a
    language they may not read, at the moment it matters most."""
    missing = [r.id for r in triage.rules if not r.reasons_by_lang.get("hi")]
    assert not missing, f"reglas sin razón en hindi: {missing}"


def test_the_reason_table_needs_no_code_change_for_a_new_language(triage: Triage) -> None:
    """It used to be one dataclass field per language, copied by name in the loader, so a new
    language silently answered in English — which is what happened to Hindi for ten minutes."""
    r = triage.rules[0]
    assert set(r.reasons_by_lang) >= {"fr", "de", "ru", "ar", "pt", "hi"}, r.reasons_by_lang


@pytest.mark.parametrize(
    "text,lang",
    [
        ("मेरे बेटे को बुखार है", "hi"),
        ("mere bacche ko bukhar hai kya karu", "hi"),
        ("bachcha saans nahi le raha", "hi"),
        # and it must not take anyone else's
        ("Mi hijo tiene fiebre", "es"),
        ("My child has a fever", "en"),
        ("Meu filho tem febre", "pt"),
    ],
)
def test_the_detector_knows_hindi_in_both_scripts(text: str, lang: str) -> None:
    assert detect_lang(text) == lang
