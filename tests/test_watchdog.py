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
    dead = wd.dead_units(
        status_of=lambda u: "failed" if u == "pedibot-acp" else "active",
        dormir=lambda _s: None,
    )
    assert dead == ["pedibot-acp"]


def test_unknown_status_counts_as_dead():
    """A systemctl call that errors out must not be read as healthy."""
    wd = _watchdog()
    assert wd.dead_units(status_of=lambda _u: "unknown", dormir=lambda _s: None) == list(
        wd.UNITS
    )


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


# --------------------------------------------------------------------------------------------
# El registro del que vive el panel (7-sep-2026)
#
# Las visitas, las páginas vistas y el tiempo de permanencia salen de `journalctl -u caddy`. Si
# Caddy dejara de escribir ahí, el panel enseñaría CERO visitas — y cero visitas no parece una
# avería, parece que no vino nadie. Es la L31 otra vez: el silencio que no se distingue de la
# ausencia, y en el único sitio con el que el operador decide si esto funciona.
# --------------------------------------------------------------------------------------------


def _respuesta(texto: str):
    class R:
        stdout = texto

    def correr(*a, **k):
        return R()

    return correr


def test_a_busy_hour_counts_its_lines():
    wd = _watchdog()
    n = wd.access_log_lines(correr=_respuesta("una\ndos\ntres\n\ncuatro\n"))
    assert n == 4  # la línea en blanco no cuenta


def test_a_silent_access_log_is_below_the_floor():
    wd = _watchdog()
    assert wd.access_log_lines(correr=_respuesta("")) < wd.ACCESS_LOG_MIN
    assert wd.access_log_lines(correr=_respuesta("solo una\n")) < wd.ACCESS_LOG_MIN


def test_the_floor_is_far_below_a_real_quiet_hour():
    """Medido en el servidor en un rato tranquilo: 403 líneas en dos horas. El suelo tiene que
    quedar muy por debajo, para que el aviso signifique «esto está mudo» y nunca «hoy hubo poca
    gente» — un vigilante que grita por poco tráfico se deja de leer."""
    wd = _watchdog()
    assert wd.ACCESS_LOG_MIN <= 10


def test_a_restart_is_not_a_dead_service():
    """18-sep-2026: el vigilante avisó de «Servicios parados: pedibot-telegram, pedibot-acp» y no
    había nada parado — el despliegue los estaba reiniciando en ese mismo segundo. Del journal:
    el vigilante arrancó a las 13:21:14, el despliegue reinició a las 13:21:16 y el vigilante
    miró a las 13:21:17.

    Un aviso que salta por un despliegue enseña al operador a ignorar el aviso, que es la mitad
    cara de la lección de los falsos positivos. Mirar dos veces separa el reinicio de la muerte
    sin preguntarle a nadie si hay un despliegue en marcha.
    """
    wd = _watchdog()
    vistas = {"n": 0}

    def reiniciando(_u: str) -> str:
        vistas["n"] += 1
        return "activating" if vistas["n"] <= len(wd.UNITS) else "active"

    assert wd.dead_units(status_of=reiniciando, dormir=lambda _s: None) == []


def test_a_service_that_stays_down_is_still_reported():
    """Y la otra mitad: mirar dos veces no puede convertirse en no mirar."""
    wd = _watchdog()
    assert wd.dead_units(status_of=lambda _u: "failed", dormir=lambda _s: None) == list(wd.UNITS)
