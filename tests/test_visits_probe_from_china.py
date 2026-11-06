"""Un barrido desde China no son 340 visitantes (6-nov-2026).

Del 4-nov 16:00 al 5-nov 16:00 UTC, justo 24 horas, a unas 300 peticiones por hora: 724 IP, todas
con navegador en `zh-CN`, cada una abre `/` y deja que el service worker precargue, y se va. Medido
por ASN: Tencent, Huawei Cloud y nodos en China Telecom, Unicom y Mobile, lo que deja un servicio de
pruebas desde muchos puntos. El contador pasó de 8 visitantes al día a 96 y 248, y China a ser el
segundo país del panel público. La web no tiene chino y nunca se ha hecho una pregunta en chino.

Huawei Cloud va a la lista de centros de datos; los nodos en operadores no se pueden listar sin
llevarse a personas, así que cuenta la conducta: navegador `zh-CN` y una sola página no es una
visita. Quien en chino abre dos páginas sí, y un navegador en chino desde España también.
"""

from __future__ import annotations

import json

from pedibot.ops import report

CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140"
)


def _linea(ip: str, uri: str, lang: str, ts: float = 1_789_000_000.0) -> str:
    return json.dumps(
        {
            "msg": "handled request",
            "ts": ts,
            "status": 200,
            "request": {
                "remote_ip": ip,
                "method": "GET",
                "uri": uri,
                "headers": {"User-Agent": [CHROME], "Accept-Language": [lang]},
            },
        }
    )


def _visita(ip: str, lang: str, *paginas: str) -> list[str]:
    lineas = [_linea(ip, "/_astro/index.css", lang)]
    return lineas + [_linea(ip, p, lang, 1_789_000_000.0 + 60 * i) for i, p in enumerate(paginas)]


def test_a_probe_opens_one_page_in_zh_cn_and_does_not_count() -> None:
    r = report.count_visits(_visita("140.206.235.8", "zh-CN,zh;q=0.9", "/"))
    assert r["visitors"] == 0
    assert r["views"] == 0
    assert r["page_requests"] == 1, "la petición existió y se sigue contando por su nombre"
    assert "CN" not in r["web"]["regions"]


def test_a_chinese_reader_who_browses_counts() -> None:
    r = report.count_visits(_visita("140.206.235.9", "zh-CN,zh;q=0.9", "/", "/guides"))
    assert r["visitors"] == 1


def test_a_chinese_browser_from_elsewhere_counts() -> None:
    """Una familia china en Madrid: `zh-ES`, `zh-TW` o `zh` a secas no son el barrido."""
    for lang in ("zh-TW,zh;q=0.9", "zh-ES", "zh"):
        r = report.count_visits(_visita("81.2.3.4", lang, "/"))
        assert r["visitors"] == 1, lang


def test_one_page_in_another_language_still_counts() -> None:
    r = report.count_visits(_visita("81.2.3.5", "en-GB,en;q=0.9", "/"))
    assert r["visitors"] == 1


def test_huawei_cloud_is_on_the_list_of_clouds() -> None:
    from pathlib import Path

    texto = (Path(__file__).resolve().parents[1] / "config" / "datacenter_nets.txt").read_text(
        encoding="utf-8"
    )
    assert "AS136907" in texto and "AS55990" in texto
