"""A country written in the question counts (5-sep-2026).

"Quels vaccins pour un bébé de 3 mois en France ?" — with the country selector set to FR the
vaccination tool answers with the real French calendar, dose by dose. With it unset the same
question fell through to the corpus, failed verification twice and came back as "je n'ai pas
d'information fiable à ce sujet". The country was in the sentence the whole time; the engine only
ever read the dropdown.

The line this must not cross is inferring a country from a LANGUAGE. A French speaker may be in
Belgium, Canada or Switzerland, and handing a Belgian family the French calendar would be worse
than the fallback, because it would look right.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import SUPPORTED_LANGS
from pedibot.bot.vaccines import COUNTRY_IN_TEXT, COUNTRY_SHORT, country_in_question


@pytest.mark.parametrize(
    "question,expected",
    [
        ("Quels vaccins pour un bébé de 3 mois en France ?", "FR"),
        ("¿Qué vacunas le tocan a los 2 meses en España?", "ES"),
        ("what vaccines does my baby need in the United Kingdom", "GB"),
        ("Welche Impfungen in Deutschland mit 2 Monaten?", "DE"),
        ("quais vacinas no Brasil aos 2 meses", "BR"),
        ("какие прививки в США в 2 месяца", "US"),
        ("que vacinas em Portugal", "PT"),
    ],
)
def test_the_country_the_parent_wrote(question: str, expected: str) -> None:
    assert country_in_question(question) == expected


def test_a_longer_name_wins() -> None:
    """ "Reino Unido" must not be read as something shorter sitting inside it, and "United
    States" must not lose to "usa" appearing in another word."""
    assert country_in_question("vacunas en el Reino Unido") == "GB"
    assert country_in_question("vaccines in the United States") == "US"


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_a_language_is_never_a_country(lang: str) -> None:
    """The one thing this must not do. A question with no country named returns None, whatever
    language it is in — the fallback is honest and a wrong calendar is not."""
    plain = {
        "en": "what vaccines does my baby need at 2 months",
        "es": "qué vacunas le tocan a mi bebé a los 2 meses",
        "fr": "quels vaccins pour mon bébé de 2 mois",
        "de": "welche Impfungen braucht mein Baby mit 2 Monaten",
        "ru": "какие прививки нужны ребёнку в 2 месяца",
        "ar": "ما التطعيمات التي يحتاجها طفلي في الشهر الثاني",
        "pt": "quais vacinas meu bebê precisa aos 2 meses",
        "hi": "मेरे 2 महीने के बच्चे को कौन से टीके चाहिए",
    }
    assert lang in plain, f"[{lang}] escribe la pregunta sin país en ese idioma"
    assert country_in_question(plain[lang]) is None, (
        f"[{lang}] deduce un país de la lengua, que es justo lo que no puede hacer"
    )


def test_every_country_with_a_schedule_can_be_named() -> None:
    """A country whose calendar we publish but whose name we cannot read is a page nobody
    reaches by asking for it.

    Two tables, one question. Most names are safe to look for anywhere in the sentence; a few
    are not, because they live inside another word — Mali inside *malignant*, Niger inside
    *Nigeria*, Guinea in front of *pig* — and those are matched with a word boundary in
    COUNTRY_SHORT. Either table counts: what must not happen is a country in neither.
    """
    import pathlib

    import yaml

    root = pathlib.Path(__file__).resolve().parents[1]
    raw = yaml.safe_load((root / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    missing = set(raw["countries"]) - set(COUNTRY_IN_TEXT) - set(COUNTRY_SHORT)
    assert not missing, f"calendarios que nadie puede pedir por su nombre: {sorted(missing)}"


def test_every_country_with_a_schedule_answers_to_its_own_name() -> None:
    """Being in the table is not the same as being found. This asks for each country by each of
    its own names and checks that the answer is that country and not a longer one that contains
    it: Guinea is not Equatorial Guinea, Niger is not Nigeria, and Congo is not the DRC."""
    import pathlib

    import yaml

    root = pathlib.Path(__file__).resolve().parents[1]
    raw = yaml.safe_load((root / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    mal = []
    for code in raw["countries"]:
        for name in COUNTRY_IN_TEXT.get(code, ()):
            leido = country_in_question(f"vacunas en {name}")
            if leido != code:
                mal.append(f"«{name}» ({code}) se lee como {leido}")
    assert not mal, mal


#: The same question in each language. Every one must reach the vaccination table.
VACCINE_QUESTION = {
    "en": "what vaccines does my baby need at 2 months",
    "es": "qué vacunas le tocan a mi bebé a los 2 meses",
    "fr": "quels vaccins pour mon bébé de 2 mois",
    "de": "welche Impfungen braucht mein Baby mit 2 Monaten",
    "ru": "какие прививки нужны ребёнку в 2 месяца",
    "ar": "ما التطعيمات التي يحتاجها طفلي في الشهر الثاني",
    "pt": "quais vacinas meu bebê precisa aos 2 meses",
    "hi": "मेरे बच्चे को कौन से टीके लगने हैं",
}


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_every_language_reaches_the_vaccination_table(lang: str) -> None:
    """The gate to the calendars, which are the most visited pages on the site. It knew Spanish,
    English and French — so German, Russian, Arabic, Hindi and Portuguese ("vacina", without the
    u) fell through to the corpus and never saw a calendar at all. Five of eight languages.
    """
    from pedibot.bot.vaccines import is_vaccine_question

    assert lang in VACCINE_QUESTION, f"[{lang}] escribe la pregunta de vacunas en ese idioma"
    assert is_vaccine_question(VACCINE_QUESTION[lang]), (
        f"[{lang}] «{VACCINE_QUESTION[lang]}» no llega a la tabla de vacunas"
    )


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_a_fever_question_is_not_a_vaccine_question(lang: str) -> None:
    """The other half: a gate that opens for everything is not a gate."""
    from pedibot.bot.vaccines import is_vaccine_question

    fever = {
        "en": "my child has a fever",
        "es": "mi hijo tiene fiebre",
        "fr": "mon enfant a de la fièvre",
        "de": "mein Kind hat Fieber",
        "ru": "у ребёнка температура",
        "ar": "طفلي عنده حرارة",
        "pt": "meu filho está com febre",
        "hi": "मेरे बच्चे को बुखार है",
    }
    assert not is_vaccine_question(fever[lang]), f"[{lang}] confunde fiebre con vacunas"
