"""La coletilla de la edad se escribe en el alfabeto del padre (24-sep-2026).

L231: quien escribe «bukhar hai lekin bacha khel raha hai» teclea urdu con el alfabeto latino, y
puede no leer nastaliq. El redactor ya lo sabe desde entonces y escribe la respuesta en el
alfabeto en el que le escribieron.

Lo que no lo sabía es la coletilla del final —«¿qué edad tiene? con la edad afino la
respuesta»—, que en las lenguas que el sitio no habla no está escrita a mano sino traducida por
el modelo. Se le pedía «tradúcelo al urdu» y devolvía nastaliq, así que la respuesta salía en
urdu latino y remataba con una línea que ese padre no puede leer.

Es el mismo fallo de L231 en el trozo que se me quedó fuera: arreglé el texto y no el remate.
"""

from __future__ import annotations

from pedibot.bot.answer import TRADUCE, instruccion_de_alfabeto


def test_a_parent_writing_in_latin_gets_the_coda_in_latin() -> None:
    sistema = instruccion_de_alfabeto(TRADUCE, "Urdu", latino=True)
    assert "Latin" in sistema, sistema
    assert TRADUCE in sistema, "la instrucción de siempre no se pierde"


def test_a_parent_writing_in_their_own_script_is_left_alone() -> None:
    sistema = instruccion_de_alfabeto(TRADUCE, "Urdu", latino=False)
    assert sistema == TRADUCE, "si escribió en su alfabeto, no se le cambia nada"


def test_languages_already_written_in_latin_need_no_instruction() -> None:
    """A un italiano no hay que decirle que escriba en latino: ya lo hace."""
    for idioma in ("Italian", "Polish", "Swahili", "Turkish"):
        assert instruccion_de_alfabeto(TRADUCE, idioma, latino=True) == TRADUCE, idioma
