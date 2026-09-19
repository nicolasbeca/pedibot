"""Cómo un padre nombra su país de verdad (8-sep-2026).

«What vaccines are due at 12 months in the UK?» no llegaba a la tabla de vacunas: la lista de
nombres tenía «united kingdom» y «england», y no «UK» — que es como se escribe. Lo mismo con
«the US» frente a «USA». El inglés es el mercado primero del producto.

No entraron con los demás porque la búsqueda es por subcadena, y con dos letras eso es una
trampa: «us» vive dentro de *because*, *must* y *bukhar*, y «uk» dentro de *Ukraine*. La mitad de
abajo de este fichero es la que importa: leer un país que el padre no ha escrito le enseña el
calendario de otro sitio, que es peor que no enseñarle ninguno.
"""

from __future__ import annotations

import pytest

from pedibot.bot.vaccines import country_in_question

NOMBRADO = [
    ("GB", "What vaccines are due at 12 months in the UK?"),
    ("GB", "UK vaccine schedule for a 2 month old"),
    ("GB", "what vaccines in Britain at 8 weeks"),
    ("GB", "Impfungen in Großbritannien?"),
    ("GB", "What vaccines at 12 months in the United Kingdom?"),
    ("US", "vaccines at 12 months in the US?"),
    ("US", "What vaccines at 12 months in the USA?"),
    ("US", "what shots at 4 months in the U.S."),
    ("FR", "Quels vaccins pour un bébé de 3 mois en France ?"),
    ("ES", "¿Qué vacunas le tocan a los 3 meses en España?"),
    ("BR", "Quais vacinas aos 4 meses no Brasil?"),
]


@pytest.mark.parametrize(("code", "pregunta"), NOMBRADO)
def test_the_country_the_parent_wrote_is_read(code: str, pregunta: str) -> None:
    assert country_in_question(pregunta) == code, f"«{pregunta}»"


NO_ES_UN_PAIS = [
    "mere bacche ko bukhar hai",  # «bukhar» lleva «uk» dentro
    "please tell us what vaccines are due",  # «us», el pronombre inglés
    "just tell us the dose",
    "because he has a fever, what should I do",  # «us» dentro de «because»
    "my child is in Ukraine",  # no tenemos calendario de Ucrania
    "vacunas en América Latina",  # el continente, no Estados Unidos
    "meu filho está na América do Sul",
]


@pytest.mark.parametrize("pregunta", NO_ES_UN_PAIS)
def test_a_country_the_parent_did_not_write_is_not_invented(pregunta: str) -> None:
    """Un país inventado enseña el calendario equivocado, y un calendario de vacunas equivocado
    es peor que ninguno: se lee como si fuera el suyo."""
    assert country_in_question(pregunta) is None, f"«{pregunta}» → {country_in_question(pregunta)}"
