"""El panel decía «sin fuente: 6» y ahí se acababa (12-sep-2026).

Un contador no se puede arreglar. Para saber **cuáles** eran esas seis hubo que abrir la base de
operaciones a mano, y al hacerlo resultó que tres eran fallos de verdad —«le duele el oido desde
ayer» con cinco fichas de oído en el corpus, «le sangro la nariz un momento y ya ha parado» con
la del NHS indexada, y una de marca— y tres eran negativas correctas, incluida «mi perro se ha
comido una tableta de chocolate».

Al ponerlo en el panel aparecieron dos más que no había visto: un recién nacido hindi que no mama
y está decaído, y «Quels vaccins pour un bébé de 3 mois en France ?». Las dos responden ya, pero
eso es justo lo que demuestra el punto: **el número las tapaba**.

Cada línea de esa lista es una de dos cosas, y las dos se arreglan: un hueco del corpus que
llenar o un fallo del buscador. El contador no distingue; la pregunta sí.
"""

from __future__ import annotations

import re
import sqlite3

import pytest

from pedibot.admin import render
from pedibot.ops.report import unanswered


@pytest.fixture
def con() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.execute(
        "CREATE TABLE answers (id INTEGER PRIMARY KEY, ts TEXT, session TEXT, lang TEXT,"
        " country TEXT, question TEXT, answer TEXT, level TEXT, verification TEXT,"
        " chunk_ids TEXT, prompt_version TEXT, model TEXT, tokens_in INT, tokens_out INT,"
        " cost_usd REAL, latency_ms INT, feedback TEXT, source TEXT)"
    )
    filas = [
        ("2026-09-09T15:40", "es", "le duele el oido desde ayer", "no_source", "web"),
        ("2026-09-09T15:51", "es", "le sangro la nariz y ya ha parado", "no_source", "web"),
        ("2026-09-10T13:25", "es", "mi perro se ha comido chocolate", "no_source", "web"),
        ("2026-09-10T14:00", "es", "mi hijo tiene fiebre", "ok", "web"),
        ("2026-09-10T14:05", "es", "prueba interna", "no_source", "test"),
    ]
    for i, (ts, lang, q, ver, src) in enumerate(filas, 1):
        c.execute(
            "INSERT INTO answers (id, ts, lang, question, answer, level, verification,"
            " cost_usd, latency_ms, source) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (i, ts, lang, q, "…", "routine", ver, 0.0, 100, src),
        )
    c.commit()
    return c


def test_la_lista_trae_las_preguntas_no_un_numero(con: sqlite3.Connection):
    items = unanswered(con, days=0)
    textos = [i["question"] for i in items]
    assert "le duele el oido desde ayer" in textos, textos
    assert len(items) == 3, f"tenían que salir las tres de lectores: {textos}"


def test_el_trafico_de_pruebas_no_cuenta_como_un_padre(con: sqlite3.Connection):
    """La regla de todo el panel: una prueba nuestra leída como la pregunta de un padre es
    cómo se persigue un problema que no existe."""
    assert "prueba interna" not in [i["question"] for i in unanswered(con, days=0)]
    assert "prueba interna" in [i["question"] for i in unanswered(con, days=0, include_test=True)]


def test_la_tarjeta_sale_en_el_panel_con_las_preguntas_dentro(con: sqlite3.Connection):
    h = render(con, days=0)
    assert "Preguntas sin respuesta" in h, "la tarjeta no está en el panel"
    m = re.search(r"Preguntas sin respuesta \((\d+)\)", h)
    assert m and m.group(1) == "3", f"la tarjeta dice {m.group(1) if m else '?'} y son 3"
    assert "le duele el oido desde ayer" in h, "la tarjeta no enseña las preguntas"


def test_cuando_no_hay_ninguna_lo_dice_y_no_deja_un_hueco(con: sqlite3.Connection):
    con.execute("UPDATE answers SET verification='ok'")
    h = render(con, days=0)
    assert "Preguntas sin respuesta" in h
    assert "Ninguna" in h, "una tarjeta vacía sin frase es peor que no tenerla"
