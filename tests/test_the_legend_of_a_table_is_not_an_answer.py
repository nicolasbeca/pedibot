"""La leyenda de una tabla no contesta a nada (25-sep-2026).

«La vacuna del rotavirus», «sus efectos secundarios», «cuándo se pone»: las tres preguntas
devolvían exactamente el mismo primer pasaje, y no era sobre el rotavirus. Era la **leyenda** de
la tabla del calendario español:

    Administración sistemática · Administración en personas susceptibles o no vacunadas con
    anterioridad · Con rayas · Calendario aprobado por el Consejo Interterritorial del SNS…

Doscientas treinta y dos palabras explicando los colores de una tabla. Ganaba por acumulación de
términos —«vacunación», «calendario», «inmunización» son justo las palabras que la expansión
añade a cualquier pregunta sobre vacunas—, y detrás de ella no cabía la hoja que sí responde.

En un documento que es una tabla, el texto de cabecera explica cómo leerla. Lo que contesta son
las notas de cada vacuna, y ésas están en sus secciones. El calendario, además, se sirve
estructurado desde `config/vaccines.yaml`: el PDF está indexado por sus notas, no por su leyenda.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
INDICE = RAIZ / "index" / "pedibot.db"

pytestmark = pytest.mark.skipif(not INDICE.exists(), reason="sin índice construido")


def test_no_calendar_contributes_its_legend() -> None:
    con = sqlite3.connect(INDICE)
    leyendas = [
        cid
        for (cid,) in con.execute(
            "SELECT chunk_id FROM chunks WHERE doc_type='calendario' AND chunk_id LIKE '%#lead#%'"
        )
    ]
    assert not leyendas, f"la cabecera de una tabla no es contenido: {leyendas}"


def test_the_calendar_still_contributes_what_it_says() -> None:
    """Y el documento sigue dentro: lo que se va es la leyenda, no las notas por vacuna."""
    con = sqlite3.connect(INDICE)
    filas = con.execute(
        "SELECT chunk_id, data FROM chunks WHERE doc_id='msan_calendario_vacunacion_2025'"
    ).fetchall()
    assert len(filas) >= 6, f"sólo quedan {len(filas)} pasajes del calendario"
    textos = " ".join(json.loads(d)["text"] for _, d in filas).lower()
    assert "meningoc" in textos and "varicela" in textos, "faltan las notas por vacuna"
