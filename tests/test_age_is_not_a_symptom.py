"""Decir la edad no puede cambiar qué documentos salen (11-sep-2026).

Lo destapó una pregunta árabe sobre malaria. Sin edad, la ficha de malaria de la OMS salía la
primera; **añadiendo «عمره ٤ سنوات» —«tiene 4 años»— desaparecía y entraba la de hepatitis B**.
Las palabras de la edad estaban entrando en la consulta FTS como si fueran un síntoma.

Medido en las ocho lenguas: **seis de ocho** ensuciaban la búsqueda al decir la edad. Sólo el
castellano y el inglés la tiraban, que es el patrón de siempre en este proyecto — se construyó en
dos idiomas y los otros seis heredaron media versión (L: las palabras vacías eran sólo
castellanas y una pregunta alemana llevaba doce términos a la consulta).

La regla que se fija es la de fondo, no la lista: **la edad se analiza aparte** —decide el triaje
del lactante, la dosis y el calendario— y en la BÚSQUEDA es ruido. Un padre que da más
información no puede recibir una respuesta peor por hacerlo.
"""

from __future__ import annotations

import pytest

from pedibot.index.store import query_terms

#: la misma pregunta, sin edad y con edad, en las ocho lenguas
PARES: dict[str, tuple[str, str]] = {
    "en": ("my child has a fever and a cough", "my 4 year old child has a fever and a cough"),
    "es": ("mi hijo tiene fiebre y tos", "mi hijo de 4 años tiene fiebre y tos"),
    "fr": (
        "mon enfant a de la fièvre et de la toux",
        "mon enfant de 4 ans a de la fièvre et de la toux",
    ),
    "de": ("mein Kind hat Fieber und Husten", "mein 4 Jahre altes Kind hat Fieber und Husten"),
    "ru": ("у моего ребёнка температура и кашель", "у моего ребёнка 4 лет температура и кашель"),
    "ar": ("ابني مصاب بالحمى والسعال", "ابني عمره ٤ سنوات مصاب بالحمى والسعال"),
    "pt": ("o meu filho tem febre e tosse", "o meu filho de 4 anos tem febre e tosse"),
    "hi": ("मेरे बच्चे को बुखार और खाँसी है", "मेरे 4 साल के बच्चे को बुखार और खाँसी है"),
}


@pytest.mark.parametrize("lang", sorted(PARES))
def test_la_edad_no_anade_terminos_de_busqueda(lang: str):
    sin, con = PARES[lang]
    a, b = query_terms(sin), query_terms(con)
    sobran = [t for t in b if t not in a]
    assert not sobran, (
        f"en {lang}, decir la edad mete {sobran} en la consulta: son palabras de edad, no "
        "síntomas, y desplazan al documento que de verdad responde"
    )


@pytest.mark.parametrize("lang", sorted(PARES))
def test_y_tampoco_quita_ninguno(lang: str):
    """La dirección contraria: una palabra vacía de más podría comerse un síntoma."""
    sin, con = PARES[lang]
    a, b = query_terms(sin), query_terms(con)
    faltan = [t for t in a if t not in b]
    assert not faltan, f"en {lang}, decir la edad hace desaparecer {faltan} de la consulta"
