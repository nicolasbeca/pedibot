"""«Menos de 3 meses» no es «3 meses» (9-sep-2026).

La regla del lactante se dispara con `age < 3`. El lector de edades veía «menor de 3 meses»,
sacaba el número —3— y la comparación fallaba por un pelo.

O sea que **la frase con la que la propia regla está escrita no la disparaba**. Y no es una
redacción rara: es literalmente cómo la enuncia la lista de urgencias del SEUP («Bebé menor de
3 meses con fiebre») y cómo la dice un padre que no quiere dar la edad exacta.

Salió de cruzar esa lista con el triaje: dos copias de la misma idea —cuándo hay que ir—
escritas por separado, y nadie las había puesto una al lado de la otra.

El cualificador va delante en siete lenguas y **detrás en hindi** («3 महीने से कम»), así que se
mira a los dos lados. Se resta medio escalón: no se busca una edad exacta, se busca que la
comparación con los cortes de 1 y 3 meses caiga del lado correcto.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import parse_age_months

MENOS_DE_TRES = [
    ("es", "mi bebé es menor de 3 meses y tiene fiebre"),
    ("es", "tengo un bebé de menos de 3 meses con fiebre"),
    ("en", "my baby is under 3 months old and has a fever"),
    ("fr", "mon bébé a moins de 3 mois et de la fièvre"),
    ("de", "mein Baby ist unter 3 Monaten alt und hat Fieber"),
    ("ru", "ребёнку меньше 3 месяцев, температура"),
    ("ar", "طفلي أقل من 3 أشهر وعنده حمى"),
    ("pt", "meu bebê tem menos de 3 meses e está com febre"),
    ("hi", "मेरा बच्चा 3 महीने से कम का है और उसे बुखार है"),
]

EDAD_A_SECAS = [
    ("es", "mi hijo de 3 meses tiene fiebre", 3.0),
    ("es", "mi bebé de 2 meses tiene fiebre", 2.0),
    ("es", "mi hijo de 4 años tiene fiebre", 48.0),
    ("es", "tiene más de 3 meses y fiebre", 3.0),
    ("hi", "मेरे 3 महीने के बच्चे को बुखार है", 3.0),
]


@pytest.mark.parametrize(("lang", "pregunta"), MENOS_DE_TRES)
def test_under_three_months_reads_as_under_three(lang: str, pregunta: str) -> None:
    edad = parse_age_months(pregunta)
    assert edad is not None and edad < 3, f"[{lang}] «{pregunta}» → {edad}"


@pytest.mark.parametrize(("lang", "pregunta"), MENOS_DE_TRES)
def test_and_therefore_the_infant_rule_fires(lang: str, pregunta: str) -> None:
    import pathlib

    from pedibot.bot.triage import Triage

    raiz = pathlib.Path(__file__).resolve().parents[1]
    t = Triage(raiz / "config" / "red_flags.yaml")
    assert t.assess(pregunta).level == "urgent", f"[{lang}] «{pregunta}»"


@pytest.mark.parametrize(("lang", "pregunta", "esperada"), EDAD_A_SECAS)
def test_an_age_said_plainly_is_not_moved(lang: str, pregunta: str, esperada: float) -> None:
    """La otra mitad: sin cualificador, la edad es la que el padre dijo. Y «más de 3 meses»
    tampoco se toca — el cualificador que importa es el que empequeñece."""
    assert parse_age_months(pregunta) == esperada, f"[{lang}] «{pregunta}»"


def test_under_one_month_refusing_feeds_is_urgent() -> None:
    """Un escalón por debajo, y la misma historia: la lista lo pone en «acudir hoy»."""
    import pathlib

    from pedibot.bot.triage import Triage

    raiz = pathlib.Path(__file__).resolve().parents[1]
    t = Triage(raiz / "config" / "red_flags.yaml")
    assert t.assess("bebé de menos de un mes que rechaza las tomas").level == "urgent"
