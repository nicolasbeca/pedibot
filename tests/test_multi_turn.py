"""Conversaciones de varios turnos, que es como escribe un padre de verdad (8-sep-2026).

Todos los barridos de hoy probaban UNA pregunta. Un padre escribe cinco, y reparte la
información entre ellas: primero lo que ve, después lo que ha comprobado.

El motor filtraba las reglas para no repetir el aviso cada turno —lo cual está bien: repetirlo
enseña a ignorarlo— pero el filtro miraba solo el último mensaje. Con eso se perdían justo las
reglas que existen para una COMBINACIÓN, que son las que se cuentan en dos frases:

    «se ha dado un golpe en la cabeza»  →  «ahora ha vomitado dos veces»    se perdía
    «le duele la barriga»              →  «ahora más en el lado derecho»   se perdía
    «le han salido unas manchas»       →  «no desaparecen al apretar»      se perdía

La tercera es el signo del meningococo contado exactamente como lo cuenta alguien que acaba de
hacer la prueba del vaso: describe la mancha, y en el mensaje siguiente el resultado. La regla
estaba escrita, saltaba con las dos frases juntas, y el filtro la tiraba.

La distinción correcta no es «¿está en el último mensaje?» sino «¿lo ha traído el último
mensaje?»: una regla que ya saltaba con lo anterior no vuelve a avisar, y una que salta al
juntarlo todo y antes no saltaba es información nueva.

La segunda mitad importa igual: una conversación corriente no puede acabar dando la alarma, y un
aviso ya dado no puede repetirse turno tras turno.
"""

from __future__ import annotations

import pytest

from pedibot.eval import fake_engine_from_settings


@pytest.fixture(scope="module")
def engine():
    return fake_engine_from_settings()


def conversa(eng, turnos, lang="es"):
    hist, salida = [], []
    for t in turnos:
        a = eng.ask(t, lang=lang, history=list(hist))
        salida.append((t, a.level, bool(a.banner)))
        hist.append({"role": "user", "text": t})
        hist.append({"role": "assistant", "text": a.text})
    return salida


CASOS = [
    ("golpe en la cabeza, y luego vomita", [
        "se ha dado un golpe fuerte en la cabeza",
        "ahora ha vomitado dos veces",
    ], "el vómito tras un golpe en la cabeza es urgente, y la combinación solo existe entre turnos"),
    ("bebé de 2 meses, y luego fiebre", [
        "tengo un bebé de 2 meses",
        "ahora tiene 38,5 de fiebre",
    ], "menor de 3 meses con fiebre: la edad la dijo antes"),
    ("fiebre, y luego le cuesta respirar", [
        "mi hijo de 3 años tiene fiebre desde ayer",
        "ahora le cuesta mucho respirar",
    ], "la dificultad respiratoria es del turno actual: tiene que saltar"),
    ("dolor de barriga, y luego a la derecha", [
        "le duele la barriga desde esta mañana",
        "ahora le duele más en el lado derecho",
    ], "apendicitis: la localización llega en el segundo turno"),
    ("manchas, y luego que no desaparecen", [
        "le han salido unas manchas rojas",
        "no desaparecen cuando aprieto",
    ], "petequias: la prueba del vaso llega en el segundo turno"),
    ("cae, y luego no se despierta bien", [
        "se ha caído del sofá",
        "está muy adormilado y no hay quien lo despierte",
    ], "somnolencia tras un golpe"),
]

TRANQUILOS = [
    ("catarro, y luego una duda", [
        "mi hijo tiene mocos y algo de tos",
        "¿le puedo dar algo para dormir mejor?",
    ]),
    ("fiebre que ya pasó", [
        "mi hija de 4 años tuvo fiebre ayer",
        "hoy ya está bien y juega normal",
    ]),
]

@pytest.mark.parametrize(("nombre", "turnos", "porque"), CASOS)
def test_what_the_new_message_completes_still_raises_the_alarm(
    engine, nombre: str, turnos: list[str], porque: str
) -> None:
    resultado = conversa(engine, turnos)
    nivel = resultado[-1][1]
    assert nivel != "routine", f"{nombre}: acaba en {nivel}. {porque}"


@pytest.mark.parametrize(("nombre", "turnos"), TRANQUILOS)
def test_an_ordinary_conversation_never_raises_the_alarm(
    engine, nombre: str, turnos: list[str]
) -> None:
    for t, nivel, _ in conversa(engine, turnos):
        assert nivel == "routine", f"{nombre}: «{t}» da {nivel}"


def test_an_alarm_already_given_is_not_repeated_every_turn(engine) -> None:
    """La otra mitad del filtro, y la razón por la que existe: repetir el aviso turno tras turno
    enseña a ignorarlo."""
    r = conversa(engine, [
        "se ha caído y ha perdido el conocimiento un momento",
        "ya está despierto, ¿qué tengo que vigilar en casa?",
    ])
    assert r[0][1] == "emergency", "el primer turno tiene que dar la alarma"
    assert r[1][2] is False, "el segundo turno repite el banner de algo ya dicho"
