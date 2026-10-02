"""Servidor MCP de PediBot (2-oct-2026).

Las herramientas son las ocho ofertas del agente de ACP, con sus esquemas de
`ops/acp_catalogue.json` y el mismo enrutado de `ops/acp_worker.py`: los dos canales no pueden
dar cifras distintas. Lo que se fija aquí:

1. Cada herramienta llega a SU endpoint o a ninguno. El enrutado del worker decide por los campos
   que trae el formulario; una dosis sin peso pero con país acababa en el calendario de vacunas.
2. Las dos herramientas que gastan modelo tienen un tope al día propio. El saldo de DeepSeek es
   uno solo: si MCP lo agota, quien se queda sin respuesta es un padre.
3. Lo que se apunta: hora, herramienta, cliente y si hubo dato. Ni IP ni argumentos.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import threading
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOGUE = json.loads((ROOT / "ops" / "acp_catalogue.json").read_text(encoding="utf-8"))


def _mod():
    spec = importlib.util.spec_from_file_location("mcp_server", ROOT / "ops" / "mcp_server.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    sys.modules["mcp_server"] = m
    spec.loader.exec_module(m)
    return m


class FakeAPI:
    """Lo que contestaría la API local; apunta a qué ruta se llamó."""

    def __init__(self, reply: dict | None = None):
        self.calls: list = []
        self.reply = reply if reply is not None else {"ok": True}

    def __call__(self, route):
        self.calls.append(route)
        return dict(self.reply)


def _server(tmp_path, api=None, **kw):
    m = _mod()
    return m, m.Server(serve=api or FakeAPI(), log=tmp_path / "mcp_uso.jsonl", **kw)


def _call(srv, name, args, ident=1, client=None, ip="1.2.3.4"):
    msg = {"jsonrpc": "2.0", "id": ident, "method": "tools/call",
           "params": {"name": name, "arguments": args}}
    return srv.handle(msg, client=client, ip=ip)


# ── las herramientas ─────────────────────────────────────────────────────────


def test_the_tools_are_the_acp_offerings(tmp_path):
    _, srv = _server(tmp_path)
    tools = {t["name"]: t for t in srv.tools}
    assert set(tools) == {o["name"] for o in CATALOGUE["offerings"]}
    for o in CATALOGUE["offerings"]:
        t = tools[o["name"]]
        assert t["description"].startswith(o["description"])
        assert t["inputSchema"]["type"] == "object"
        assert t["inputSchema"]["properties"] == o["requirements"]["properties"]
        assert t["annotations"]["readOnlyHint"] is True


def test_every_offering_has_its_endpoint():
    m = _mod()
    assert set(m.ENDPOINT) == {o["name"] for o in CATALOGUE["offerings"]}


def test_every_catalogue_example_reaches_its_own_endpoint(tmp_path):
    api = FakeAPI()
    m, srv = _server(tmp_path, api)
    for o in CATALOGUE["offerings"]:
        out = _call(srv, o["name"], o["example"])
        assert out["result"]["isError"] is False, o["name"]
        assert api.calls[-1].path.startswith(m.ENDPOINT[o["name"]]), o["name"]


def test_a_dose_without_weight_does_not_become_a_vaccine_schedule(tmp_path):
    api = FakeAPI()
    _, srv = _server(tmp_path, api)
    out = _call(srv, "child_medicine_dose", {"drug": "Calpol", "country": "GB"})
    assert out["result"]["isError"] is True
    assert "weight_kg" in out["result"]["content"][0]["text"]
    assert api.calls == []


def test_fields_from_another_tool_are_ignored(tmp_path):
    """Una pregunta colada en la dosis no la convierte en chat (que gasta modelo)."""
    api = FakeAPI()
    _, srv = _server(tmp_path, api)
    _call(srv, "child_medicine_dose", {"drug": "Calpol", "weight_kg": 14, "question": "hola"})
    assert api.calls[-1].path == "/api/dose"


def test_the_child_explanation_is_always_for_a_child(tmp_path):
    api = FakeAPI()
    _, srv = _server(tmp_path, api)
    _call(srv, "child_friendly_health_explanation", {"question": "why do I have a fever?"})
    assert api.calls[-1].payload["mode"] == "child"


def test_the_answer_carries_the_source_and_the_disclaimer(tmp_path):
    _, srv = _server(tmp_path, FakeAPI({"level": "routine"}))
    res = _call(srv, "oral_rehydration_plan", {"weight_kg": 12})["result"]
    assert res["structuredContent"]["level"] == "routine"
    assert "disclaimer" in res["structuredContent"]
    assert "https://pedibot.xyz" in res["content"][0]["text"]


def test_an_api_failure_is_a_tool_error_not_a_crash(tmp_path):
    m = _mod()
    srv = m.Server(serve=lambda r: None, log=tmp_path / "u.jsonl")
    res = _call(srv, "oral_rehydration_plan", {"weight_kg": 12})["result"]
    assert res["isError"] is True


# ── el tope del modelo ───────────────────────────────────────────────────────


def test_model_tools_stop_at_the_daily_cap(tmp_path):
    api = FakeAPI()
    _, srv = _server(tmp_path, api, model_per_day=2, model_per_ip_hour=99)
    q = {"question": "fever"}
    assert _call(srv, "paediatric_question_with_sources", q, ip="a")["result"]["isError"] is False
    assert _call(srv, "paediatric_question_with_sources", q, ip="b")["result"]["isError"] is False
    third = _call(srv, "paediatric_question_with_sources", q, ip="c")["result"]
    assert third["isError"] is True
    assert len(api.calls) == 2
    # las tablas fijas no gastan modelo: siguen contestando
    assert _call(srv, "oral_rehydration_plan", {"weight_kg": 12})["result"]["isError"] is False


def test_model_tools_are_limited_per_caller(tmp_path):
    _, srv = _server(tmp_path, model_per_day=100, model_per_ip_hour=1)
    q = {"question": "fever"}
    assert _call(srv, "paediatric_question_with_sources", q, ip="a")["result"]["isError"] is False
    assert _call(srv, "paediatric_question_with_sources", q, ip="a")["result"]["isError"] is True
    assert _call(srv, "paediatric_question_with_sources", q, ip="b")["result"]["isError"] is False


# ── lo que se apunta ─────────────────────────────────────────────────────────


def test_the_log_has_no_ip_and_no_arguments(tmp_path):
    _, srv = _server(tmp_path)
    _call(srv, "child_medicine_dose", {"drug": "Calpol", "weight_kg": 14},
          client="claude-ai", ip="9.9.9.9")
    rows = [json.loads(x) for x in (tmp_path / "mcp_uso.jsonl").read_text().splitlines()]
    assert rows[0]["tool"] == "child_medicine_dose"
    assert rows[0]["client"] == "claude-ai"
    assert rows[0]["no_data"] is False
    text = json.dumps(rows)
    assert "9.9.9.9" not in text and "Calpol" not in text


def test_usage_summary(tmp_path):
    m = _mod()
    log = tmp_path / "u.jsonl"
    log.write_text("\n".join(json.dumps(r) for r in [
        {"ts": "2026-10-02 10:00:00", "tool": "child_medicine_dose", "client": "a", "no_data": False},
        {"ts": "2026-10-02 11:00:00", "tool": "child_medicine_dose", "client": "b", "no_data": True},
        {"ts": "2026-10-01 11:00:00", "tool": "oral_rehydration_plan", "client": "a", "no_data": False},
    ]), encoding="utf-8")
    s = m.usage(log, ["2026-10-02"])
    assert s == {"calls": 2, "clients": 2, "no_data": 1, "by_tool": {"child_medicine_dose": 2}}


# ── el protocolo ─────────────────────────────────────────────────────────────


def test_initialize_negotiates_the_version(tmp_path):
    m, srv = _server(tmp_path)
    r = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18"}})["result"]
    assert r["protocolVersion"] == "2025-06-18"
    assert r["serverInfo"]["name"] == "pedibot"
    assert "not medical advice" in r["instructions"].lower()
    r = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "initialize",
                    "params": {"protocolVersion": "1999-01-01"}})["result"]
    assert r["protocolVersion"] == m.VERSIONS[0]


def test_unknown_tool_and_method(tmp_path):
    _, srv = _server(tmp_path)
    assert _call(srv, "nope", {})["error"]["code"] == -32602
    out = srv.handle({"jsonrpc": "2.0", "id": 3, "method": "foo/bar"})
    assert out["error"]["code"] == -32601
    assert srv.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_empty_lists_for_resources_and_prompts(tmp_path):
    _, srv = _server(tmp_path)
    r = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "prompts/list"})["result"]
    assert r == {"prompts": []}


def test_http_transport(tmp_path):
    m, srv = _server(tmp_path)
    httpd = m.serve_http(srv, port=0)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{port}/mcp"
        try:
            urllib.request.urlopen(url, timeout=5)
            raise AssertionError("GET should be 405")
        except urllib.error.HTTPError as e:
            assert e.code == 405
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert len(json.loads(resp.read())["result"]["tools"]) == 8
        note = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode()
        req = urllib.request.Request(url, data=note, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 202
    finally:
        httpd.shutdown()


# ── el despliegue y el registro ──────────────────────────────────────────────


def test_caddy_sends_mcp_to_the_server():
    caddy = (ROOT / "ops" / "Caddyfile").read_text(encoding="utf-8")
    assert "path /mcp" in caddy
    assert f"127.0.0.1:{_mod().PORT}" in caddy


def test_the_unit_is_installed_and_restarted():
    unit = ROOT / "ops" / "systemd" / "pedibot-mcp.service"
    assert "ops/mcp_server.py" in unit.read_text(encoding="utf-8")
    deploy = (ROOT / "ops" / "deploy.sh").read_text(encoding="utf-8")
    assert deploy.count("pedibot-mcp.service") >= 2  # enable y restart


def test_the_registry_file_points_here():
    sj = json.loads((ROOT / "ops" / "mcp" / "server.json").read_text(encoding="utf-8"))
    assert sj["name"] == "xyz.pedibot/pedibot"
    assert sj["remotes"][0]["url"] == "https://pedibot.xyz/mcp"
    assert len(sj["description"]) <= 100
    auth = ROOT / "web" / "site" / "public" / ".well-known" / "mcp-registry-auth"
    assert auth.read_text(encoding="utf-8").startswith("v=MCPv1; k=ed25519; p=")


# ── lo que puntúan los catálogos ─────────────────────────────────────────────
# Glama puntúa cada herramienta; en Regime (2-oct) flojeaban todas en lo mismo: no decían cuándo
# usarlas ni qué hermana usar en su lugar. La línea viaja sólo por MCP (ACP corta en 500).


def test_every_tool_says_when_to_use_it_and_names_a_sibling(tmp_path):
    m, srv = _server(tmp_path)
    assert set(m.USE_WHEN) == set(m.ENDPOINT)
    names = set(m.ENDPOINT)
    for t in srv.tools:
        line = m.USE_WHEN[t["name"]]
        assert line.startswith("Use when"), t["name"]
        assert line in t["description"]
        assert any(other in line for other in names - {t["name"]}), t["name"]


def test_the_glama_claim_is_valid_json():
    """Glama verifica el dominio leyendo /.well-known/glama.json (2-oct-2026). Si deja de ser
    JSON válido o se borra, se pierde la ficha verificada."""
    import re as _re

    p = ROOT / "web" / "site" / "public" / ".well-known" / "glama.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["$schema"] == "https://glama.ai/mcp/schemas/connector.json"
    assert _re.fullmatch(r"glama_claim_[A-Za-z0-9_-]{32}", data["claim"])
