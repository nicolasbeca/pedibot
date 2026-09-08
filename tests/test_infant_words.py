"""La palabra con la que un padre dice «es muy pequeño» (8-sep-2026).

La regla del lactante con fiebre —la 5 de CLAUDE.md, la más importante que hay— tiene dos
caminos hacia la alarma y hasta hoy solo funcionaba uno:

  · `requires: [age_under_3_months, fever]`, que exige LEER una edad y detectar fiebre;
  · sus 28 patrones, escritos a mano en las ocho lenguas… y **nunca evaluados**, porque
    `assess()` hacía `continue` en cuanto una regla tenía `requires`.

El candado estructural que ya existía (`test_every_rule_can_fire_in_every_script`) los contaba
tan contento: comprobaba que estuvieran escritos, no que sirvieran. Un examen que no examina.

Lo que se colaba era exactamente lo que el `requires` no sabe leer: la palabra. «Mi lactante
tiene fiebre» no lleva ninguna cifra de edad, y cinco de las ocho lenguas se quedaban en rutina.

La otra mitad importa igual y por eso está aquí abajo: la palabra no puede ganarle a una edad
dicha. Si el padre escribe que el niño tiene ocho meses, esta regla no es la suya.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage, parse_age_months

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: La misma urgencia dicha con la palabra, sin ninguna cifra de edad. Cada una tiene su patrón
#: escrito en `red_flags.yaml` desde el primer día; ninguna saltaba.
CON_PALABRA = [
    ("es", "mi lactante tiene fiebre"),
    ("es", "el bebé de mi hermana, un lactante, tiene temperatura"),
    ("de", "Mein Säugling hat Fieber"),
    ("de", "Das Neugeborene hat Fieber"),
    ("ru", "у младенца температура 38"),
    ("ru", "у грудничка температура"),
    ("ar", "رضيعي عنده حرارة"),
    ("ar", "رضيع عنده حمى"),
    ("pt", "bebê de 10 dias com febre"),
    ("hi", "नवजात को बुखार"),
]


@pytest.mark.parametrize(("lang", "pregunta"), CON_PALABRA)
def test_the_word_for_a_very_young_baby_raises_the_alarm(
    triage: Triage, lang: str, pregunta: str
) -> None:
    r = triage.assess(pregunta)
    assert r.level == "urgent", f"[{lang}] «{pregunta}» se queda en {r.level}"
    assert any(x.id == "infant_fever_under_3_months" for x in r.matched)


#: Una edad dicha gana a la palabra. Si esto salta, la alarma deja de significar nada.
CON_EDAD_MAYOR = [
    ("ru", "у ребёнка 5 месяцев температура 38"),
    ("ar", "ابني عمره 8 أشهر وعنده حرارة"),
    ("es", "mi bebé de 8 meses tiene fiebre"),
    ("es", "mi hijo de 4 años tiene fiebre"),
    ("pt", "meu bebê de 6 meses com febre"),
    ("de", "mein Kind ist 2 Jahre alt und hat Fieber"),
]


@pytest.mark.parametrize(("lang", "pregunta"), CON_EDAD_MAYOR)
def test_an_age_the_parent_wrote_beats_the_word(triage: Triage, lang: str, pregunta: str) -> None:
    r = triage.assess(pregunta)
    assert not any(x.id == "infant_fever_under_3_months" for x in r.matched), (
        f"[{lang}] «{pregunta}» ({r.age_months} meses) recibe el aviso del lactante"
    )


def test_ten_days_of_fever_is_not_a_ten_day_old_baby() -> None:
    """«10 दिन का बुखार» son diez días DE fiebre; «10 दिन का बच्चा» es un bebé de diez días.

    La misma construcción para las dos cosas. Sin el sustantivo detrás, un niño de cualquier
    edad con una fiebre larga recibía el aviso del lactante, con ese motivo en el banner.
    """
    assert parse_age_months("बच्चे को 10 दिन का बुखार है") is None
    assert parse_age_months("10 दिन का बच्चा") is not None
    assert parse_age_months("10 दिन का बच्चा") < 1


def test_the_patterns_of_a_rule_with_requires_are_actually_evaluated() -> None:
    """El candado de fondo, para que no vuelvan a quedarse de adorno.

    No mira una frase: mira el código. Toda regla que traiga patrones tiene que poder saltar
    por ellos, tenga o no `requires`. La forma de comprobarlo sin depender del idioma es
    quitarle el `requires` a mano y ver que la evaluación no cambia de camino.
    """
    triage = Triage(RAIZ / "config" / "red_flags.yaml")
    con_ambos = [r for r in triage.rules if r.requires and r.patterns]
    assert con_ambos, "si esto se queda vacío, este candado ya no vigila nada"
    for r in con_ambos:
        assert any(triage._hits(rx, "mi lactante tiene fiebre") for rx in r.patterns) or any(
            triage._hits(rx, "у младенца температура 38") for rx in r.patterns
        ), f"{r.id}: sus patrones no casan ni con las frases que los motivaron"
