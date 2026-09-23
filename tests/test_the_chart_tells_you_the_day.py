"""La gráfica del panel, con el ratón encima (23-sep-2026).

El operador: «en la gráfica de visitas y consultas me gustaría que hubiera más información, y
que fuera más dinámica, donde pudiera ponerme encima con el ratón y que me diera datos».

Lo que hace falta para eso no es dibujo: son series por día que antes no salían del informe.
Una consulta con aviso rojo y una consulta sin fuente son las dos cosas que cambian lo que él
hace ese día, y sólo existían como totales del periodo.
"""

from __future__ import annotations

import sqlite3

from pedibot.ops import report
from pedibot.ops.store import _SCHEMA as SCHEMA


def _con() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)
    filas = [
        ("2026-09-21T10:00:00", "s1", "es", "ES", "p", "r", "routine", "ok", "", "web"),
        ("2026-09-21T11:00:00", "s2", "es", "ES", "p", "r", "urgent", "ok", "", "web"),
        ("2026-09-22T09:00:00", "s3", "en", "US", "p", "r", "emergency", "ok", "", "web"),
        ("2026-09-22T10:00:00", "s4", "en", "US", "p", "r", "routine", "no_source", "", "web"),
    ]
    con.executemany(
        "INSERT INTO answers (ts, session, lang, country, question, answer, level, verification,"
        " chunk_ids, source) VALUES (?,?,?,?,?,?,?,?,?,?)",
        filas,
    )
    con.commit()
    return con


def test_the_alarms_of_each_day_are_there() -> None:
    q = report.questions(_con(), days=0)
    assert q["alarms_per_day"] == {"2026-09-21": 1, "2026-09-22": 1}


def test_so_are_the_ones_with_no_source() -> None:
    q = report.questions(_con(), days=0)
    assert q["no_source_per_day"] == {"2026-09-22": 1}


def test_the_chart_can_be_hovered() -> None:
    """Cada día tiene su banda y sus datos colgados, que es lo que lee el ratón."""
    from pedibot.admin import _chart

    svg = _chart(
        {"2026-09-21": 4, "2026-09-22": 9},
        {"2026-09-21": 2, "2026-09-22": 2},
        0,
        google={"2026-09-22": 3},
        alarms={"2026-09-22": 1},
        no_source={"2026-09-22": 1},
    )
    assert 'class="hit"' in svg
    assert 'data-d="2026-09-22"' in svg
    assert 'data-v="9"' in svg and 'data-q="2"' in svg
    assert 'data-g="3"' in svg and 'data-a="1"' in svg and 'data-n="1"' in svg
