"""En el panel no puede salir nada nuestro: ni visitas, ni consultas, ni votos (13-sep-2026).

El operador lo pidió así, «es importante», después de descubrir que las consultas que veía eran
mías. Lo que había ya filtraba algo, y se escapaba por cuatro sitios:

1. **Sus consultas desde el chat.** El chat manda `x-pedibot-client: web` a todo el mundo, así
   que el operador probando su propio producto contaba como un padre.
2. **Sus visitas desde otro dispositivo o con otra IP.** Se descartaba el navegador exacto
   (IP + agente) que había abierto /admin; su móvil, o su portátil al día siguiente con la IP
   cambiada, contaban.
3. **El navegador de la máquina de las pruebas.** Mis scripts ya se descartan por su agente
   (`curl`, `python`), pero un Chrome normal en la misma IP contaba.
4. **Mis sondas que imitaban al chat** (ids 356–358, 12-sep): etiquetadas `web`.

Cómo se reconoce lo nuestro sin romper lo que promete /legal —las respuestas se guardan «con un
identificador de sesión aleatorio, sin dirección IP»—:

- **Por navegador, para las consultas.** Abrir /admin deja una marca en el navegador. Con ella,
  el chat pregunta como `test`, y cada página avisa a `/api/team` con la sesión: lo que esa sesión
  ya hubiera preguntado como `web` pasa a ser nuestro. Sin IP en ninguna tabla.
- **Por dirección, para las visitas**, que salen del registro del servidor, que ya la tiene:
  toda la IP que abrió /admin o mandó tráfico `test` es nuestra una semana antes y una
  después. No para siempre: las IP domésticas cambian de manos.
- **Por id, lo de antes**, en `config/team.yaml`, sin tocar la base.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
import yaml

from pedibot.ops import report
from pedibot.settings import ROOT

CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140"
PHONE = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/140 Mobile"
DIA = 86_400.0
T0 = 1_789_000_000.0


def _linea(
    ip: str,
    ua: str,
    uri: str,
    ts: float = T0,
    status: int = 200,
    method: str = "GET",
    team: bool = False,
) -> str:
    headers = {"User-Agent": [ua]}
    if team:
        headers["X-Pedibot-Client"] = ["test"]
    return json.dumps(
        {
            "msg": "handled request",
            "ts": ts,
            "status": status,
            "request": {"remote_ip": ip, "method": method, "uri": uri, "headers": headers},
        }
    )


def _visita(ip: str, ua: str, ts: float) -> list[str]:
    return [_linea(ip, ua, "/es/dose", ts), _linea(ip, ua, "/_astro/index.js", ts + 1)]


# ── visitas ───────────────────────────────────────────────────────────────────────────────
def test_otro_dispositivo_en_la_ip_del_panel_no_es_una_visita():
    lineas = [_linea("5.5.5.5", CHROME, "/admin", T0)] + _visita("5.5.5.5", PHONE, T0 + 3600)
    assert report.count_visits(lineas)["visitors"] == 0, (
        "el móvil del operador, en su wifi, contaba"
    )


def test_los_dias_sin_panel_entre_dos_marcas_tambien_son_nuestros():
    """Medido en el registro real: el Chrome de casa se colaba los días sin panel cerca."""
    lineas = [
        _linea("5.5.5.5", CHROME, "/admin", T0),
        _linea("5.5.5.5", CHROME, "/admin", T0 + 9 * DIA),
    ]
    lineas += _visita("5.5.5.5", CHROME, T0 + 4 * DIA)
    assert report.count_visits(lineas)["visitors"] == 0


def test_la_ip_que_manda_trafico_de_prueba_no_es_una_visita():
    lineas = [_linea("6.6.6.6", "python-urllib/3.12", "/api/ask", T0, method="POST", team=True)]
    lineas += _visita("6.6.6.6", CHROME, T0 + 600)
    assert report.count_visits(lineas)["visitors"] == 0, (
        "el navegador de la máquina desde la que se lanzan las pruebas contaba de visita"
    )


def test_un_panel_sin_contrasena_no_marca_nada():
    """Los escáneres piden /admin a cientos y reciben un 401: no son el operador."""
    lineas = [_linea("7.7.7.7", CHROME, "/admin", T0, status=401)] + _visita(
        "7.7.7.7", CHROME, T0 + 60
    )
    assert report.count_visits(lineas)["visitors"] == 1


def test_la_marca_caduca_porque_las_ip_cambian_de_manos():
    lineas = [_linea("5.5.5.5", CHROME, "/admin", T0)] + _visita("5.5.5.5", PHONE, T0 + 10 * DIA)
    assert report.count_visits(lineas)["visitors"] == 1, (
        "diez días después esa IP puede ser de otro"
    )


def test_un_lector_de_verdad_sigue_contando():
    lineas = [_linea("5.5.5.5", CHROME, "/admin", T0)] + _visita("9.9.9.9", CHROME, T0 + 60)
    assert report.count_visits(lineas)["visitors"] == 1


# ── consultas: lo de antes, por id ────────────────────────────────────────────────────────
def test_las_sondas_del_12_sep_estan_declaradas():
    team = yaml.safe_load((ROOT / "config" / "team.yaml").read_text(encoding="utf-8"))
    assert {356, 357, 358} <= set(team["answer_ids"])


def test_el_filtro_de_lectores_deja_fuera_los_ids_declarados():
    from pedibot.ops.store import real_only

    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE answers (id INTEGER, ts TEXT, source TEXT)")
    con.executemany(
        "INSERT INTO answers VALUES (?,?,?)", [(1, "x", "web"), (356, "x", "web"), (2, "x", "test")]
    )
    n = con.execute(
        "SELECT COUNT(*) FROM answers WHERE ts>=?" + real_only({356}), ("",)
    ).fetchone()[0]
    assert n == 1


# ── consultas: por navegador ──────────────────────────────────────────────────────────────
@pytest.fixture
def cliente(tmp_path: Path):
    from fastapi.testclient import TestClient

    from pedibot.api import ApiConfig, create_app
    from pedibot.ops.store import AnswerRecord, OpsStore

    ops = OpsStore(tmp_path / "ops.db", salt="s")

    def fila(session: str, source: str) -> int:
        return ops.log_answer(
            AnswerRecord(
                session, "es", None, "q", "a", "routine", "ok", [], None, None, 0, 0, 0.0, 0, source
            )
        )

    ids = {"mia": fila("sess-operador", "web"), "otra": fila("sess-lector", "web")}

    class _Motor:  # /api/team no pregunta nada al motor
        retriever = None

    app = create_app(
        _Motor(),
        ops,
        ApiConfig(
            allowed_origins=["http://x"],
            rate_limit_per_10min=10,
            rate_limit_per_day=10,
            max_daily_llm_usd=1.0,
        ),
    )
    return TestClient(app), ops, ids


def test_la_marca_del_navegador_reetiqueta_su_sesion_y_solo_la_suya(cliente):
    c, ops, ids = cliente
    r = c.post("/api/team", json={"session": "sess-operador"}, headers={"x-pedibot-client": "test"})
    assert r.status_code == 204
    src = dict(ops.con.execute("SELECT id, source FROM answers").fetchall())
    assert src[ids["mia"]] == "test", (
        "lo que el operador preguntó desde su navegador sigue como lector"
    )
    assert src[ids["otra"]] == "web", "se ha reetiquetado la sesión de otro"


def test_sin_sesion_no_hace_nada(cliente):
    c, ops, _ = cliente
    assert c.post("/api/team", json={}).status_code == 204
    assert {s for (s,) in ops.con.execute("SELECT source FROM answers")} == {"web"}


# ── el sitio ──────────────────────────────────────────────────────────────────────────────
def test_el_panel_marca_el_navegador(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from pedibot import admin
    from pedibot.ops.store import OpsStore

    monkeypatch.setattr(report, "web_visits", lambda days: report.count_visits([]))
    html = admin.render(OpsStore(tmp_path / "ops.db", salt="s").con, 0)
    assert "localStorage.setItem('pedibot_team'" in html


def test_con_la_marca_el_chat_pregunta_como_prueba():
    chat = (ROOT / "web/site/src/components/Chat.astro").read_text(encoding="utf-8")
    assert "'x-pedibot-client': 'web'" not in chat, (
        "queda una llamada que se presenta siempre como lector"
    )
    assert "pedibot_team" in chat


def test_cada_pagina_avisa_con_la_marca():
    base = (ROOT / "web/site/src/layouts/Base.astro").read_text(encoding="utf-8")
    assert "pedibot_team" in base and "/api/team" in base
