"""Urgencias dichas como las diría un padre, no como las escribiría un manual (6-sep-2026).

El conjunto dorado iba al 100 % en las seis métricas con cero fallos sobre 111 casos. Un examen
que se aprueba siempre ha dejado de examinar: solo medía lo que ya sabíamos que funcionaba.

Se escribieron 31 preguntas para colarse — la misma urgencia con otras palabras — y **veinte se
colaron**. Ninguna por falta de regla: cada regla casaba solo con la redacción exacta con la que
se escribió.

    estaba:  se le marcan las costillas    se colaba:  se le marcan MUCHO las costillas
    estaba:  doesn't fade                  se colaba:  does NOT fade
    estaba:  manchas que no desaparecen    se colaba:  SARPULLIDO que no desaparece
    estaba:  blaue Lippen                  se colaba:  die Lippen SIND BLAU
    estaba:  swallowed ... battery         se colaba:  swallowed ... batteries

Y la causa más honda no era ningún patrón: la regla del lactante menor de 3 meses exige entender
la edad **y** detectar fiebre, y «está calentita» no contaba como fiebre. Un padre con un bebé de
seis semanas en brazos a las tres de la mañana no escribe «presenta fiebre».

Este fichero es ese examen, para que no se vuelva a estrechar. La otra mitad importa igual: las
preguntas de rutina tienen que seguir saliendo de rutina. Una regla ensanchada que salta con unos
mocos no protege a nadie — enseña a ignorar la alarma, que es peor que no tenerla.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

ROOT = pathlib.Path(__file__).resolve().parents[1]
ORDEN = {"routine": 0, "mental_health": 1, "urgent": 2, "emergency": 3}


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


#: (pregunta, idioma, nivel MÍNIMO aceptable). Cada una se coló alguna vez.
DEBEN_SALTAR = [
    # emergencias, dichas sin la palabra del manual
    ("tiene los labios azulados", "es", "emergency"),
    ("his lips look blue", "en", "emergency"),
    ("die Lippen sind blau", "de", "emergency"),
    ("se le marcan mucho las costillas al respirar", "es", "emergency"),
    ("I can see his ribs pulling in when he breathes", "en", "emergency"),
    ("le ha salido un sarpullido que no desaparece al apretarlo con un vaso", "es", "emergency"),
    ("he has a rash that does not fade when I press a glass on it", "en", "emergency"),
    ("se ha quedado rígido y con los ojos en blanco un momento", "es", "emergency"),
    ("está muy flojito y no responde igual que siempre", "es", "emergency"),
    ("lleva dormido desde ayer y no se despierta ni para comer", "es", "emergency"),
    # la pila de botón: quema el esófago en horas, y estaba con las monedas en «urgente»
    ("se ha tragado una pila de las redondas", "es", "emergency"),
    ("he swallowed one of those flat round batteries", "en", "emergency"),
    # fiebre en un lactante muy pequeño, sin termómetro delante
    ("mi hija de 6 semanas está calentita y no quiere comer", "es", "urgent"),
    ("my 7 week old feels hot and is feeding badly", "en", "urgent"),
    ("mi bebé de 2 meses tiene 38 de fiebre", "es", "urgent"),
    ("mein Baby ist 6 Wochen alt und hat Fieber", "de", "urgent"),
    ("mon bébé de 5 semaines a de la fièvre", "fr", "urgent"),
    # veneno: en casa nada se llama por su nombre químico
    ("mi hijo se ha bebido algo del armario de la limpieza", "es", "urgent"),
    # ideación suicida, que casi nunca se dice con esas palabras
    ("mi hija de 14 dice que no quiere seguir aquí", "es", "mental_health"),
    ("my teenager said she would be better off gone", "en", "mental_health"),
    ("mi hijo adolescente se hace cortes en los brazos", "es", "mental_health"),
]

#: La otra mitad: esto es rutina y tiene que seguir siéndolo.
NO_DEBEN_SALTAR = [
    ("mi hijo de 4 años tiene mocos", "es"),
    ("cuándo empiezo con la fruta", "es"),
    ("qué vacunas le tocan a los 12 meses", "es"),
    ("le están saliendo los dientes y babea mucho", "es"),
    ("my toddler has a runny nose", "en"),
    ("cuánto paracetamol le doy si pesa 14 kg", "es"),
    ("a qué edad empiezan a andar", "es"),
]


@pytest.mark.parametrize(("pregunta", "lang", "minimo"), DEBEN_SALTAR)
def test_an_emergency_in_a_parents_words_still_raises_the_alarm(
    triage: Triage, pregunta: str, lang: str, minimo: str
) -> None:
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, -1) >= ORDEN[minimo], (
        f"[{lang}] «{pregunta}» sale {nivel} y debería ser al menos {minimo}"
    )


@pytest.mark.parametrize(("pregunta", "lang"), NO_DEBEN_SALTAR)
def test_an_ordinary_question_does_not_raise_an_alarm(
    triage: Triage, pregunta: str, lang: str
) -> None:
    """Media hora antes de escribir esto se ensancharon seis reglas. Una alarma que salta con unos
    mocos enseña a ignorarla, y entonces no salta cuando importa."""
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, 9) < ORDEN["urgent"], f"[{lang}] falsa alarma en «{pregunta}»: {nivel}"
