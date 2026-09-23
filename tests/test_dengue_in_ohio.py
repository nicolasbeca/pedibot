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


def test_with_no_country_the_note_is_still_put_in() -> None:
    """Cambiado el 23-sep-2026, y a propósito. La primera versión callaba sin país, «porque
    quien no ha elegido no es probablemente europeo». Cierto, y aun así: ofrecerle dengue para
    explicarle un síntoma suelto no le ayuda viva donde viva. Donde se SABE que es endémico, la
    nota no se pone; con país desconocido, sí."""
    assert tropical_note(FUERA, None)


def test_a_trip_reopens_it() -> None:
    assert tropical_note("we just came back from Thailand and he has fever and a rash", "US") == ""
    assert tropical_note("volvimos de un viaje a Brasil y tiene fiebre y manchas", "ES") == ""


def test_the_note_is_harmless_where_it_does_not_apply() -> None:
    """En una pregunta de tos la nota sobra, y no hace daño: le dice al redactor que no saque
    enfermedades tropicales, que es lo que ya iba a hacer. Se deja simple a propósito — filtrar
    por síntomas era lo que dejó escapar el caso de la respiración rápida."""
    assert tropical_note("my son has a cough", "US")


def test_with_no_country_it_still_does_not_volunteer_them() -> None:
    """Y el caso que se escapó: «respira rápido pero no tiene fiebre», sin país (23-sep-2026).

    La primera versión pedía dos cosas que aquí no se cumplían —país conocido y la palabra
    «fiebre» en la pregunta— así que no se aplicó, y la respuesta explicó la respiración rápida
    con los signos de gravedad del DENGUE. Quien no ha elegido país no está «seguramente en
    Europa», pero tampoco hay que ofrecerle una enfermedad tropical para explicarle un síntoma
    suelto: si viene de un viaje, o la nombra él, vuelve a estar sobre la mesa.
    """
    assert tropical_note("respira rapido pero no tiene fiebre y esta tranquilo", None)


def test_if_the_parent_names_it_we_talk_about_it() -> None:
    assert tropical_note("¿mi hijo puede tener dengue?", "ES") == ""
    assert tropical_note("me preocupa la malaria, volvimos hace poco", None) == ""


def test_where_it_is_endemic_it_stays_silent() -> None:
    assert tropical_note("fiebre y sarpullido", "BR") == ""
