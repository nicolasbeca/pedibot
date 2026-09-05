r"""Every language needs a local way to search (5-sep-2026).

Retrieval works in two steps: a synonym table that runs offline, and — when that finds nothing —
a translation of the question by the model. `config/synonyms.yaml` had `en`, `es` and `fr`, so for
German, Russian, Arabic, Portuguese and Hindi the first step returned an empty list and the second
was the only one there was. Five of eight languages could lose their sources to a failed call or a
spent budget, while English and Spanish kept working.

The two traps that made the tables harder to write than they look, both of them the same trap in
different alphabets:

  * `\w` excludes Devanagari combining vowel signs, so the tokeniser split बुखार into ब, ख, र and
    every single-word Hindi trigger was unmatchable. Third thing that one property of `\w` broke
    in a day.
  * Arabic glues و ف ب ك ل and ال to the front of a word and turns a final ة into ت when anything
    is attached: "and his temperature" is one token, «وحرارته», which shares no prefix at all with
    «حرارة».
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.answer import SUPPORTED_LANGS
from pedibot.bot.retrieval import Synonyms

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def syn() -> Synonyms:
    return Synonyms(ROOT / "config" / "synonyms.yaml")


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_every_language_can_search_without_a_model(lang: str, syn: Synonyms) -> None:
    assert syn.knows(lang), (
        f"[{lang}] sin tabla local: su recuperación depende por completo de una llamada a la IA"
    )


#: The same question in each language. Each must reach the Spanish leaflet vocabulary offline.
FEVER = {
    "en": "my child has a fever",
    "es": "mi hijo tiene fiebre",
    "fr": "mon enfant a de la fièvre",
    "de": "mein Kind hat Fieber",
    "ru": "у ребёнка температура",
    "ar": "طفلي عنده حرارة",
    "pt": "meu filho está com febre",
    "hi": "मेरे बच्चे को बुखार है",
}


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_a_fever_question_finds_the_fever_words(lang: str, syn: Synonyms) -> None:
    assert lang in FEVER, f"[{lang}] escribe cómo se pregunta por la fiebre en ese idioma"
    got = syn.expand(FEVER[lang], lang)
    assert got, f"[{lang}] «{FEVER[lang]}» no expande a nada"
    assert any("fiebre" in t or "fever" in t or "fièvre" in t for t in got), got


def test_devanagari_survives_the_tokeniser(syn: Synonyms) -> None:
    r"""`\w` excludes the combining vowel signs, so बुखार tokenised as ब, ख, र and no Hindi
    trigger of a single word could ever match."""
    from pedibot.bot.retrieval import _TOKEN

    assert _TOKEN.findall("बुखार है") == ["बुखार", "है"]
    assert syn.expand("मेरे बच्चे को बुखार है", "hi")


def test_arabic_finds_a_word_with_its_clitics(syn: Synonyms) -> None:
    """«وحرارته» is "and his temperature": the و is glued to the front and the ة has become ت.
    It shares no prefix with «حرارة» and a parent writes it constantly."""
    plain = syn.expand("حرارة", "ar")
    assert plain
    for form in ("طفلي عمره شهران وحرارته 38.5", "الحمى عند الأطفال", "ابني عنده سعال وحرارة"):
        assert syn.expand(form, "ar"), f"«{form}» no expande a nada"


def test_the_targets_are_words_the_corpus_actually_uses(syn: Synonyms) -> None:
    """The new tables point at the Spanish and English terms the `en` table already used, so a
    German parent's "Fieber" reaches exactly what an English parent's "fever" reaches. A target
    invented here would send the search somewhere the documents never say."""
    import yaml

    raw = yaml.safe_load((ROOT / "config" / "synonyms.yaml").read_text(encoding="utf-8"))
    known = {str(t) for terms in raw["en"].values() for t in terms}
    for name in ("de_es", "ru_es", "ar_es", "pt_es", "hi_es"):
        targets = {str(t) for terms in raw[name].values() for t in terms}
        assert targets <= known, f"{name} inventa vocabulario: {sorted(targets - known)[:5]}"
