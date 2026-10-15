"""El escáner de enlaces de Outlook no es una persona (15-oct-2026).

Cada correo de difusión «traía» visitas en el mismo minuto en que salía: `?r=mcn`, `?r=accem`,
`?r=mhp-salud`… Miradas una a una, las 15 llegadas con canal desde el 11-oct eran 12 de Microsoft
(AS8075), una de Amazon y el resto pruebas nuestras: ningún clic humano. El pico del 12-oct
(179 «personas») era lo mismo, 1.110 peticiones en una hora desde 72.145, 72.152, 135.232…
Cargan la página entera, CSS y JavaScript incluidos, así que pasan la prueba del navegador; por
agente son un Chrome de Windows. Sólo la dirección los delata: una casa no navega desde la nube.

La lista sale de las redes que anuncian los centros de datos (RIPEstat), en
`config/datacenter_nets.txt`. Apple y Cloudflare no están: por ellas pasan personas de verdad
(Private Relay, WARP).
"""

from __future__ import annotations

import json

from pedibot.ops import report


def _linea(ip: str, uri: str, ts: float = 1_792_000_000.0) -> str:
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


CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79"
)


def _visita(ip: str, uri: str = "/?r=mcn") -> list[str]:
    return [_linea(ip, uri), _linea(ip, "/_astro/index.CK-Hh5JU.js")]


def test_el_escaner_de_outlook_no_es_una_persona():
    # las direcciones de verdad del 12 al 15-oct, todas AS8075
    for ip in ("72.153.231.4", "72.145.76.10", "135.232.20.2", "48.209.223.128", "74.179.68.9"):
        r = report.count_visits(_visita(ip))
        assert r["visitors"] == 0, ip
        assert r["web"]["channels"] == {}, f"{ip}: un escáner no trae a nadie por un canal"


def test_un_programa_desde_amazon_tampoco():
    assert report.count_visits(_visita("3.231.237.226"))["visitors"] == 0


def test_una_conexion_de_casa_si_cuenta():
    r = report.count_visits(_visita("47.62.69.158"))  # Vodafone España
    assert r["visitors"] == 1
    assert r["web"]["channels"] == {"mcn": 1}


def test_apple_y_cloudflare_no_estan_en_la_lista():
    """Private Relay y WARP son personas detrás de una red de empresa."""
    for ip in ("17.253.144.10", "104.28.0.1", "172.226.0.1"):
        assert not report._de_rastreador(ip), ip


def test_la_lista_esta_en_el_repositorio_y_no_vacia():
    nets = report._datacenter_nets()
    assert len(nets) > 1000, "Microsoft, Amazon y Google Cloud solos ya son miles de redes"
