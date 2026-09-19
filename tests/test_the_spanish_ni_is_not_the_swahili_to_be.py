"""«Ni» es una negación en castellano y es el verbo SER en suajili (19-sep-2026).

Preguntando a lo desplegado el día de MetaDAO, en suajili:

    «mtoto wangu wa miezi 6 midomo yake ni ya bluu na hajibu»
    (mi bebé de 6 meses tiene los labios azules y no responde)
    → rutina, sin aviso

La cianosis saltaba. Lo que no saltaba era el «no responde», y no por falta de patrón: lo
apagaba el guardián de negaciones. `NEGADORES` lleva `\\bni\\b` porque en castellano el «ni»
continúa una negación —«no tiene fiebre, tos NI dificultad para respirar»—, y resulta que en
suajili **«ni» es el verbo ser**: «midomo yake NI ya bluu» es «sus labios SON azules».

O sea: en suajili, cualquier señal que venga detrás de un «es» se quedaba muda. Es la familia de
averías de siempre en este proyecto —una palabra corta de una lengua viviendo dentro de otra,
como «catar» dentro de «catarro»— pero del lado peor, porque aquí no produce una alarma de más,
produce un **silencio**.

El arreglo no es quitar el «ni» castellano, que hace falta. Es pedirle lo que el castellano
cumple siempre y el suajili no: **el «ni» continúa una negación, así que tiene que haber otra
negación antes en la misma frase**. «No tiene fiebre ni le cuesta respirar» la tiene. «Midomo
yake ni ya bluu» no la tiene.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: El suajili, donde «ni» es «es» y no puede callar nada.
SUAJILI_QUE_TIENE_QUE_SALTAR = [
    "mtoto wangu wa miezi 6 midomo yake ni ya bluu na hajibu",
    "midomo yake ni ya bluu na hapumui vizuri",
    "hali yake ni mbaya na ana degedege",
    # escrita a la primera con «amezimia» —se ha desmayado— y la quité: el desmayo simple NO
    # es una urgencia en la fuente («no se producen por problemas médicos importantes», SEUP),
    # así que no hay regla que disparar y la prueba estaba inventándose una. Aquí va una señal
    # que sí existe.
    "joto lake ni kali na damu inatoka puani haikomi",
]


@pytest.mark.parametrize("texto", SUAJILI_QUE_TIENE_QUE_SALTAR)
def test_the_swahili_copula_silences_nothing(triaje: Triage, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "emergency", f"«{texto}» → {r.level}: el «ni» de ser está haciendo de no"


#: Y el castellano, que es por lo que el «ni» está en la lista: si se rompe esto, la alarma
#: salta cuando el padre está diciendo justo lo contrario.
CASTELLANO_QUE_NO_PUEDE_SALTAR = [
    "no tiene fiebre ni le cuesta respirar",
    "no tiene fiebre, no vomita ni le cuesta respirar",
    "no le veo manchas ni los labios morados",
    "no ha vomitado ni tiene diarrea",
]


@pytest.mark.parametrize("texto", CASTELLANO_QUE_NO_PUEDE_SALTAR)
def test_the_spanish_ni_still_negates(triaje: Triage, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", f"«{texto}» → {r.level} por {[m.id for m in r.matched]}"
