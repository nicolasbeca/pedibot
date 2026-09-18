"""PediBot watchdog: API health, DeepSeek balance, disk, daily LLM cost, averías del modelo
→ Telegram (push only on problems).

Runs every 10 min from pedibot-watchdog.timer. State in data/watchdog_state.json avoids repeating
the same alert more than once every 6 hours; a recovery message is sent when a problem clears.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from typing import Any

import httpx

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "watchdog_state.json"
API = os.environ.get("PEDIBOT_API", "http://127.0.0.1:8601")
BALANCE_WARN_PCT = float(os.environ.get("BALANCE_WARN_PCT", "20"))
BALANCE_INITIAL_USD = float(os.environ.get("BALANCE_INITIAL_USD", "10"))
DAILY_COST_WARN_USD = float(os.environ.get("MAX_DAILY_LLM_USD", "2"))
DISK_WARN_PCT = 85
#: Respuestas dadas sin modelo por avería en la última hora antes de avisar. Una suelta puede ser
#: un hipo de red; varias seguidas es DeepSeek caído, y ahí hay que enterarse sin abrir el panel.
NO_MODEL_WARN = int(os.environ.get("NO_MODEL_WARN", "3"))
OPS_DB = ROOT / "data" / "pedibot_ops.db"
UNITS = ("pedibot-api", "pedibot-telegram", "pedibot-acp", "caddy")


def unit_status(name: str) -> str:
    """`systemctl is-active <unit>`; anything we cannot read counts as not running."""
    try:
        out = subprocess.run(
            ["systemctl", "is-active", name], capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


#: Cuánto se espera antes de mirar por segunda vez una unidad que parece caída.
REINTENTO_S = float(os.environ.get("WATCHDOG_RETRY_S", "8"))


def dead_units(
    status_of=unit_status, units: tuple[str, ...] = UNITS, dormir=time.sleep
) -> list[str]:
    """Units that are not `active`, looked at TWICE. Pure enough to test without systemd.

    18-sep-2026. El vigilante mandó «🚨 Servicios parados: pedibot-telegram, pedibot-acp» y no
    había nada parado: el despliegue los estaba reiniciando en ese mismo segundo. Los tiempos,
    del journal:

        13:21:14  arranca el vigilante
        13:21:16  el despliegue reinicia las tres unidades
        13:21:17  el vigilante las mira y las ve caídas

    Corre cada diez minutos y el reinicio dura dos segundos, así que la ventana es estrecha —y
    aun así la encontró—. Un aviso que salta por un despliegue enseña al operador a ignorar el
    aviso, que es la mitad cara de la lección de los falsos positivos del triaje: el rojo que no
    significa nada acaba no significando nada el día que sí.

    Mirar dos veces separa las dos cosas sin inventarse nada: un reinicio está arriba ocho
    segundos después y un servicio muerto sigue muerto. No se pregunta si hay un despliegue en
    marcha —eso sería fiarse de una bandera que alguien tiene que acordarse de poner— sino que
    se vuelve a mirar el hecho.
    """
    sospechosas = [u for u in units if status_of(u) != "active"]
    if not sospechosas:
        return []
    dormir(REINTENTO_S)
    return [u for u in sospechosas if status_of(u) != "active"]


def telegram(text: str) -> None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("telegram not configured:", text)
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text},
            timeout=15,
        )
    except Exception as e:  # noqa: BLE001
        print("telegram failed:", e, file=sys.stderr)


def outages_last_hour(db: pathlib.Path, now: dt.datetime | None = None) -> int:
    """Respuestas de la última hora dadas sin modelo **por avería** (`no_model`).

    No cuenta las `degraded`: esas son el tope de gasto, que decidimos nosotros y ya tiene su
    propio aviso. Se abre en solo lectura para no tocar nunca la base que usa el API.
    """
    import sqlite3

    ahora = now or dt.datetime.now(dt.UTC)
    desde = (ahora - dt.timedelta(hours=1)).isoformat(timespec="seconds")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return int(
            con.execute(
                "SELECT COUNT(*) FROM answers WHERE ts>=? AND verification='no_model'", (desde,)
            ).fetchone()[0]
        )
    finally:
        con.close()


#: Cuántas líneas de Caddy hay que ver en dos horas para dar el registro por vivo. Medido el
#: 7-sep-2026 en un rato tranquilo: 403. Cinco es un suelo muy por debajo de cualquier hora real,
#: para que el aviso signifique «esto está mudo» y no «hoy hubo poca gente».
ACCESS_LOG_MIN = 5


def access_log_lines(desde: str = "-2 hours", correr: Any = None) -> int:
    """Líneas que Caddy ha escrito en el journal. Es de donde el panel saca las visitas."""
    ejecutar = correr or subprocess.run
    r = ejecutar(
        ["journalctl", "-u", "caddy", "--since", desde, "-o", "cat", "--no-pager"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return len([x for x in (r.stdout or "").splitlines() if x.strip()])


def main() -> int:
    problems: dict[str, str] = {}
    # 1. API health
    try:
        r = httpx.get(f"{API}/api/health", timeout=10)
        r.raise_for_status()
        h = r.json()
        if float(h.get("cost_today_usd", 0)) >= DAILY_COST_WARN_USD:
            problems["daily_cost"] = (
                f"⚠️ Coste LLM de hoy {h['cost_today_usd']} USD ≥ tope {DAILY_COST_WARN_USD} → modo degradado activo"
            )
    except Exception as e:  # noqa: BLE001
        problems["api_down"] = f"🚨 PediBot API no responde: {e}"
    # 2. DeepSeek balance
    try:
        from pedibot.bot.llm import deepseek_balance
        from pedibot.settings import get_settings

        s = get_settings()
        b = deepseek_balance(s.deepseek_api_key, s.deepseek_base_url)
        total = b.get("total_usd")
        if isinstance(total, (int, float)):
            pct = 100 * float(total) / BALANCE_INITIAL_USD if BALANCE_INITIAL_USD else 100
            if pct < BALANCE_WARN_PCT or float(total) < 1.0:
                problems["balance"] = (
                    f"🚨 Saldo DeepSeek bajo: {total:.2f} USD ({pct:.0f}% de {BALANCE_INITIAL_USD}). Recarga en platform.deepseek.com"
                )
    except Exception as e:  # noqa: BLE001
        problems["balance_check"] = f"⚠️ No se pudo consultar el saldo de DeepSeek: {e}"
    # 3. our own services (a dead telegram or acp worker is silent otherwise)
    dead = dead_units()
    if dead:
        problems["units"] = (
            f"🚨 Servicios parados: {', '.join(dead)}. Arranca con: systemctl restart {dead[0]}"
        )
    # 4. el modelo falló y contestamos sin él
    #
    # Desde el 7-sep-2026 una avería de DeepSeek ya no tumba la respuesta: se contesta con los
    # pasajes de las guías y el triaje entero. Eso es bueno para el que pregunta y peligroso para
    # nosotros — un fallo que no se nota es un fallo que dura semanas. Por eso se cuenta aquí.
    try:
        n = outages_last_hour(OPS_DB)
        if n >= NO_MODEL_WARN:
            problems["no_model"] = (
                f"🚨 El modelo no contesta: {n} respuestas en la última hora se han dado sin él "
                "(llevan las guías y la alarma, pero sin redactar). Mira el saldo y el estado de "
                "DeepSeek."
            )
    except Exception as e:  # noqa: BLE001
        problems["no_model_check"] = f"⚠️ No se pudieron contar las averías del modelo: {e}"

    # 4b. una consulta de verdad, por el camino de verdad
    #
    # Todo lo de arriba vigila NUESTRA infraestructura: el proceso, el saldo, las unidades, el
    # disco. Ninguna de esas preguntas es la que importa —si una consulta funciona— y la
    # diferencia costó cara el 8-sep-2026: un «112» sin comillas en synonyms.yaml tuvo el
    # buscador devolviendo un 500 en inglés con /api/health en verde todo el tiempo, porque el
    # proceso estaba perfectamente en pie.
    #
    # Va con el modelo desconectado, así que no cuesta nada y puede correr cada diez minutos.
    try:
        from pedibot.ops.selfcheck import revisa
        from pedibot.settings import get_settings

        s_ = get_settings()
        fallos = revisa(s_.index_db_path, s_.config_dir)
        if fallos:
            problems["buscador"] = chr(10).join(fallos[:4])
    except Exception as e:  # noqa: BLE001
        problems["buscador_check"] = f"⚠️ No se pudo revisar el buscador: {e}"

    # 5. el registro del que vive el panel
    #
    # Las visitas del panel salen de `journalctl -u caddy`. Si Caddy dejara de escribir ahí, el
    # panel enseñaría CERO visitas — y cero visitas no parece una avería, parece que no vino
    # nadie. Es la L31 otra vez: el silencio que no se distingue de la ausencia, y en el único
    # sitio con el que se decide si esto funciona.
    try:
        lineas = access_log_lines()
        if lineas < ACCESS_LOG_MIN:
            problems["access_log"] = (
                "🚨 El registro de accesos está mudo: "
                f"{lineas} líneas de Caddy en dos horas. El panel cuenta las visitas desde "
                "ahí, así que estaría enseñando cero sin que nadie viera un error. "
                "Comprueba el bloque `log` del Caddyfile y `systemctl status systemd-journald`."
            )
    except Exception as e:  # noqa: BLE001
        problems["access_log_check"] = f"⚠️ No se pudo comprobar el registro de accesos: {e}"

    # 6. disk
    du = shutil.disk_usage("/")
    used_pct = 100 * (du.total - du.free) / du.total
    if used_pct > DISK_WARN_PCT:
        problems["disk"] = f"⚠️ Disco al {used_pct:.0f}%"

    # de-dup + recovery
    prev = json.loads(STATE.read_text()) if STATE.exists() else {}
    now = dt.datetime.now(dt.UTC)
    nxt: dict[str, str] = {}
    for k, msg in problems.items():
        last = prev.get(k)
        if not last or (now - dt.datetime.fromisoformat(last)).total_seconds() > 6 * 3600:
            telegram(f"PediBot · {msg}")
            nxt[k] = now.isoformat()
        else:
            nxt[k] = last
    for k in prev:
        if k not in problems:
            telegram(f"PediBot · ✅ resuelto: {k}")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(nxt))
    print(json.dumps({"problems": list(problems), "disk_pct": round(used_pct, 1)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
