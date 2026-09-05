"""One clinical case, every language the engine speaks (5-sep-2026).

Each language got its own triage test file, written when that language was added, and each one
tested the phrasings its author had in mind. Twelve Hindi cases passed. None of them was a baby
with a fever, and that is the rule the whole safety layer is built around:

    infant_fever_under_3_months — the only rule that fires from CONTEXT rather than from a
    literal pattern, through `requires: [age_under_3_months, fever]`.

In Hindi neither half worked. `parse_age_months` had no Devanagari units, `has_fever` had no
Hindi word for fever, so the rule was unreachable and the live site answered a question about a
two-month-old with 38.5 with advice about keeping the child hydrated. Spanish, English and
Portuguese all said "emergency department, today" to the same question.

So the case is written once here and asked in every language, and the parametrisation comes from
the engine's own language list — a language added without its phrases fails collection instead of
shipping a silent hole.

Two phrasings each: the number written as a digit and the age written as a word. They travel
through different code (`_AGE_PATTERNS` and `_WORD_AGES`) and the second was broken in Hindi and
Portuguese even after the first was fixed.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.answer import SUPPORTED_LANGS
from pedibot.bot.triage import Triage, parse_age_months

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


# A two-month-old with 38.5 °C. Nothing else in the sentence: no "lethargic", no "not feeding",
# nothing another rule could fire on. If this comes back routine, the context path is dead.
INFANT_FEVER: dict[str, tuple[str, ...]] = {
    "en": ("my 2 month old baby has a fever of 38.5", "my two month old has a fever"),
    "es": ("mi bebe de 2 meses tiene 38.5 de fiebre", "mi bebe de dos meses tiene fiebre"),
    "fr": ("mon bebe de 2 mois a 38.5 de fievre", "mon bebe de deux mois a de la fievre"),
    "de": ("mein baby von 2 monaten hat 38.5 fieber", "mein baby von zwei monaten hat fieber"),
    "ru": ("моему ребенку 2 месяца температура 38.5", "моему ребенку два месяца температура"),
    "ar": ("طفلي عمره 2 أشهر حرارته 38.5", "طفلي عمره شهرين حرارته 38.5"),
    "pt": ("meu bebe de 2 meses esta com febre de 38.5", "meu bebe de dois meses esta com febre"),
    "hi": ("मेरे 2 महीने के बच्चे को 38.5 बुखार है", "मेरे दो महीने के बच्चे को बुखार है"),
}

# The same age and the same fever, taken apart, so a failure says which half broke.
NEWBORN: dict[str, str] = {
    "en": "my newborn has a fever",
    "es": "mi recien nacido tiene fiebre",
    "fr": "mon nouveau-ne a de la fievre",
    "de": "mein neugeborenes hat fieber",
    "ru": "у новорожденного температура",
    "ar": "مولود جديد لديه حمى",
    "pt": "meu recem-nascido esta com febre",
    "hi": "नवजात को बुखार है",
}


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_the_language_has_phrases_written_for_it(lang: str) -> None:
    """The list is the engine's, not a copy: adding a language fails here until somebody writes
    down how a parent asks this question in it."""
    assert lang in INFANT_FEVER, f"[{lang}] escribe cómo se pregunta esto en ese idioma"
    assert lang in NEWBORN, f"[{lang}] falta la frase del recién nacido"


@pytest.mark.parametrize("lang", sorted(INFANT_FEVER))
def test_a_two_month_old_with_a_fever_is_urgent(triage: Triage, lang: str) -> None:
    for phrase in INFANT_FEVER[lang]:
        age = parse_age_months(phrase)
        assert age is not None and age <= 3, f"[{lang}] no lee la edad en «{phrase}» ({age})"
        assert triage.has_fever(phrase), f"[{lang}] no lee la fiebre en «{phrase}»"
        assert triage.assess(phrase).level == "urgent", f"[{lang}] no salta con «{phrase}»"


@pytest.mark.parametrize("lang", sorted(NEWBORN))
def test_a_newborn_with_a_fever_is_urgent(triage: Triage, lang: str) -> None:
    phrase = NEWBORN[lang]
    assert parse_age_months(phrase) == 0.5, f"[{lang}] no reconoce «recién nacido» en «{phrase}»"
    assert triage.assess(phrase).level == "urgent", f"[{lang}] no salta con «{phrase}»"


def test_a_word_boundary_still_works_after_devanagari() -> None:
    r"""The reason all of this was dead in Hindi, kept as a check of its own because it is not
    obvious and it will bite the next person who adds a Devanagari alternative to these regexes:
    Python's `\w` excludes combining vowel signs, and most Hindi words end in one, so `\b` finds
    no boundary there. `NOT_AFTER` does.
    """
    import re

    from pedibot.bot.triage import NOT_AFTER

    assert not re.search(r"महीने\b", "2 महीने के")
    assert re.search(rf"महीने{NOT_AFTER}", "2 महीने के")


@pytest.mark.parametrize("lang", sorted(INFANT_FEVER))
def test_an_older_child_with_a_fever_is_not_urgent(triage: Triage, lang: str) -> None:
    """The other half of the same rule: it must not fire for a four-year-old, or a parent learns
    to ignore it. Same sentence, one number changed."""
    phrase = INFANT_FEVER[lang][0].replace("2", "4", 1).replace("٢", "٤", 1)
    if parse_age_months(phrase) is None:  # the word-form languages change nothing here
        pytest.skip(f"[{lang}] la frase no lleva número")
    assert triage.assess(phrase).level != "urgent", f"[{lang}] salta con «{phrase}»"
