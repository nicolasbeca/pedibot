"""The watchdog must notice when one of our own systemd units is down (26-ago-2026).

`ops/` is a scripts directory, not a package, so we load the module by path.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _watchdog():
    spec = importlib.util.spec_from_file_location("wd", ROOT / "ops" / "watchdog.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wd"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_all_active_means_no_problem():
    wd = _watchdog()
    assert wd.dead_units(status_of=lambda _u: "active") == []


def test_inactive_unit_is_reported():
    wd = _watchdog()
    dead = wd.dead_units(status_of=lambda u: "failed" if u == "pedibot-acp" else "active")
    assert dead == ["pedibot-acp"]


def test_unknown_status_counts_as_dead():
    """A systemctl call that errors out must not be read as healthy."""
    wd = _watchdog()
    assert wd.dead_units(status_of=lambda _u: "unknown") == list(wd.UNITS)


def test_the_units_we_actually_run_are_watched():
    wd = _watchdog()
    assert {"pedibot-api", "pedibot-telegram", "pedibot-acp", "caddy"} <= set(wd.UNITS)


# --------------------------------------------------------------------------------------------
# Que el modelo falle ya no tumba la respuesta (7-sep-2026): se contesta con las guías y el
# triaje. Bueno para quien pregunta, y peligroso para nosotros — un fallo que no se nota dura
# semanas. Por eso el vigilante lo cuenta.
# --------------------------------------------------------------------------------------------


def _base(tmp_path, filas):
    import sqlite3

    db = tmp_path / "ops.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE answers (ts TEXT, verification TEXT)")
    con.executemany("INSERT INTO answers VALUES (?,?)", filas)
    con.commit()
    con.close()
    return db


def test_a_healthy_hour_counts_zero_outages(tmp_path):
    import datetime as dt

    outages_last_hour = _watchdog().outages_last_hour

    ahora = dt.datetime(2026, 9, 7, 12, 0, tzinfo=dt.UTC)
    db = _base(tmp_path, [(ahora.isoformat(timespec="seconds"), "ok")] * 5)
    assert outages_last_hour(db, ahora) == 0


def test_outages_are_counted(tmp_path):
    import datetime as dt

    outages_last_hour = _watchdog().outages_last_hour

    ahora = dt.datetime(2026, 9, 7, 12, 0, tzinfo=dt.UTC)
    reciente = (ahora - dt.timedelta(minutes=10)).isoformat(timespec="seconds")
    viejo = (ahora - dt.timedelta(hours=5)).isoformat(timespec="seconds")
    db = _base(
        tmp_path,
        [(reciente, "no_model"), (reciente, "no_model"), (viejo, "no_model"), (reciente, "ok")],
    )
    assert outages_last_hour(db, ahora) == 2, "solo la última hora"


def test_the_spending_cap_is_not_reported_as_an_outage(tmp_path):
    """`degraded` lo decidimos nosotros y ya tiene su propio aviso. Confundirlos haría que el
    vigilante gritase «DeepSeek caído» cada día que se agota el presupuesto."""
    import datetime as dt

    outages_last_hour = _watchdog().outages_last_hour

    ahora = dt.datetime(2026, 9, 7, 12, 0, tzinfo=dt.UTC)
    r = (ahora - dt.timedelta(minutes=5)).isoformat(timespec="seconds")
    db = _base(tmp_path, [(r, "degraded")] * 9)
    assert outages_last_hour(db, ahora) == 0
