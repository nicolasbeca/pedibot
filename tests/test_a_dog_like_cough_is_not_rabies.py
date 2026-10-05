"""Una tos «como de perro» no es la rabia (5-oct-2026).

«بنتي عندها كحة مثل نباح الكلب» —tos como el ladrido de un perro, que es como se describe el
crup— traía cuatro fichas de la rabia de la OMS: «الكلب» (el perro) era la palabra que más casaba.
Cuando la frase habla de tos, la comparación con el perro se quita antes de buscar; los sinónimos
de crup ya añaden lo que importa.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import sin_comparacion_de_perro


@pytest.mark.parametrize(
    ("frase", "fuera"),
    [
        ("بنتي عندها كحة مثل نباح الكلب", "الكلب"),
        ("my son has a cough like a dog barking", "dog"),
        ("ma fille a une toux comme un chien", "chien"),
        ("tem uma tosse de cachorro", "cachorro"),
    ],
)
def test_la_tos_pierde_el_perro(frase: str, fuera: str) -> None:
    assert fuera not in sin_comparacion_de_perro(frase)


@pytest.mark.parametrize(
    "frase",
    ["my son was bitten by a dog", "عضه الكلب", "un chien l'a mordu"],
)
def test_una_mordedura_conserva_el_perro(frase: str) -> None:
    assert sin_comparacion_de_perro(frase) == frase
