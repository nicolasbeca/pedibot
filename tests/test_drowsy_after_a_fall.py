"""Somnoliento después de una caída salía rutina (21-sep-2026).

El operador escribió «Mi hijo se ha caído de una silla y ahora está somnoliento. ¿Qué hago?» y
el chat contestó sin cartel. La respuesta redactada decía bien lo que dice la SEUP, pero la
somnolencia tras un golpe no es algo que se vigila 24 horas: es el signo por el que MedlinePlus
manda llamar a emergencias («very sleepy or hard to wake»). La regla del golpe sólo conocía los
vómitos y la pérdida de conocimiento.

Y lo que no puede saltar: tener sueño sin golpe, o un golpe de hace semanas con el niño que
duerme mal, que es otra cosa.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


SI = [
    "Mi hijo se ha caido de una silla y ahora esta somnoliento. Que hago?",
    "se dio un golpe en la cabeza y está muy adormilado",
    "mi hija está somnolienta desde que se cayó del columpio",
    "se cayó de la cama y no hay quien lo despierte",
    "my son fell off the sofa and now he is very drowsy",
    "she hit her head and now she's hard to wake",
    "il est tombé du lit et maintenant il est très somnolent",
    "caiu da cadeira e agora está sonolento",
    "er ist vom Stuhl gefallen und jetzt sehr schläfrig",
    "упал с дивана и теперь очень сонливый",
    "ابني وقع من الكرسي والآن هو نعسان جدا",
    "बच्चा बिस्तर से गिर गया और अब सुस्त है",
    "mtoto ameanguka kutoka kitandani na sasa anasinzia sana",
]

NO = [
    "mi hijo tiene mucho sueño por las tardes",
    "se cayó hace un mes y desde entonces duerme mal",
    "my baby is sleepy after feeding",
    "está somnoliento con el antihistamínico",
]


@pytest.mark.parametrize("texto", SI)
def test_drowsy_after_a_fall_calls_for_help_now(triaje: Triage, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "emergency", texto
    assert "drowsy_after_head_injury" in {m.id for m in r.matched}


@pytest.mark.parametrize("texto", NO)
def test_sleepy_without_a_fall_is_not_this(triaje: Triage, texto: str) -> None:
    ids = {m.id for m in triaje.assess(texto).matched}
    assert "drowsy_after_head_injury" not in ids
