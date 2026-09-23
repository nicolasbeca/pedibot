"""Un niño de 8 años en Estados Unidos, con vómitos, fiebre y un sarpullido — y dengue.

Del registro del 22-sep-2026, una consulta real:

    «My 8 year old has vomiting, fever and a red rash»

La respuesta empezaba bien —las manchas que no se borran al presionar son motivo de consulta
urgente, según la SEUP— y después dedicaba un párrafo al **dengue**, con sus signos de alarma.
El corpus tiene la hoja de la OMS, encaja con las tres palabras, y el modelo la usó. Para un
padre en Ohio, que no ha salido del país, eso no es información: es un susto y una pista falsa.

Al revés también importa, y por eso esto no borra nada: en Brasil, o si el padre cuenta que
vienen de un viaje, el dengue es exactamente lo que hay que nombrar.
"""

from __future__ import annotations

from pedibot.bot.who_first import tropical_note

FUERA = "My 8 year old has vomiting, fever and a red rash"


def test_in_a_country_without_dengue_the_writer_is_told() -> None:
    nota = tropical_note(FUERA, "US")
    assert nota and "dengue" in nota.lower()


def test_where_it_is_endemic_nothing_is_said() -> None:
    assert tropical_note(FUERA, "BR") == ""
    assert tropical_note(FUERA, "IN") == ""


def test_with_no_country_nothing_is_assumed() -> None:
    assert tropical_note(FUERA, None) == ""


def test_a_trip_reopens_it() -> None:
    assert tropical_note("we just came back from Thailand and he has fever and a rash", "US") == ""
    assert tropical_note("volvimos de un viaje a Brasil y tiene fiebre y manchas", "ES") == ""


def test_a_question_that_has_nothing_to_do_with_it_is_left_alone() -> None:
    assert tropical_note("my son has a cough", "US") == ""
