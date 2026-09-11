"""El panel contaba 3.227 visitantes donde había 201 (11-sep-2026).

Lo notó el operador: demasiadas visitas para tan pocas consultas. Medido sobre catorce días del
registro: **6.258 vistas y 3.227 visitantes**, de los cuales **2.729 pidieron una página y nada
más** y sólo **211 llegaron a cargar un fichero estático** — que es lo que hace cualquier
navegador de verdad al abrir una página, y lo que no hace quien sólo quiere el HTML.

El código ya lo sabía. Tenía escrito, encima del contador, que «uno que pide una página y se va
es un rastreador, diga lo que diga su agente», y nunca lo aplicaba: `pages_each` sólo servía para
contar quién volvía.

Dos coladeros concretos, encontrados mirando quién eran los que más pedían:

1. **Google.** Sus direcciones `66.249.79.x` pedían 897 páginas con un agente de Chrome normal,
   sin la palabra «bot» en ninguna parte: es su renderizador, que carga la página entera como un
   navegador. La red `66.249.64.0/19` la publica Google, así que se puede excluir por dirección.
2. **Agentes que no dicen «bot»**: `ContactScraper/DomainWorkers/2.0` y `Lightpanda/1.0` — un
   raspador y un navegador headless — pasaban limpios porque el filtro buscaba bot|crawl|spider.

La cifra honesta es la que se defiende sola: **cargó la página entera, y no viene de una red de
rastreo conocida**. Lo demás se sigue enseñando, pero dicho por su nombre.
"""

from __future__ import annotations

import json

from pedibot.ops import report


def _linea(ip: str, ua: str, uri: str, ts: float = 1_789_000_000.0, status: int = 200) -> str:
    return json.dumps(
        {
            "msg": "handled request",
            "ts": ts,
            "status": status,
            "request": {
                "remote_ip": ip,
                "method": "GET",
                "uri": uri,
                "headers": {"User-Agent": [ua]},
            },
        }
    )


CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140"


def test_quien_solo_pide_el_html_no_es_una_visita():
    r = report.count_visits([_linea("9.9.9.9", CHROME, "/es/dose")])
    assert r["visitors"] == 0, "una página sin un solo fichero de la página no es un navegador"
    assert r["page_requests"] == 1, "la petición existió y se sigue contando por su nombre"


def test_quien_carga_la_pagina_entera_si_lo_es():
    r = report.count_visits(
        [
            _linea("9.9.9.9", CHROME, "/es/dose"),
            _linea("9.9.9.9", CHROME, "/_astro/index.CK-Hh5JU.js"),
        ]
    )
    assert r["visitors"] == 1
    assert r["views"] == 1, "el fichero estático prueba el navegador, no es una página vista"


def test_el_renderizador_de_google_no_cuenta_aunque_cargue_todo():
    """66.249.64.0/19 es la red que Google publica para su rastreador."""
    r = report.count_visits(
        [
            _linea("66.249.79.132", CHROME, "/es/dose"),
            _linea("66.249.79.132", CHROME, "/_astro/index.CK-Hh5JU.js"),
        ]
    )
    assert r["visitors"] == 0


def test_los_agentes_que_no_dicen_bot_tambien_se_filtran():
    for ua in ("Mozilla/5.0 (compatible; ContactScraper/DomainWorkers/2.0)", "Lightpanda/1.0"):
        r = report.count_visits([_linea("8.8.4.4", ua, "/"), _linea("8.8.4.4", ua, "/favicon.ico")])
        assert r["visitors"] == 0, ua


def test_el_numero_en_bruto_sigue_estando_para_poder_compararlos():
    lineas = [_linea(f"10.0.0.{i}", CHROME, "/") for i in range(1, 51)]
    lineas += [_linea("9.9.9.9", CHROME, "/es"), _linea("9.9.9.9", CHROME, "/favicon.ico")]
    r = report.count_visits(lineas)
    assert r["page_requests"] == 51, "todo lo que no se identifica como robot"
    assert r["visitors"] == 1, "y de todo eso, un navegador"
