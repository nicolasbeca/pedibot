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
from pedibot.bot.vaccines import COUNTRY_IN_TEXT, country_in_question


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
    """"Reino Unido" must not be read as something shorter sitting inside it, and "United
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
    reaches by asking for it."""
    import pathlib

    import yaml

    root = pathlib.Path(__file__).resolve().parents[1]
    raw = yaml.safe_load((root / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    missing = set(raw["countries"]) - set(COUNTRY_IN_TEXT)
    assert not missing, f"calendarios que nadie puede pedir por su nombre: {sorted(missing)}"
