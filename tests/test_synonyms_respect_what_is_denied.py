"""Los sinónimos no amplían lo que el padre niega (9-oct-2026).

Pendiente del 5-oct: «fever since yesterday but no rash» ampliaba también «rash» → exantema,
manchas, urticaria, y la búsqueda se iba a la erupción que el padre acababa de descartar. Por eso
no se pudo repetir «fever»/«rash» en la tabla inglesa: rompía «no fever». La negación ya se
miraba al ordenar los pasajes (`_NEGADA`); faltaba en la ampliación.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Synonyms
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def sin() -> Synonyms:
    return Synonyms(ROOT / "config" / "synonyms.yaml", ROOT / "config" / "drugs.yaml")


@pytest.mark.parametrize(
    ("texto", "lang", "no_debe"),
    [
        ("breathing very fast but no fever", "en", "fiebre"),
        ("fever since yesterday but no rash", "en", "exantema"),
        ("he has a cough, not a fever", "en", "fiebre"),
        ("tos sin fiebre desde ayer", "es", "fever"),
    ],
)
def test_what_is_denied_is_not_expanded(sin: Synonyms, texto: str, lang: str, no_debe: str) -> None:
    assert no_debe not in sin.expand(texto, lang), sin.expand(texto, lang)


@pytest.mark.parametrize(
    ("texto", "lang", "debe"),
    [
        ("my son has a fever and a rash", "en", "fiebre"),
        ("my son has a fever and a rash", "en", "exantema"),
        ("no appetite and a high fever", "en", "fiebre"),
    ],
)
def test_what_is_said_still_is(sin: Synonyms, texto: str, lang: str, debe: str) -> None:
    assert debe in sin.expand(texto, lang), sin.expand(texto, lang)


@pytest.mark.parametrize(
    ("texto", "lang", "debe"),
    [
        ("my baby is not gaining weight", "en", "centile lines"),
        ("mi hija no gana peso", "es", None),
    ],
)
def test_a_trigger_that_carries_the_negation_still_fires(
    sin: Synonyms, texto: str, lang: str, debe: str | None
) -> None:
    ampl = sin.expand(texto, lang)
    assert ampl, texto
    if debe:
        assert debe in ampl, ampl
