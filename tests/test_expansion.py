"""Cross-lingual query expansion (26-ago-2026).

Two golden-set failures had the same root cause: the question is in one language and the leaflet
that answers it is in the other. The `en` table already reached the Spanish sheets; the Spanish
side only mapped Spanish to Spanish, so a question like "¿cuánto tiene que dormir…?" never reached
the WHO guideline, which is in English.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.retrieval import Synonyms

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def syn() -> Synonyms:
    return Synonyms(ROOT / "config" / "synonyms.yaml")


def test_spanish_to_spanish_still_works(syn: Synonyms):
    """The colloquial → leaflet mapping must survive the new table."""
    got = syn.expand("le duele la barriga y tiene cagalera", "es")
    assert "dolor abdominal" in got and "gastroenteritis" in got


def test_english_expansion_unchanged(syn: Synonyms):
    got = syn.expand("my child has a fever", "en")
    assert "fiebre" in got


def test_plain_stomach_pain_does_not_pull_gastroenteritis(syn: Synonyms):
    """«stomach pain» is not «stomach flu»: the gastro leaflet was outranking the abdominal one."""
    got = syn.expand("Severe continuous stomach pain that is getting worse, he is 9", "en")
    assert "dolor abdominal" in got
    assert "gastroenteritis" not in got


def test_multiword_trigger_matches_the_phrase(syn: Synonyms):
    """…but «stomach bug» / «stomach flu» do mean gastroenteritis."""
    got = syn.expand("my son has a stomach bug", "en")
    assert "gastroenteritis" in got


def test_unknown_language_returns_nothing(syn: Synonyms):
    """The negative example is a code that will never be a language of this site.

    It used to be French, then German — each time, the day that language shipped its tables the
    test went green while asserting the opposite of what we wanted, exactly as `test_api` once
    asserted that the German chat should return 422. A test that names a real language is a copy
    of the language list, and the copy is always the one nobody updates.
    """
    from pedibot.bot.answer import SUPPORTED_LANGS

    never = next(c for c in ("zz", "qq", "xx") if c not in SUPPORTED_LANGS)
    assert syn.expand("mein Kind hat Fieber", never) == []
    # and every language that IS supported expands: see tests/test_synonyms_coverage.py
    assert "fever" in syn.expand("mon enfant a de la fievre", "fr")


def test_spanish_question_reaches_the_english_only_material(syn: Synonyms):
    """Sleep duration and screen time exist ONLY in the WHO guideline, which is in English."""
    got = syn.expand("¿Cuánto tiene que dormir un niño de 2 años?", "es")
    assert "sleep duration" in got
    assert syn.expand("¿cuántas horas de pantalla?", "es") == ["screen time", "sedentary"]


def test_the_spanish_to_english_bridge_stays_tiny(syn: Synonyms):
    """Lock (26-ago): a full es→en table made the English sheets outrank the Spanish ones and
    dropped source@3 from 0.964 to 0.891. The bridge is only for what has NO Spanish source.
    Before adding an entry here, check the corpus and re-run `pedibot eval`."""
    bridge = syn._maps.get("es_en", {})
    assert len(bridge) <= 15, "the bridge grew: re-measure the golden set before widening it"
    for covered in ("fiebre", "tos", "vómit", "diarrea", "convuls", "quemadura", "vacun"):
        assert covered not in bridge, f"{covered} has Spanish leaflets: bridging it hurts retrieval"
