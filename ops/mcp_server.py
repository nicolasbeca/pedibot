"""Servidor MCP de PediBot: las herramientas del agente, para cualquier asistente (2-oct-2026).

    uv run --no-dev python ops/mcp_server.py      # 127.0.0.1:8603, detrás de Caddy en /mcp

**Por qué existe.** Claude, ChatGPT, Cursor y otros asistentes se conectan a herramientas de
fuera por MCP (Model Context Protocol). Si alguien le pregunta a uno «¿cuántos ml de Dalsy para
12 kg?», el asistente nos llama, contesta con nuestra tabla y la cita. Es un escaparate donde el
enlace no lo ponemos nosotros. Decidido por el operador el 1-oct (IDEAS.md, «Registro oficial de
MCP»), copiando el camino que Regime abrió ese mismo día.

**No se escribe ninguna herramienta nueva.** Son las ocho ofertas del agente de ACP: los
esquemas salen de `ops/acp_catalogue.json` y el enrutado de `ops/acp_worker.py`, que llama a la
misma API local que la web. Si una oferta cambia, cambia la herramienta, y los dos canales no
pueden dar cifras distintas. Gratis y sin clave: es exposición, no cobro.

**Dos cosas que el worker no necesitaba y aquí sí:**
- Cada herramienta llega a SU endpoint o a ninguno (`ENDPOINT`). El worker decide por los campos
  del formulario, y un asistente manda lo que quiere: una dosis sin peso pero con país acababa
  en el calendario de vacunas, y una pregunta colada en cualquier herramienta, en el modelo.
- Las dos herramientas que gastan modelo tienen tope propio, al día y por quien llama. En ACP el
  comprador paga; aquí no, y el saldo de DeepSeek es uno solo: si MCP lo agota, quien se queda
  sin respuesta es un padre. Las tablas fijas (dosis, vacunas, curvas…) no tienen tope.

**El transporte** es el HTTP «streamable» del protocolo en su forma mínima, como en Regime: cada
POST lleva un mensaje JSON-RPC (o un lote) y se contesta con JSON; sin sesiones ni SSE. GET da
405, que es lo que la especificación manda a un servidor que no abre flujos.

**Lo que se apunta** por llamada (`data/mcp_uso.jsonl`): hora, herramienta, el nombre que el
cliente declara de sí mismo y si hubo dato. Ni IP ni argumentos: una pregunta sobre un niño no
se guarda dos veces. La IP sólo vive en memoria, para el tope por hora.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import sys
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def _load_worker() -> Any:
    """El worker de ACP, cargado por su ruta: en el servidor `ops/` no es un paquete."""
    if "acp_worker" in sys.modules:
        return sys.modules["acp_worker"]
    spec = importlib.util.spec_from_file_location("acp_worker", HERE / "acp_worker.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["acp_worker"] = mod
    spec.loader.exec_module(mod)
    return mod


acp_worker = _load_worker()

SITE = "https://pedibot.xyz"
PORT = int(os.environ.get("PEDIBOT_MCP_PORT") or 8603)
VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
"""Las versiones del protocolo que hablamos. Si el cliente pide otra, se le ofrece la primera y
decide él; así lo manda la especificación."""
SERVER_VERSION = "1.0.0"
MAX_BODY = 64 * 1024
EMPTY_LISTS = {
    "resources/list": "resources",
    "resources/templates/list": "resourceTemplates",
    "prompts/list": "prompts",
}

ENDPOINT = {
    "paediatric_question_with_sources": "/api/agent/ask",
    "child_friendly_health_explanation": "/api/agent/ask",
    "paediatric_warning_sign_check": "/api/triage",
    "child_growth_percentile": "/api/growth",
    "child_medicine_dose": "/api/dose",
    "childhood_vaccination_schedule": "/api/vaccines",
    "oral_rehydration_plan": "/api/ors",
    "paediatric_guide_finder": "/api/guides",
}
"""Adónde tiene que llegar cada herramienta. Si el enrutado del worker la manda a otro sitio, es
que faltan campos: se contesta con el error, no con otra cosa."""

MODEL_PATH = "/api/agent/ask"
MODEL_PER_DAY = int(os.environ.get("PEDIBOT_MCP_MODEL_PER_DAY") or 100)
MODEL_PER_IP_HOUR = int(os.environ.get("PEDIBOT_MCP_MODEL_PER_IP_HOUR") or 10)

INSTRUCTIONS = (
    "PediBot answers parents' questions about children's health only from published paediatric "
    "guidelines (WHO, NHS, CDC, national health ministries and paediatric societies), in eight "
    "languages. Doses, vaccination schedules, growth percentiles, rehydration volumes and "
    "warning signs come from fixed tables and rules, never from a language model. Each answer "
    "names its sources; please cite https://pedibot.xyz when you use one. If a tool returns "
    "level 'emergency', tell the user to call their emergency number now. "
    "Information only: not medical advice, not a diagnosis."
)
FOOTER = (
    f"\n\nSource: {SITE} (PediBot), from published paediatric guidelines. "
    "Not medical advice, not a diagnosis."
)


def offerings() -> list[dict[str, Any]]:
    data = json.loads((HERE / "acp_catalogue.json").read_text(encoding="utf-8"))
    return [o for o in data["offerings"] if o["name"] in ENDPOINT]


def _title(name: str) -> str:
    return name.replace("_", " ").capitalize()


def tools() -> list[dict[str, Any]]:
    out = []
    for o in offerings():
        out.append({
            "name": o["name"],
            "title": _title(o["name"]),
            "description": o["description"],
            "inputSchema": {**o["requirements"], "type": "object"},
            "outputSchema": {**o["deliverable"], "type": "object"},
            "annotations": {
                "title": _title(o["name"]),
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        })
    return out


def _error(ident: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": ident, "error": {"code": code, "message": message}}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Server:
    """El protocolo, sin HTTP: un mensaje entra, una respuesta (o nada) sale."""

    def __init__(
        self,
        *,
        serve: Callable[[Any], dict[str, Any] | None] | None = None,
        log: Path | None = None,
        model_per_day: int = MODEL_PER_DAY,
        model_per_ip_hour: int = MODEL_PER_IP_HOUR,
    ):
        self.serve = serve or (lambda r: acp_worker.serve(r))
        self.log = log
        self.model_per_day = model_per_day
        self.model_per_ip_hour = model_per_ip_hour
        self.tools = tools()
        self._schemas = {t["name"]: t["inputSchema"] for t in self.tools}
        self._lock = threading.Lock()
        self._day = _now().strftime("%Y-%m-%d")
        self._model_today = self._model_calls_logged(self._day)
        self._by_ip: dict[str, list[float]] = {}

    # ── el tope del modelo ──
    def _model_calls_logged(self, day: str) -> int:
        """Las del día que ya están en el registro: un reinicio (cada despliegue) no lo pone a 0."""
        if self.log is None or not self.log.exists():
            return 0
        n = 0
        for line in self.log.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if str(row.get("ts", ""))[:10] == day and ENDPOINT.get(row.get("tool")) == MODEL_PATH:
                n += 1
        return n

    def _model_allowed(self, ip: str | None) -> str | None:
        """None si puede; si no, el motivo para el asistente."""
        with self._lock:
            today = _now().strftime("%Y-%m-%d")
            if today != self._day:
                self._day, self._model_today = today, 0
            if self._model_today >= self.model_per_day:
                return (
                    "PediBot's free daily allowance for written answers is used up. The tools "
                    "that read fixed tables (doses, vaccines, growth, rehydration, warning signs, "
                    f"guides) still work, and the website answers at {SITE}."
                )
            key = ip or "?"
            t = time.monotonic()
            recent = [s for s in self._by_ip.get(key, []) if t - s < 3600]
            if len(recent) >= self.model_per_ip_hour:
                self._by_ip[key] = recent
                return f"Too many written answers from this caller in the last hour; try later or use {SITE}."
            recent.append(t)
            self._by_ip[key] = recent
            self._model_today += 1
            return None

    # ── lo que se apunta ──
    def _note(self, tool: str, client: str | None, no_data: bool, ms: int) -> None:
        if self.log is None:
            return
        row = {
            "ts": _now().strftime("%Y-%m-%d %H:%M:%S"),
            "tool": tool,
            "client": (client or "")[:60],
            "no_data": no_data,
            "ms": ms,
        }
        try:
            self.log.parent.mkdir(parents=True, exist_ok=True)
            with self.log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except OSError:
            pass  # apuntar nunca tumba una respuesta

    def _result(self, data: dict[str, Any] | None, message: str | None = None) -> dict[str, Any]:
        if data is None:
            return {"content": [{"type": "text", "text": message or "No answer."}], "isError": True}
        data.setdefault("disclaimer", acp_worker.DISCLAIMER)
        text = json.dumps(data, ensure_ascii=False, indent=1) + FOOTER
        return {"content": [{"type": "text", "text": text}], "structuredContent": data,
                "isError": False}

    def _call(self, params: Any, client: str | None, ip: str | None) -> dict[str, Any] | tuple[int, str]:
        if not isinstance(params, dict):
            return (-32602, "params must be an object")
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in self._schemas:
            return (-32602, f"unknown tool: {name}")
        if not isinstance(args, dict):
            return (-32602, "arguments must be an object")
        schema = self._schemas[name]
        # sólo los campos de ESTA herramienta: lo demás no puede desviarla a otro endpoint
        form = {k: v for k, v in args.items() if k in schema.get("properties", {})}
        if name == "child_friendly_health_explanation":
            form["mode"] = "child"
        t0 = time.monotonic()
        r = acp_worker.route(form)
        if r is None or not r.path.startswith(ENDPOINT[name]):
            need = ", ".join(schema.get("required", []))
            out = self._result(None, f"Missing or invalid fields for {name}. Required: {need}.")
        else:
            refusal = self._model_allowed(ip) if ENDPOINT[name] == MODEL_PATH else None
            if refusal:
                out = self._result(None, refusal)
            else:
                got = self.serve(r)
                out = self._result(
                    got if isinstance(got, dict) else None,
                    f"PediBot could not answer right now; the website is at {SITE}.",
                )
        self._note(name, client, out["isError"], int((time.monotonic() - t0) * 1000))
        return out

    def handle(self, msg: Any, *, client: str | None = None, ip: str | None = None) -> dict[str, Any] | None:
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
            return _error(msg.get("id") if isinstance(msg, dict) else None, -32600, "invalid request")
        ident, method, params = msg.get("id"), msg["method"], msg.get("params")
        notification = "id" not in msg
        if method.startswith("notifications/"):
            return None
        if method == "initialize":
            asked = params.get("protocolVersion") if isinstance(params, dict) else None
            res: dict[str, Any] = {
                "protocolVersion": asked if asked in VERSIONS else VERSIONS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "pedibot", "title": "PediBot",
                               "version": SERVER_VERSION, "websiteUrl": SITE},
                "instructions": INSTRUCTIONS,
            }
        elif method == "ping":
            res = {}
        elif method == "tools/list":
            res = {"tools": self.tools}
        elif method in EMPTY_LISTS:
            # sin recursos ni prompts; algunos clientes los piden igual y un «method not
            # found» les sale como aviso (Regime, Smithery, 1-oct)
            res = {EMPTY_LISTS[method]: []}
        elif method == "tools/call":
            r = self._call(params, client, ip)
            if isinstance(r, tuple):
                return None if notification else _error(ident, *r)
            res = r
        else:
            return None if notification else _error(ident, -32601, f"method not found: {method}")
        return None if notification else {"jsonrpc": "2.0", "id": ident, "result": res}


def _client_of(msgs: list[Any]) -> str | None:
    for m in msgs:
        if isinstance(m, dict) and m.get("method") == "initialize":
            info = (m.get("params") or {}).get("clientInfo") or {}
            return str(info.get("name") or "") or None
    return None


def serve_http(srv: Server, host: str = "127.0.0.1", port: int = PORT) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        server_version = "pedibot-mcp"
        sys_version = ""

        def log_message(self, *_a: Any) -> None:  # sin IPs en el journal
            pass

        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers",
                             "Content-Type, Accept, Mcp-Protocol-Version, Mcp-Session-Id")

        def _send(self, code: int, body: Any = None) -> None:
            data = b"" if body is None else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self._cors()
            if body is not None:
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send(204)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?")[0] != "/mcp":
                self._send(404, {"error": "not found"})
                return
            self.send_response(405)
            self.send_header("Allow", "POST")
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_DELETE = do_GET  # noqa: N815 — sin sesiones que cerrar

        def do_POST(self) -> None:  # noqa: N802
            if self.path.split("?")[0] != "/mcp":
                self._send(404, {"error": "not found"})
                return
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                # se lee (hasta un tope) antes de contestar: si no, el cliente ve la conexión
                # cortada en vez del 413
                if n <= 16 * MAX_BODY:
                    self.rfile.read(n)
                self._send(413, _error(None, -32600, "request too large"))
                return
            try:
                body = json.loads(self.rfile.read(n) or b"null")
            except ValueError:
                self._send(400, _error(None, -32700, "parse error"))
                return
            batch = isinstance(body, list)
            msgs = body if batch else [body]
            if batch and not msgs:
                self._send(400, _error(None, -32600, "empty batch"))
                return
            client = _client_of(msgs) or self.headers.get("User-Agent", "")[:60] or None
            # Caddy pone la IP real delante; sólo se usa en memoria para el tope por hora
            ip = (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
            replies = [r for r in (srv.handle(m, client=client, ip=ip) for m in msgs) if r is not None]
            if not replies:
                self._send(202)
            else:
                self._send(200, replies if batch else replies[0])

    return ThreadingHTTPServer((host, port), Handler)


def usage(log: Path | str, days: list[str]) -> dict[str, Any]:
    """Cuántas llamadas hubo esos días (`AAAA-MM-DD`), de cuántos clientes, cuántas sin dato y
    por herramienta. Es la medida que decide si el canal sirve."""
    rows = []
    try:
        for line in Path(log).read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if str(row.get("ts", ""))[:10] in days:
                rows.append(row)
    except OSError:
        pass
    by_tool: dict[str, int] = {}
    for row in rows:
        by_tool[row.get("tool", "?")] = by_tool.get(row.get("tool", "?"), 0) + 1
    return {
        "calls": len(rows),
        "clients": len({row.get("client") or "?" for row in rows}),
        "no_data": sum(1 for row in rows if row.get("no_data")),
        "by_tool": by_tool,
    }


def main() -> int:
    log = Path(os.environ.get("PEDIBOT_MCP_LOG") or ROOT / "data" / "mcp_uso.jsonl")
    httpd = serve_http(Server(log=log))
    print(f"MCP en 127.0.0.1:{PORT}/mcp, {len(tools())} herramientas", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
