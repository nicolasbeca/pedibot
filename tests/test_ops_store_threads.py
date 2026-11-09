"""9-nov-2026: un 500 en /api/ask con cinco preguntas a la vez.

FastAPI corre los endpoints síncronos en un pool de hilos y todos comparten la única conexión
SQLite de OpsStore (`check_same_thread=False`). Dos hilos a la vez sobre ella: `count_day` leyó
`fetchone()` → None y la pregunta del padre se quedó en «Internal Server Error». Con poco
tráfico es raro; basta con que dos personas pregunten en el mismo segundo.
"""

from __future__ import annotations

import threading
from pathlib import Path

from pedibot.ops.store import OpsStore


def test_rate_limit_counters_survive_concurrent_requests(tmp_path: Path) -> None:
    ops = OpsStore(tmp_path / "ops.db", salt="x")
    errores: list[BaseException] = []
    salida = threading.Barrier(12)

    def golpea(n: int) -> None:
        try:
            salida.wait()
            for i in range(150):
                ip = f"10.0.{n}.{i % 7}"
                ops.hit_and_count(ip, 10)
                ops.count_day(ip)
        except BaseException as e:  # noqa: BLE001 - queremos ver cualquier fallo del hilo
            errores.append(e)

    hilos = [threading.Thread(target=golpea, args=(n,)) for n in range(12)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert errores == []
    assert ops.count_day("10.0.0.0") > 0


def test_the_connection_still_reads_like_sqlite(tmp_path: Path) -> None:
    """El panel de admin recibe `ops.con` y hace execute/fetchone/fetchall/iterar."""
    ops = OpsStore(tmp_path / "ops.db", salt="x")
    con = ops.con
    con.execute("CREATE TABLE t (a INTEGER)")
    cur = con.execute("INSERT INTO t (a) VALUES (?)", (5,))
    assert cur.lastrowid == 1
    con.commit()
    con.execute("INSERT INTO t (a) VALUES (7)")
    assert con.execute("SELECT count(*) FROM t").fetchone()[0] == 2
    assert [r[0] for r in con.execute("SELECT a FROM t ORDER BY a")] == [5, 7]
    assert con.execute("SELECT a FROM t ORDER BY a").fetchall() == [(5,), (7,)]
    assert con.execute("SELECT a FROM t WHERE a > 99").fetchone() is None
    assert con.execute("UPDATE t SET a = 1").rowcount == 2
