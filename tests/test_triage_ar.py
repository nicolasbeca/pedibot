"""Arabic triage: the two things that are grammar, not vocabulary (3-sep-2026).

Both were found by running the checklist against real sentences rather than by reading the
patterns. They are the Arabic equivalents of the homograph trap French had.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.retrieval import detect_lang
from pedibot.bot.triage import Triage, parse_age_months

CONFIG = pathlib.Path(__file__).resolve().parents[1] / "config" / "red_flags.yaml"


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(CONFIG)


@pytest.mark.parametrize(
    ("question", "level"),
    [
        ("طفلي لا يتنفس جيدا وأرى انسحاب الأضلاع", "emergency"),
        ("ابنتي لا تستجيب", "emergency"),  # feminine
        ("ابني لا يستجيب", "emergency"),  # masculine
        ("ابني عمره شهران وعنده حرارة", "urgent"),  # the dual
        ("ابنتي عمرها شهرين وعندها حرارة", "urgent"),
        ("ابتلع طفلي بطارية", "urgent"),
        ("طفلي يسعل منذ يومين", "routine"),
        ("ابنتي تسعل منذ يومين", "routine"),
    ],
)
def test_warning_signs_fire_in_arabic(triage: Triage, question: str, level: str) -> None:
    assert triage.assess(question).level == level


def test_a_verb_written_for_a_boy_also_fires_for_a_girl(triage: Triage) -> None:
    """Arabic conjugates the verb by gender: "لا يستجيب" is he, "لا تستجيب" is she. Every pattern
    was written in the masculine at first, which silently halved the children they covered."""
    assert triage.assess("ابنتي لا تستجيب").level == triage.assess("ابني لا يستجيب").level
    assert triage.assess("ابنتي ترفض الرضاعة").level == triage.assess("ابني يرفض الرضاعة").level


def test_the_dual_is_an_age(triage: Triage) -> None:
    """"شهران" means exactly two months. It is not "2 months", and the age parser reads digits —
    so the most important age rule in the checklist was silent for the age it exists for."""
    assert parse_age_months("ابني عمره شهران") == 2.0
    assert parse_age_months("ابنتي عمرها سنتان") == 24.0


def test_arabic_is_detected_by_its_script(triage: Triage) -> None:
    assert detect_lang("ابني عمره ثلاث سنوات ويسعل في الليل") == "ar"
    # a Latin brand name inside an Arabic sentence does not change the language
    assert detect_lang("كم جرعة Nurofen لطفلي وزنه 14 كغ؟") == "ar"
