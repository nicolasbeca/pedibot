"""El panel habla de la web, no sólo de Google (21-sep-2026).

El operador: «el panel está muy centrado en Google, y yo quiero que esos datos existan pero quiero
saber más cosas en general de la web». Todo sale del mismo registro del servidor que ya cuenta
las visitas, sin cookies ni nada que se instale en el navegador del padre: de dónde llega cada
persona, con qué aparato, en qué idioma tiene el navegador, qué herramientas abre y por qué
página entra. Se cuentan personas, no páginas.
"""

from __future__ import annotations

import json

from pedibot.admin import _web_card
from pedibot.ops import report

MOVIL = "Mozilla/5.0 (Linux; Android 14; SM-A145) AppleWebKit/537.36 Chrome/140 Mobile Safari"
PC = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140"


def _l(ip, uri, ts, ua=PC, ref="", lang="es-ES,es;q=0.9"):
    h = {"User-Agent": [ua], "Accept-Language": [lang]}
    if ref:
        h["Referer"] = [ref]
    return json.dumps(
        {
            "msg": "handled request",
            "ts": ts,
            "status": 200,
            "request": {"remote_ip": ip, "method": "GET", "uri": uri, "headers": h},
        }
    )


def _persona(ip, paginas, ts=1_789_000_000.0, **kw):
    out = [_l(ip, "/_astro/a.css", ts, **{k: v for k, v in kw.items() if k != "ref"})]
    for i, uri in enumerate(paginas):
        out.append(
            _l(ip, uri, ts + i, **(kw if i == 0 else {k: v for k, v in kw.items() if k != "ref"}))
        )
    return out


def _web():
    lineas = []
    lineas += _persona("1.1.1.1", ["/es/dose", "/es/growth/es"], ref="https://www.google.com/")
    lineas += _persona("2.2.2.2", ["/hi/", "/hi/emergency"], ua=MOVIL, lang="hi-IN,hi;q=0.9")
    lineas += _persona("3.3.3.3", ["/es/dose"], ua=MOVIL, ref="https://t.co/abc", lang="en-NG")
    lineas += _persona("4.4.4.4", ["/guides/fever"], ref="https://chatgpt.com/")
    lineas += _persona("5.5.5.5", ["/es/vaccines"], ref="https://pedibot.xyz/es/")
    return report.count_visits(lineas)


def test_where_people_come_from() -> None:
    w = _web()["web"]
    assert w["sources"] == {"Google": 1, "directo": 2, "redes sociales": 1, "asistentes de IA": 1}


def test_phone_or_computer() -> None:
    assert _web()["web"]["devices"] == {"móvil": 2, "ordenador": 3}


def test_browser_language_and_region() -> None:
    w = _web()["web"]
    assert w["browser_langs"] == {"es": 3, "hi": 1, "en": 1}
    assert w["regions"] == {"ES": 3, "IN": 1, "NG": 1}


def test_which_tools_people_open_counted_once_each() -> None:
    t = _web()["web"]["tools"]
    assert t["calculadora de dosis"] == 2
    assert t["percentiles"] == 1
    assert t["urgencias"] == 1
    assert t["chat"] == 1
    assert t["guías"] == 1
    assert t["vacunas"] == 1


def test_the_page_people_land_on() -> None:
    assert _web()["web"]["entries"][0] == ("/es/dose", 2)


def test_the_card_shows_it_all() -> None:
    h = _web_card(_web()["web"])
    for cosa in (
        "De dónde llegan",
        "Google",
        "móvil",
        "Idioma del navegador",
        "hindi",
        "Qué herramientas usan",
        "calculadora de dosis",
        "Por dónde entran",
        "/es/dose",
    ):
        assert cosa in h, cosa


def test_an_empty_log_is_an_empty_card_not_an_error() -> None:
    assert "Todavía" in _web_card({})
