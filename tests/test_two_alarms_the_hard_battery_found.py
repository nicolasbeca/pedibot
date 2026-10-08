"""Dos alarmas que faltaban, encontradas leyendo la urgencia mal de la batería difícil (8-oct-2026).

1. «My child says he feels like he can't catch his breath» daba rutina. Es como un padre dice
   que a su hijo le cuesta respirar; «shortness of breath» ya saltaba y su forma hablada, no.
   Nivel urgente (que lo vean hoy), como «breathing fast», y no emergencia: «siente que no coge
   aire pero el monitor marca 99» no es para una ambulancia. Al correr o con ejercicio, no.
2. «My 3 year old has malaria fever or maybe teething» daba rutina: la regla de malaria pedía un
   viaje o «zona de malaria». La OMS: fiebre con sospecha de paludismo, prueba cuanto antes. Si
   la palabra va con la vacuna («fever after the malaria vaccine»), no.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage


@pytest.fixture(scope="module")
def triage(config_dir) -> Triage:
    return Triage(config_dir / "red_flags.yaml")


def _ids(t: Triage, text: str) -> set[str]:
    return {r.id for r in t.assess(text).matched}


@pytest.mark.parametrize(
    "text",
    [
        "my child says he feels like he cant catch his breath but his oxygen monitor says 99",
        "my daughter can't catch her breath",
        "my son is short of breath and coughing",
        "he gets out of breath just walking to the bathroom",
        "it's hard for him to breathe tonight",
        "a mi hija le falta el aire",
        "mon fils manque d'air",
    ],
)
def test_breathlessness_said_plainly_is_seen_today(triage, text):
    assert triage.assess(text).level in ("urgent", "emergency"), text


@pytest.mark.parametrize(
    "text",
    [
        "he gets out of breath when he runs, is that normal",
        "she is out of breath after football practice",
        "my son can't catch his breath after running around the park",
    ],
)
def test_breathless_after_exercise_is_not_an_alarm(triage, text):
    assert triage.assess(text).level == "routine", text


@pytest.mark.parametrize(
    "text",
    [
        "my 3 year old has malaria fever or maybe teething, how can I tell",
        "mi hijo tiene fiebre, creo que es paludismo",
        "mon fils a de la fièvre, est-ce le paludisme ?",
        "fever and chills, could it be malaria",
    ],
)
def test_fever_with_malaria_named_asks_for_a_test(triage, text):
    assert "malaria_area_fever" in _ids(triage, text), text


@pytest.mark.parametrize(
    "text",
    [
        "my baby had a fever after the malaria vaccine",
        "can the malaria vaccine cause fever",
        "what should I know about malaria symptoms in a child returning from Africa",
    ],
)
def test_malaria_without_a_feverish_child_is_not_an_alarm(triage, text):
    assert "malaria_area_fever" not in _ids(triage, text), text
