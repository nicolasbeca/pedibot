"""El registro se cuenta leyéndolo, no cargándolo (29-sep-2026).

`publish_stats` llevaba desde el 26-sep muriendo cada hora con un 137: el OOM killer. El registro
de Caddy de un año son 220 MB y 220.000 líneas, y `web_visits` lo cargaba entero tres veces —los
bytes de `journalctl`, la cadena y la lista de líneas— antes de empezar a contar. En una máquina de
2 GB sin swap el proceso llegó a 1,26 GB; y el panel `/admin` hace la misma lectura **dentro de la
API**, que es lo único que no puede caerse.

Ahora `count_visits` cuenta en **una sola pasada** sobre cualquier iterable —un generador, las
líneas de un tubo— y `web_visits` le pasa la salida de `journalctl` según llega.
"""

from __future__ import annotations

import io
import json

from pedibot.ops import report

CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140"
T0 = 1_789_000_000.0


def _linea(ip: str, uri: str, ts: float, status: int = 200, team: bool = False) -> str:
    headers = {"User-Agent": [CHROME]}
    if team:
        headers["X-Pedibot-Client"] = ["test"]
    return json.dumps(
        {
            "msg": "handled request",
            "ts": ts,
            "status": status,
            "request": {"remote_ip": ip, "method": "GET", "uri": uri, "headers": headers},
        }
    )


def _registro() -> list[str]:
    return [
        # un lector: página y su hoja de estilo
        _linea("9.9.9.9", "/es/dose", T0),
        _linea("9.9.9.9", "/_astro/index.css", T0 + 1),
        _linea("9.9.9.9", "/es/vaccines", T0 + 90),
        # el operador visita ANTES de abrir el panel: la marca llega después en el registro
        _linea("5.5.5.5", "/es/dose", T0 + 100),
        _linea("5.5.5.5", "/_astro/index.css", T0 + 101),
        _linea("5.5.5.5", "/admin", T0 + 3600),
    ]


def test_se_cuenta_en_una_sola_pasada():
    """Un generador sólo se puede recorrer una vez: dos pasadas contarían cero."""
    lista = report.count_visits(_registro())
    flujo = report.count_visits(line for line in _registro())
    assert lista["visitors"] == 1
    assert flujo == lista


def test_la_marca_del_panel_vale_aunque_llegue_despues():
    r = report.count_visits(line for line in _registro())
    assert r["visitors"] == 1, "el operador contaba porque abrió el panel una hora después"
    assert r["views"] == 2


def test_web_visits_lee_journalctl_como_un_tubo(monkeypatch):
    """Ni `subprocess.run` ni `.stdout` entero: un proceso con su salida leída línea a línea."""
    texto = "\n".join(_registro()) + "\n"

    class Proceso:
        def __init__(self, cmd, **kw):
            assert kw.get("stdout") is not None, "la salida tiene que ser un tubo"
            self.stdout = io.StringIO(texto)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def wait(self, timeout=None):
            return 0

        def kill(self):
            pass

    def prohibido(*a, **kw):
        raise AssertionError("subprocess.run carga toda la salida en memoria")

    monkeypatch.setattr(report.subprocess, "Popen", Proceso)
    monkeypatch.setattr(report.subprocess, "run", prohibido)
    r = report.web_visits(0)
    assert r["visitors"] == 1
    assert r["views"] == 2
