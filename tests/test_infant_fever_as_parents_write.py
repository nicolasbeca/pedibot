"""El bebé con fiebre, dicho como lo escribe un padre con prisa (29-sep-2026).

La regla 5 de CLAUDE.md —menor de tres meses con fiebre, urgencias— salía como *rutina* en el
sitio vivo con dos frases de la octava tanda del operador:

- «mi bebé tiene 20 días y tiene fiebre, ¿qué hago?»: la edad en días sólo se leía con «de vida»,
  «de edad» u «old» detrás, para que «3 días de fiebre» no hiciera recién nacido a cualquiera.
  El cuidado era bueno; dejaba fuera la forma más corriente de decir la edad de un recién nacido.
- «39.2 + bebe de 2 meses + esta dormido»: la cifra contaba como fiebre con un verbo delante o
  una unidad detrás, y a las tres de la mañana no se escribe ninguna de las dos.

Cada arreglo lleva su mitad contraria, porque las dos precauciones que había eran correctas.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage, parse_age_months
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


@pytest.mark.parametrize(
    "texto",
    [
        "mi bebé tiene 20 días y tiene fiebre, ¿qué hago?",
        "39.2 + bebe de 2 meses + esta dormido, ¿lo despierto?",
        "bebé de 15 días con 38,3",
        "my baby is 20 days and has a fever",
        "mon bébé a 20 jours et de la fièvre",
        "meu bebê tem 20 dias e está com febre",
        "mein Baby ist 20 Tage alt und hat Fieber",
        "38.4 en mi bebe de 6 semanas",
    ],
)
def test_el_bebe_con_fiebre_salta(triage, texto):
    assert triage.assess(texto).level in ("urgent", "emergency"), texto


@pytest.mark.parametrize(
    "texto",
    [
        "mi hijo tiene 3 días de fiebre",
        "mi hija lleva 10 días con tos",
        "my son has had a fever for 5 days",
        "mi bebé tiene 20 días de fiebre",
    ],
)
def test_dias_de_sintoma_no_son_una_edad(texto):
    assert parse_age_months(texto) is None, texto


@pytest.mark.parametrize(
    "texto,meses",
    [
        ("mi bebé tiene 20 días", 20 / 30.4),
        ("my baby is 12 days", 12 / 30.4),
        ("mon bébé a 20 jours", 20 / 30.4),
        ("meu bebê tem 20 dias", 20 / 30.4),
        ("mein Baby ist 20 Tage alt", 20 / 30.4),
    ],
)
def test_la_edad_en_dias_se_lee(texto, meses):
    assert parse_age_months(texto) == pytest.approx(meses, rel=0.01), texto


@pytest.mark.parametrize(
    "texto",
    [
        "pesa 38,5 kg y tiene tos",
        "nació de 38,5 semanas",
        "mide 39.5 cm de brazo",
    ],
)
def test_una_cifra_que_no_es_temperatura_no_es_fiebre(triage, texto):
    assert not triage.has_fever(texto), texto


def test_la_cifra_sola_con_decimales_es_fiebre(triage):
    assert triage.has_fever("39.2 + bebe de 2 meses")
    assert triage.has_fever("40,1 sin mas datos")
