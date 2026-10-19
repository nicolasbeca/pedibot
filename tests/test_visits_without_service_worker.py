"""El service worker no es una persona mirando páginas (19-oct-2026).

Para que la web funcione sin conexión, `sw.js` descarga por su cuenta /emergency, /growth,
/vaccines, /muac y /offline nada más abrir cualquier página. El panel contaba esas descargas
como páginas vistas por la persona. Medido sobre siete días del registro: **579 vistas donde
había 139**, 44 visitantes «que vuelven» donde había 8, una mediana de 2,7 s donde había 19,5 s,
y las herramientas (vacunas 41, percentiles 40, cinta del brazo 38) en realidad 4, 2 y 1.

Lo que pide el service worker llega con `Referer: https://pedibot.xyz/sw.js`. No es una página
que nadie haya abierto: fuera de las vistas, de las herramientas y de quién vuelve.
"""

from __future__ import annotations

import json

from pedibot.ops import report

CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140"
)
SW = "https://pedibot.xyz/sw.js"


def _linea(uri: str, ts: float, referer: str = "") -> str:
    headers = {"User-Agent": [CHROME]}
    if referer:
        headers["Referer"] = [referer]
    return json.dumps(
        {
            "msg": "handled request",
            "ts": ts,
            "status": 200,
            "request": {"remote_ip": "9.9.9.9", "method": "GET", "uri": uri, "headers": headers},
        }
    )


def _visita_con_precarga() -> list[str]:
    t = 1_792_000_000.0
    return [
        _linea("/", t),
        _linea("/_astro/index.CK-Hh5JU.js", t + 0.2, "https://pedibot.xyz/"),
        _linea("/offline", t + 1, SW),
        _linea("/vaccines", t + 1.2, SW),
        _linea("/growth", t + 1.4, SW),
        _linea("/muac", t + 1.6, SW),
        _linea("/emergency", t + 1.8, SW),
    ]


def test_lo_que_descarga_el_service_worker_no_es_una_pagina_vista():
    r = report.count_visits(_visita_con_precarga())
    assert r["visitors"] == 1
    assert r["views"] == 1, "sólo abrió la portada; lo demás lo pidió sw.js"
    assert r["top"] == [("/", 1)]


def test_ni_hace_que_parezca_que_vuelve():
    assert report.count_visits(_visita_con_precarga())["returning"] == 0


def test_ni_cuenta_como_uso_de_las_herramientas():
    assert report.count_visits(_visita_con_precarga())["web"]["tools"] == {"chat": 1}


def test_la_misma_herramienta_abierta_de_verdad_si_cuenta():
    t = 1_792_000_100.0
    lineas = _visita_con_precarga() + [_linea("/vaccines", t, "https://pedibot.xyz/")]
    r = report.count_visits(lineas)
    assert r["views"] == 2
    assert r["web"]["tools"] == {"chat": 1, "vacunas": 1}
