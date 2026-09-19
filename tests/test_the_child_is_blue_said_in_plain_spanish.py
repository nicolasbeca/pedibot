"""«No respira bien y está morado» salía como rutina (19-sep-2026).

Lo encontré probando contra lo desplegado el día que el proyecto se presenta en MetaDAO. La
frase es la que escribiría cualquier padre en castellano y lo vivo la clasificaba como RUTINA:
contestaba con los espasmos del sollozo, que es lo que más se le parecía en el buscador.

`severe_breathing` tiene más de noventa patrones y ninguno cubría estas dos formas:

    «no respira bien»     estaba «le cuesta respirar», estaba «no puede respirar», y hasta
                          estaba en suajili («hapumui vizuri»). En castellano, no.
    «está morado»         estaban «se pone morado» y «labios morados», o sea, el cambio en
                          marcha y la parte del cuerpo. El estado, dicho del niño entero y
                          con el verbo estar, no estaba.

Es la avería de siempre aquí: la regla nace con la forma en que la escribí yo y cada lengua se
queda con una red más estrecha que la de al lado.

La otra mitad del fichero es la que impide que el remedio sea peor. Dos trampas concretas del
castellano, y las dos son cosas que un padre escribe todas las semanas:

    «no respira bien por la nariz»   es un catarro, no una urgencia;
    «tiene un morado en la rodilla»  en España un morado es un cardenal, un golpe.

Si la regla ensanchada se lleva por delante esas dos, el aviso rojo deja de significar nada.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: Lo que un padre escribe a las tres de la mañana y tiene que abrir la puerta roja.
URGENTE = [
    "mi hijo de 2 años no respira bien y está morado",
    "mi hijo de 2 anos no respira bien y esta morado",
    "mi hijo está morado",
    "mi hija está morada",
    "el niño está azul",
    "mi bebé está amoratado",
    "no respira bien desde hace un rato",
    "respira mal y está muy raro",
    "no le entra el aire",
    "mi hijo no respira bien, tiene 3 años",
]


@pytest.mark.parametrize("pregunta", URGENTE)
def test_the_plain_spanish_for_cyanosis_opens_the_red_door(triage: Triage, pregunta: str) -> None:
    r = triage.assess(pregunta)
    assert r.level == "emergency", f"«{pregunta}» sale {r.level}"


#: Y lo que escribe el resto de las semanas, que tiene que quedarse en rutina.
CORRIENTE = [
    "no respira bien por la nariz, está lleno de mocos",
    "respira mal por la nariz desde que se resfrió",
    "lleva una semana con catarro y respira mal por la nariz",
    "se dio un golpe y tiene un morado en la rodilla",
    "le ha salido un moratón en la pierna",
    "tiene la pierna morada del golpe de ayer",
    "le he comprado un pijama morado",
]


@pytest.mark.parametrize("pregunta", CORRIENTE)
def test_a_blocked_nose_and_a_bruise_are_not_an_emergency(triage: Triage, pregunta: str) -> None:
    """Una alarma que salta con un catarro manda a urgencias a quien no tiene que ir y enseña a
    ese padre a ignorar la roja, que es la que una noche va a importar."""
    r = triage.assess(pregunta)
    assert r.level == "routine", f"«{pregunta}» da la alarma ({[m.id for m in r.matched]})"
