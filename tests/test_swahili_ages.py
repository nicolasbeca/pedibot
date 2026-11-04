"""La edad en suajili: la unidad va delante del número (26-oct-2026).

Comprobado en vivo antes de escribir a mothers2mothers: «Mtoto wangu wa wiki 6 ana homa ya 38.2»
(mi bebé de 6 semanas tiene 38,2) salía como RUTINA, sin aviso, y con «a un niño mayor puedes
cuidarlo en casa». El triaje veía la fiebre pero no la edad: el lector buscaba «6 weeks», «6
semanas», «6 हफ्ते», siempre el número delante, y en suajili se dice «wiki 6», «miezi miwili».
La fiebre en un lactante de menos de tres meses es la regla que más importa, y en suajili se
apagaba entera salvo con las dos frases fijas de red_flags.yaml («mtoto wa miezi miwili ana homa»).

La edad se distingue de la duración por lo que va delante: «mtoto WA wiki 6», «ANA miezi 2»,
«UMRI WA miaka 3» son la edad; «homa KWA wiki 2», «homa YA siku 3» y «wiki 2 ZILIZOPITA» no.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage, parse_age_months
from pedibot.settings import get_settings

EDADES = [
    ("Mtoto wangu wa wiki 6 ana homa ya 38.2", 6 / 4.345),
    ("mtoto wa miezi 2 ana homa 38.5", 2),
    ("mtoto wangu ana miezi 2 na ana homa", 2),
    ("Mtoto wangu ana wiki tatu, ana homa", 3 / 4.345),
    ("mtoto wangu wa miezi miwili ana homa kali", 2),
    ("mtoto wa mwezi mmoja anatapika", 1),
    ("mtoto wa siku 10 ana homa", 10 / 30.4),
    ("mtoto wangu mwenye umri wa miaka 3 ana kikohozi", 36),
    ("mwanangu wa mwaka mmoja ana kuhara", 12),
    ("binti yangu wa miaka miwili ana homa", 24),
]

DURACIONES = [
    "mtoto ana homa kwa wiki 2",
    "ana homa ya siku 3",
    "alianza kukohoa wiki 2 zilizopita",
    "amekuwa na kuhara kwa miezi miwili",
]


@pytest.mark.parametrize(("texto", "meses"), EDADES)
def test_the_age_is_read(texto: str, meses: float) -> None:
    edad = parse_age_months(texto)
    assert edad is not None, texto
    assert edad == pytest.approx(meses, abs=0.05), texto


@pytest.mark.parametrize("texto", DURACIONES)
def test_how_long_is_not_how_old(texto: str) -> None:
    assert parse_age_months(texto) is None, texto


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(get_settings().config_dir / "red_flags.yaml")


@pytest.mark.parametrize(
    "texto",
    ["Mtoto wangu wa wiki 6 ana homa ya 38.2", "mtoto wa miezi 2 ana homa 38.5"],
)
def test_the_infant_with_fever_gets_the_warning(triaje: Triage, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "urgent", (r.level, [m.id for m in r.matched])
    assert "infant_fever_under_3_months" in [m.id for m in r.matched]


def test_an_older_child_with_fever_does_not(triaje: Triage) -> None:
    assert triaje.assess("mtoto wangu wa miaka 3 ana homa ya 38.2").level == "routine"


# 4-nov-2026: probado en vivo antes de escribir a la Doris Mollel Foundation (prematuros, Tanzania).
# «mtoto wangu njiti wa wiki mbili hanyonyi vizuri na ana homa» (mi prematuro de dos semanas no mama
# bien y tiene fiebre) salía como RUTINA. La edad se leía; la fiebre no: «homa» sin cifra no estaba
# en la lista de fiebre de red_flags.yaml, y de esa lista depende la regla del lactante. Y la del
# menor de un mes que no mama sólo tenía dos frases fijas en suajili.
@pytest.mark.parametrize(
    "texto",
    [
        "mtoto wangu njiti wa wiki mbili hanyonyi vizuri na ana homa",
        "mtoto wangu wa wiki 2 ana homa",
        "mtoto wa miezi 2 ana homa",
        "mtoto wangu ana wiki sita na ana homa kali",
    ],
)
def test_the_infant_with_fever_in_words_gets_the_warning(triaje: Triage, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "urgent", (r.level, [m.id for m in r.matched])
    assert "infant_fever_under_3_months" in [m.id for m in r.matched]


@pytest.mark.parametrize(
    "texto",
    [
        "mtoto wangu wa wiki mbili hanyonyi vizuri",
        "mtoto wa siku 10 anakataa kunyonya",
        "mtoto wangu wa wiki 3 hataki kunyonya tangu jana",
    ],
)
def test_the_newborn_who_will_not_feed_gets_the_warning(triaje: Triage, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "urgent", (r.level, [m.id for m in r.matched])
    assert "newborn_refusing_feeds" in [m.id for m in r.matched]


def test_no_fever_and_older_babies_stay_routine(triaje: Triage) -> None:
    assert "infant_fever_under_3_months" not in [
        m.id for m in triaje.assess("mtoto wangu wa wiki 2 hana homa, anapiga chafya").matched
    ]
    assert "newborn_refusing_feeds" not in [
        m.id for m in triaje.assess("mtoto wangu wa miezi 8 hanyonyi vizuri usiku").matched
    ]
