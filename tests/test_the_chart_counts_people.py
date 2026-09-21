"""La gráfica del panel cuenta personas, no páginas (21-sep-2026).

Decía «visitas» y sumaba páginas vistas: quien abría diez guías eran diez. El día que marcó 176
no vinieron 176 personas. El operador la leyó como si fueran datos de Google, y pidió visitas de
verdad, con Google «otra línea en paralelo». La línea de Google son sus clics por día, que son
visitas también y se pueden poner en la misma escala; las impresiones no.
"""

from __future__ import annotations

import datetime as dt
import json

from pedibot.admin import _chart
from pedibot.ops import report

CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140"


def _linea(ip: str, uri: str, ts: float) -> str:
    return json.dumps(
        {
            "msg": "handled request",
            "ts": ts,
            "status": 200,
            "request": {
                "remote_ip": ip,
                "method": "GET",
                "uri": uri,
                "headers": {"User-Agent": [CHROME]},
            },
        }
    )


def test_ten_pages_by_one_person_is_one_visit_that_day() -> None:
    ts = 1_789_000_000.0
    lineas = [_linea("9.9.9.9", "/_astro/a.css", ts)]
    lineas += [_linea("9.9.9.9", f"/es/guia-{i}", ts + i) for i in range(10)]
    lineas += [_linea("8.8.4.4", "/_astro/a.css", ts), _linea("8.8.4.4", "/es/dose", ts)]
    r = report.count_visits(lineas)
    dia = dt.datetime.fromtimestamp(ts, dt.UTC).date().isoformat()
    assert r["per_day"][dia] == 11, "las páginas vistas se siguen contando"
    assert r["visitors_per_day"][dia] == 2, "pero la gráfica cuenta personas"


def _hoy(n: int = 0) -> str:
    return (dt.date.today() - dt.timedelta(days=n)).isoformat()


def test_the_chart_says_people_not_visits_of_pages() -> None:
    h = _chart({_hoy(1): 5, _hoy(): 3}, {_hoy(): 1}, 7)
    assert "personas" in h
    assert "máx 5 personas/día" in h


def test_google_clicks_are_a_parallel_dashed_line_on_the_same_scale() -> None:
    h = _chart({_hoy(1): 5}, {}, 7, google={_hoy(2): 10})
    assert "clics desde Google" in h
    assert "stroke-dasharray" in h
    assert "máx 10" in h, "una sola escala: si Google trae más, el techo es el suyo"


def test_without_google_data_there_is_no_google_line() -> None:
    h = _chart({_hoy(1): 5}, {}, 7)
    assert "Google" not in h
    assert "stroke-dasharray" not in h
