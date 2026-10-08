"""Una quemadura pequeña se cura en casa (8-oct-2026).

«My son got a small burn from hot water on his arm» sacaba el aviso de ir hoy a urgencias: la
regla `burn` saltaba con cualquier quemadura. El NHS dice otra cosa: «Burns and scalds can often
be treated at home if they're small»; A&E si es «very large or deep», si está en «face, genitals
or bottom», o si es química o eléctrica. El redactor escribía lo que dice el NHS para una
quemadura pequeña, eso contradecía el aviso, el filtro de seguridad lo tumbaba y el padre se
quedaba con «haz lo que dice el aviso» sin un solo consejo (batería difícil, v14).

La regla ahora lleva `mild_if` y `serious_if`: deja de saltar SÓLO cuando el padre dice que es
pequeña y no dice nada de lo que la hace grave. Sin la palabra «pequeña», sigue saltando: no
sabemos el tamaño y no se adivina.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage


@pytest.fixture(scope="module")
def triage(config_dir) -> Triage:
    return Triage(config_dir / "red_flags.yaml")


def _burn(t: Triage, text: str) -> bool:
    return "burn" in [r.id for r in t.assess(text).matched]


@pytest.mark.parametrize(
    "text",
    [
        "my son got a small burn from hot water on his arm",
        "she has a little burn on her finger from the oven",
        "minor burn on his leg from the iron, what should I do",
        "mi hijo se ha hecho una quemadura pequeña en el brazo con agua caliente",
        "una quemadura leve en el dedo con la sartén",
        "mon fils a une petite brûlure au bras",
        "mein Kind hat eine kleine Verbrennung am Arm",
    ],
)
def test_a_small_burn_does_not_send_the_parent_to_the_emergency_department(triage, text):
    assert not _burn(triage, text), text


@pytest.mark.parametrize(
    "text",
    [
        "my son got burned with boiling water",  # sin tamaño: no se adivina
        "small burn on his face from hot tea",  # cara
        "a small burn on her hand with blisters",  # ampollas en la mano
        "my baby has a small burn on the arm",  # bebé
        "small chemical burn from bleach",  # química
        "a small electrical burn from a socket",  # eléctrica
        "small burn but the skin is white and he feels no pain",  # profunda
        "quemadura pequeña en la cara",
        "petite brûlure au visage",
        "kleine Verbrennung im Gesicht",
    ],
)
def test_a_burn_that_can_be_serious_still_raises_the_warning(triage, text):
    assert _burn(triage, text), text
