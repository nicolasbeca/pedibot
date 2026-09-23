"""Lo que faltaba y lo que sobraba, según las 500 del 23-sep-2026.

El operador escribió esta tanda a propósito contra las costuras: la misma señal dicha de diez
maneras, negada, pasada, hipotética, y cruzada con idiomas y países. Pasadas por el triaje en
seco —que no cuesta nada— salieron cinco alarmas que NO estaban y cinco que sobraban.

Las que faltaban son las que importan:

    «tiene ronchas y ademas dice que nota rara la garganta»   ← anafilaxia que empieza
    «tiene sangre en el vomito pero ha sido solo una rayita»
    «lleva todo el dia sin hacer pis pero esta jugando»       ← 8 horas sí saltaba; «todo el día» no
    «tiene manchas moradas en las piernas desde ayer»         ← púrpura sin fiebre

Y las que sobraban tienen todas la misma forma: la frase dice que NO, o dice que ya pasó, o
habla de otra cosa («hace 42 grados FUERA»).
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT

TRIAJE = Triage(ROOT / "config" / "red_flags.yaml")

FALTABAN = [
    "tiene ronchas y ademas dice que nota rara la garganta",
    "le pica la garganta y tiene habones por todo el cuerpo",
    "tiene sangre en el vomito pero ha sido solo una rayita",
    "ha vomitado con sangre",
    "lleva todo el dia sin hacer pis pero esta jugando",
    "no ha mojado el pañal en todo el dia",
    "tiene manchas moradas en las piernas desde ayer",
    "le han salido moratones morados por las piernas sin darse golpes",
]

SOBRABAN = [
    "se ha caido y ha llorado mucho, pero no ha perdido el conocimiento",
    "hace 42 grados fuera, como enfrio la habitacion del bebe?",
    "labios un poco morados despues de llorar pero ya estan normales",
    "tiene las manos frias y moradas pero los labios estan normales",
    "dice q le cuesta respirar solo cuando corre, sentado respira bien, urgencias?",
]


@pytest.mark.parametrize("q", FALTABAN)
def test_it_has_to_ring(q: str) -> None:
    assert TRIAJE.assess(q).level in ("urgent", "emergency"), q


@pytest.mark.parametrize("q", SOBRABAN)
def test_it_must_not_ring(q: str) -> None:
    r = TRIAJE.assess(q)
    assert r.level == "routine", f"{[x.id for x in r.matched]}: {q}"


def test_forty_degrees_is_not_by_itself_an_alarm() -> None:
    """Y una que yo daba por fallo y no lo era.

    «Tiene 40 de fiebre pero está jugando» sale rutina, y está bien: el umbral de la regla es
    40,5 °C y viene de la hoja de la SEUP, que es la que se cita. Bajarlo porque 40 suena mucho
    sería cambiar la norma por una intuición mía, y la respuesta redactada sí dice cuándo
    consultar. Lo que sí cuenta es el estado del niño, y eso ya tiene sus propias reglas.
    """
    assert TRIAJE.assess("tiene 40 de fiebre pero esta jugando con los juguetes").level == "routine"
    assert TRIAJE.assess("tiene 41,5 de fiebre").level in ("urgent", "emergency")
    assert TRIAJE.assess("tiene 40 de fiebre y esta muy decaido").level in ("urgent", "emergency")


def test_the_ones_that_were_right_stay_right() -> None:
    """De las 500, la mayoría de los avisos eran correctos. Estos no se tocan."""
    for q in (
        "se ha tragado una pila de boton pero esta jugando normal",
        "tiene fiebre y manchas q no desaparecen con un vaso",
        "se le han hinchado los labios despues de comer pero dice que esta bien",
        "tiene 6 semanas y 38 de fiebre pero esta comiendo",
        "solo ha tenido una convulsion y ya esta normal, puedo esperar?",
        "la mancha es pequeña y solo hay una, pero no desaparece al apretar",
    ):
        assert TRIAJE.assess(q).level in ("urgent", "emergency"), q


SIGNO_DESCRITO = [
    "no le cuesta respirar, solo se le hunde un poco debajo de las costillas al dormir",
    "se le hunde debajo de las costillas cuando respira",
    "se le hunde la piel entre las costillas",
    "no parece ahogarse pero se le hunde el pecho",
]


@pytest.mark.parametrize("q", SIGNO_DESCRITO)
def test_the_sign_the_parent_describes_beats_the_word_they_use(q: str) -> None:
    """«No le cuesta respirar, SOLO se le hunde un poco debajo de las costillas» (23-sep-2026).

    El padre dice que no y describe un tiraje subcostal, que es exactamente el signo por el que
    se mira si un niño respira con esfuerzo. Aquí la negación no es del signo: es de la palabra
    con la que nosotros lo llamamos. «Se le hunde el pecho» ya saltaba; «debajo de las
    costillas», que es donde se ve primero, no estaba escrito.
    """
    assert TRIAJE.assess(q).level in ("urgent", "emergency"), q


DORMIDO = [
    "no tiene fiebre pero esta como dormido todo el dia",
    "esta somnoliento y no juega",
    "lleva todo el dia adormilado",
    "está más dormido de lo normal y no quiere jugar",
]


@pytest.mark.parametrize("q", DORMIDO)
def test_a_child_who_sleeps_all_day_rings(q: str) -> None:
    """«No tiene fiebre pero está como dormido todo el día» (23-sep-2026).

    «Muy decaído» saltaba; «como dormido todo el día» y «somnoliento y no juega», no. Es el
    mismo niño contado con las palabras de su madre, y la somnolencia sin fiebre es de los
    signos que las guías piden ver — precisamente porque no hay fiebre que lo explique.
    """
    assert TRIAJE.assess(q).level in ("urgent", "emergency"), q


def test_dry_lips_with_diarrhoea_ring() -> None:
    """Los labios secos con diarrea son deshidratación empezando, aunque el niño «no parezca
    enfermo»: eso es lo que hace que se espere demasiado."""
    assert TRIAJE.assess("tiene diarrea y los labios secos pero no parece enfermo").level in (
        "urgent",
        "emergency",
    )
