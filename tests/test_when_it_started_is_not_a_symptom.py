"""Decir cuándo empezó no puede cambiar qué documentos salen (11-sep-2026).

Sale del registro de producción, no de mi cabeza. De las 345 respuestas dadas, seis se quedaron
en «no tengo información fiable sobre esto», y **las seis en castellano**. Leídas una por una,
tres eran fallos de verdad:

- «le duele el oido desde ayer» — el corpus tiene `seup_otitis`, `mlp_es_earinfections` y tres
  fichas más de oído.
- «le sangro la nariz un momento y ya ha parado» — hay material de epistaxis.
- «Cuando dalsy le doy a mi hijo?» — Dalsy es ibuprofeno y hay calculadora (esto ya lo arregló
  el puente de marcas del 7-sep).

Las otras tres eran negativas correctas, y una da gusto: «mi perro se ha comido una tableta de
chocolate».

La causa es la hermana de la edad (L133). Un padre no escribe «otitis», escribe «le duele el
oído **desde ayer**». Medido: «desde» aparece en **497 pasajes** del corpus y «momento» en 275,
casi todos de los dos libros de texto de mil páginas, así que esas dos palabras solas arrastran
los libros por encima de la hoja de la SEUP que responde. En las ocho lenguas, decir cuándo
empezó metía **quince términos de ruido en ocho preguntas**.

La regla es la misma que con la edad: **cuándo empezó es contexto clínico, no un término de
búsqueda**. El triaje sí lo usa —«más de tres días de fiebre» es un criterio—; el buscador, no.
"""

from __future__ import annotations

import pytest

from pedibot.index.store import query_terms

#: la misma pregunta sin decir cuándo y diciéndolo
PARES: dict[str, tuple[str, str]] = {
    "es": ("le duele el oído", "le duele el oído desde ayer"),
    "en": ("his ear hurts", "his ear hurts since yesterday"),
    "fr": ("il a mal à l'oreille", "il a mal à l'oreille depuis hier"),
    "de": ("sein Ohr tut weh", "sein Ohr tut seit gestern weh"),
    "ru": ("у него болит ухо", "у него болит ухо со вчера"),
    "pt": ("dói-lhe o ouvido", "dói-lhe o ouvido desde ontem"),
    "ar": ("أذنه تؤلمه", "أذنه تؤلمه منذ أمس"),
    "hi": ("उसके कान में दर्द है", "उसके कान में कल से दर्द है"),
}

#: y «ahora mismo», «esta mañana», «hoy»… una por una
AHORA: dict[str, list[str]] = {
    "es": ["desde ayer", "desde anoche", "esta mañana", "ahora mismo", "hoy"],
    # «right now» no está: «right» no es palabra vacía y no puede serlo, porque «right
    # side» es el criterio de dolor abdominal derecho —apendicitis— en las reglas de alarma.
    "en": ["since yesterday", "already", "today", "still"],
    "fr": ["depuis hier", "ce matin", "maintenant", "encore"],
    "de": ["seit gestern", "heute", "jetzt", "schon"],
    "ru": ["со вчера", "сегодня", "сейчас", "уже"],
    "pt": ["desde ontem", "esta manhã", "agora", "ainda"],
    "ar": ["منذ أمس", "اليوم", "الآن"],
    "hi": ["कल से", "आज", "अभी"],
}


@pytest.mark.parametrize("lang", sorted(PARES))
def test_decir_cuando_empezo_no_anade_terminos(lang: str):
    sin, con = PARES[lang]
    a, b = query_terms(sin), query_terms(con)
    sobran = [t for t in b if t not in a]
    assert not sobran, (
        f"en {lang}, decir cuándo empezó mete {sobran} en la consulta; «desde» sale en 497 "
        "pasajes del corpus y arrastra los libros de texto por encima de la hoja que responde"
    )


@pytest.mark.parametrize("lang", sorted(PARES))
def test_y_no_se_lleva_por_delante_el_sintoma(lang: str):
    """La dirección contraria: una palabra vacía de más podría comerse «oído» o «duele»."""
    sin, con = PARES[lang]
    a, b = query_terms(sin), query_terms(con)
    faltan = [t for t in a if t not in b]
    assert not faltan, f"en {lang}, decir cuándo empezó hace desaparecer {faltan}"


@pytest.mark.parametrize(
    ("lang", "momento"),
    [(lg, m) for lg, ms in AHORA.items() for m in ms],
)
def test_una_expresion_de_tiempo_sola_no_es_una_consulta(lang: str, momento: str):
    """«desde ayer» no es una pregunta de pediatría: no puede aportar ni un término."""
    assert not query_terms(momento), (
        f"«{momento}» ({lang}) aporta {query_terms(momento)} a la búsqueda, y no dice nada "
        "de lo que le pasa al niño"
    )
