"""La medicina que ya está en casa y salió mal (23-sep-2026, octava tanda).

De las 500 preguntas, 17 se quedaron sin fuente y cinco eran la misma cosa:

    «le di dos veces la misma dosis porque mi marido no sabía que ya se la había dado»
    «mi hijo vomitó después de tomar el medicamento pero no sé cuánto tiempo pasó»
    «dejé de darle el medicamento ayer, ¿tengo que reiniciarlo?»
    «le di apiretall pero creo que era otra concentración, ¿cómo lo compruebo?»
    «¿qué pasa si una dosis se da una hora antes de lo previsto?»

El corpus sabía calcular la dosis y no sabía nada de lo que pasa después, que es justo cuando
el padre escribe. Se trajeron diez hojas del NHS —las cinco subpáginas de paracetamol infantil,
las cuatro de amoxicilina y la de cómo dar medicinas a un bebé— y los puentes de castellano que
llegan hasta ellas, porque están escritas en inglés y sin puente no las alcanza nadie.

Esta prueba mira el índice de verdad: si alguien retira esas fuentes, o el puente deja de llevar,
las preguntas vuelven a quedarse secas y aquí se ve.
"""

from __future__ import annotations

import pytest

from pedibot.index.store import Index
from pedibot.settings import ROOT

BD = ROOT / "index" / "pedibot.db"

#: (lo que escribe el padre, un trozo del doc_id que tiene que aparecer arriba)
CASOS = [
    ("le di dos veces la misma dosis de paracetamol", "paracetamol_for_children"),
    ("dejé de darle el antibiótico a la mitad", "antibiotic"),
    ("el jarabe pone otra concentración distinta", "paracetamol_for_children"),
    ("se me ha olvidado una dosis del antibiótico", "antibiotic"),
]


@pytest.mark.skipif(not BD.exists(), reason="sin índice construido")
@pytest.mark.parametrize(("pregunta", "doc"), CASOS, ids=lambda x: x[:28])
def test_the_question_reaches_the_sheet(pregunta: str, doc: str) -> None:
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.ingest.classify import Taxonomy

    r = Retriever(
        Index(BD),
        Synonyms(ROOT / "config" / "synonyms.yaml"),
        taxonomy=Taxonomy(ROOT / "config" / "taxonomia.yaml"),
    )
    hits, _ = r.search(pregunta, lang="es")
    ids = [h.chunk.doc_id for h in hits[:8]]
    assert any(doc in i for i in ids), f"{pregunta} → {ids}"


@pytest.mark.skipif(not BD.exists(), reason="sin índice construido")
def test_the_sheet_that_answers_the_vomited_dose_is_in_the_corpus() -> None:
    """«Vomitó después de tomarlo» no lo contesta ninguna hoja inglesa del NHS: lo contesta la
    ficha de antitérmicos de Familia y Salud, con una frase y un número.

    No se comprueba que suba a los primeros puestos de una búsqueda léxica, porque no sube: la
    palabra «vomitó» arrastra las hojas de vómitos, que además llevan realce de alarma. Lo que
    sí se comprueba es que la frase está dentro, que es la condición para que el motor pueda
    llegar a ella por la segunda búsqueda —la que hace con las palabras de la IA cuando la
    primera no contesta—, que es como contesta hoy.
    """
    import json
    import sqlite3

    c = sqlite3.connect(BD)
    filas = c.execute("select chunk_id, data from chunks where doc_id like 'fys_%'").fetchall()
    assert filas, "las fichas de Familia y Salud no están indexadas"
    textos = " ".join(json.loads(d)["text"] for _, d in filas)
    assert "repetir la dosis si el niño vomita" in textos, textos[:300]
