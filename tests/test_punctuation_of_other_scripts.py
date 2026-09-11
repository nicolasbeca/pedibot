"""La interrogación árabe se comía la marca (11-sep-2026).

Un padre en El Cairo escribe «طفلي وزنه 14 كيلو، كم أعطيه من بنادول؟» — «mi hijo pesa 14 kilos,
¿cuánto Panadol le doy?». El peso se leía bien y la marca estaba en el catálogo, y aun así **no
salía ninguna dosis**: el detector parte la frase en palabras por una lista de signos de
puntuación **latinos**, así que el último token no era «بنادول» sino «بنادول؟», con el signo
pegado. Quitando el signo, la misma pregunta da la dosis.

El árabe tiene su propia coma (‎،‎), su punto y coma (‎؛‎) y su interrogación (‎؟‎), y el hindi
termina las frases con danda (‎।‎). Son caracteres distintos de los latinos, con otro punto de
código, y ninguno estaba en la lista.

Es la misma familia de fallos que `\b` en devanagari y que el artículo pegado en árabe: **el
código da por hecho la forma de una lengua que no es la suya**, no falla, y simplemente deja de
encontrar cosas en el mercado que el proyecto ha decidido atacar.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import dose_intent
from pedibot.bot.drugs import DrugCatalog
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def catalogo() -> DrugCatalog:
    return DrugCatalog(ROOT / "config" / "drugs.yaml")


#: la misma pregunta con y sin el signo pegado: las dos tienen que dar la misma dosis
PREGUNTAS = [
    ("ar", "طفلي وزنه 14 كيلو، كم أعطيه من بنادول؟"),
    ("ar", "ابني 14 كيلو؛ كم من أدول؟"),
    ("ar", "طفلي وزنه ١٤ كيلو، كم أعطيه من بنادول؟"),
    ("hi", "मेरे बच्चे का वजन 14 किलो है, कितना क्रोसिन दूँ।"),
    ("hi", "बच्चे का वजन 14 किलो, कितना डोलो।"),
    ("hi", "मेरे बच्चे का वजन १४ किलो है, कितना ब्रूफेन दूँ।"),
]


@pytest.mark.parametrize(("lang", "pregunta"), PREGUNTAS)
def test_el_signo_pegado_no_esconde_la_marca(catalogo: DrugCatalog, lang: str, pregunta: str):
    r = dose_intent(pregunta, catalogo)
    assert r is not None, f"[{lang}] «{pregunta}» no produce dosis; la marca está en el catálogo"
    clave, kg = r
    assert clave in ("paracetamol", "ibuprofen", "ibuprofeno"), clave
    assert kg == 14.0, f"peso mal leído: {kg}"


def test_y_la_puntuacion_no_inventa_un_medicamento(catalogo: DrugCatalog):
    """La otra dirección: separar por más signos no puede hacer aparecer marcas donde no las hay."""
    assert dose_intent("طفلي وزنه 14 كيلو، ماذا أفعل؟", catalogo) is None
    assert dose_intent("मेरे बच्चे का वजन 14 किलो है, क्या करूँ।", catalogo) is None
