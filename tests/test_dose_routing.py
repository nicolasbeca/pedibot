"""La calculadora de dosis tiene que ser alcanzable en los ocho idiomas (7-sep-2026).

Es la herramienta determinista insignia: da los mililitros exactos de una tabla publicada, sin
modelo y sin coste. Y hasta hoy **tres de los ocho idiomas no llegaban a ella nunca**:

    es/en/fr/de/pt   ('paracetamol', 12.0)   correcto
    ru  сколько нурофена ребёнку весом 12 кг    →  None
    ar  كم جرعة الباراسيتامول لطفل وزنه 12 كيلو  →  None
    hi  12 किलो के बच्चे को कितना पैरासिटामोल     →  None

Cuatro causas encadenadas, y cada una bastaba por sí sola:

1. Los kilos: el patrón solo conocía «kg» y sus variantes latinas. Ni кг, ni كيلو, ni किलो.
2. Las cifras: un teclado árabe escribe ١٢ y uno hindi १२, no 12.
3. Las palabras: el respaldo que busca la marca usaba `[^\\W\\d_]`, que se apoya en `\\w` — y las
   vocales del devanagari son marcas combinantes, **no alfanuméricas**, así que «पैरासिटामोल» se
   rompía en trozos de una letra y no quedaba ningún token. Primo hermano del `\\b` que tampoco
   funciona en esa escritura.
4. El catálogo: `resolve()` comparaba con el genérico en inglés y español — dos de los ocho que
   la ficha tiene—, y además exigía coincidencia exacta, cuando el ruso declina («парацетамолА»).

Salió de aplicar al enrutador de dosis la misma jugada que acababa de funcionar con el de vacunas:
**probarlo en los ocho idiomas**. Ninguna consulta real lo había tocado todavía.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.answer import SUPPORTED_LANGS, dose_intent
from pedibot.bot.drugs import DrugCatalog

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def catalogo() -> DrugCatalog:
    return DrugCatalog(RAIZ / "config" / "drugs.yaml")


#: Una pregunta de dosis por idioma, con la marca o el genérico que un padre de ese mercado
#: escribiría y con los kilos en su unidad. El resultado esperado, y el peso.
PREGUNTAS = {
    "es": ("cuánto apiretal le doy a mi hijo de 12 kg", "paracetamol"),
    "en": ("how much calpol for a 12 kg child", "paracetamol"),
    "fr": ("combien de doliprane pour un enfant de 12 kg", "paracetamol"),
    "de": ("wie viel Nurofen für ein Kind von 12 kg", "ibuprofen"),
    "pt": ("quanto alivium para uma criança de 12 kg", "ibuprofen"),
    "ru": ("сколько парацетамола ребёнку 12 килограмм", "paracetamol"),
    "ar": ("كم جرعة الباراسيتامول لطفل وزنه 12 كيلو", "paracetamol"),
    "hi": ("12 किलो के बच्चे को कितना पैरासिटामोल", "paracetamol"),
}


def test_there_is_a_question_for_every_language() -> None:
    """El candado del candado: un idioma sin pregunta aquí no se comprobaría."""
    faltan = [lang for lang in SUPPORTED_LANGS if lang not in PREGUNTAS]
    assert not faltan, f"escribe una pregunta de dosis en {faltan}"


@pytest.mark.parametrize("lang", sorted(PREGUNTAS))
def test_the_calculator_is_reachable_in_every_language(lang: str, catalogo: DrugCatalog) -> None:
    pregunta, esperado = PREGUNTAS[lang]
    r = dose_intent(pregunta, catalogo)
    assert r is not None, (
        f"[{lang}] no llega a la calculadora: «{pregunta}». Quien pregunte así recibirá una "
        "respuesta redactada por el modelo en vez del mililitro exacto de la tabla."
    )
    assert r[0] == esperado and r[1] == 12.0, f"[{lang}] resolvió {r}"


@pytest.mark.parametrize(
    ("pregunta", "kg"),
    [
        ("12 kg", 12.0),
        ("12 kilos", 12.0),
        ("12,5 kg", 12.5),
        ("12 кг", 12.0),
        ("12 килограмм", 12.0),
        ("12 كيلو", 12.0),
        ("12 كجم", 12.0),
        ("12 किलो", 12.0),
        ("12 किलोग्राम", 12.0),
        ("١٢ كجم", 12.0),  # cifras arábigo-índicas, las de un teclado árabe
        ("१२ किलोग्राम", 12.0),  # cifras devanagari
    ],
)
def test_the_kilos_are_read_in_every_script(
    pregunta: str, kg: float, catalogo: DrugCatalog
) -> None:
    r = dose_intent(f"paracetamol {pregunta}", catalogo)
    assert r is not None and r[1] == kg, f"«{pregunta}» → {r}"


@pytest.mark.parametrize(
    "nombre",
    ["парацетамола", "ибупрофена", "الباراسيتامول", "पैरासिटामोल", "आइबुप्रोफेन", "Ibuprofeno"],
)
def test_the_generic_name_resolves_in_its_own_script(nombre: str, catalogo: DrugCatalog) -> None:
    """El catálogo guarda el genérico en los ocho idiomas y el resolutor miraba dos. Y el ruso
    declina, así que hace falta comparar por raíz."""
    assert catalogo.resolve(nombre) is not None, f"«{nombre}» no resuelve"


@pytest.mark.parametrize(
    "pregunta",
    [
        "mi hijo tiene fiebre",  # ni peso ni medicamento
        "pesa 12 kg y tiene tos",  # peso sin medicamento: no es una pregunta de dosis
        "cuánto paracetamol le doy",  # medicamento sin peso: la calculadora necesita el peso
    ],
)
def test_a_question_that_is_not_a_dose_question_is_left_alone(
    pregunta: str, catalogo: DrugCatalog
) -> None:
    assert dose_intent(pregunta, catalogo) is None, f"se desvía a la calculadora: «{pregunta}»"
