"""«Está sudando» no es Sudán, y «llorando» no es Orán (20-sep-2026).

Al meter el norte de África, «sudan» entró en la tabla de países que se leen por subcadena, que
es donde vive «egipto» o «marruecos». El candado de `test_a_country_name_is_not_hiding_in_another_word`
avisó en el acto: «sudan» casa dentro de **«sudando»**, y esa palabra está en una regla de
alarma de diabetes («sudoroso, sudando, con sed»). Un padre contando que su hijo suda se leía
como si hubiera dicho Sudán.

Es el mismo fallo que el «ni» suajili (L199), con una diferencia que importa: aquel salió a
producción y éste no salió de la máquina. Por eso el genérico no basta como recuerdo —dice qué
regla se rompió, no qué frase la rompía— y aquí quedan las frases de verdad, con su intención.
"""

from __future__ import annotations

import pytest

from pedibot.bot.vaccines import country_in_question

#: Frases de padre donde NO hay ningún país, por mucho que las letras coincidan.
SIN_PAIS = [
    "mi hijo está sudando mucho y tiene mucha sed desde ayer",
    "lleva toda la noche sudando y no baja la fiebre",
    "está llorando sin parar desde hace dos horas",
    "o meu filho está piorando, a dor de barriga não passa",
    "le nombril est rouge et malodorant",
]

#: Y las que sí lo dicen, que tienen que seguir funcionando.
CON_PAIS = [
    ("vivo en sudán, ¿qué vacunas le tocan a mi hijo de 2 meses?", "SD"),
    ("estoy en Sudan, cuando le toca el sarampion", "SD"),
    ("vivimos en orán, ¿cuál es el calendario?", "DZ"),
    ("estamos en Marruecos, ¿qué vacuna toca a los 9 meses?", "MA"),
    ("نحن في المغرب، ما هي اللقاحات؟", "MA"),
    ("we live in Tunisia, which vaccines are due at 18 months?", "TN"),
    ("estamos en Libia y no sé qué le toca", "LY"),
    ("vivo en Argelia con mi hija de 6 meses", "DZ"),
]


@pytest.mark.parametrize("frase", SIN_PAIS)
def test_una_palabra_corriente_no_es_un_pais(frase: str) -> None:
    assert country_in_question(frase) is None, (
        f"«{frase}» no nombra ningún país y se ha leído uno dentro de una palabra corriente"
    )


@pytest.mark.parametrize(("frase", "cc"), CON_PAIS)
def test_el_pais_dicho_de_verdad_si_se_lee(frase: str, cc: str) -> None:
    assert country_in_question(frase) == cc
