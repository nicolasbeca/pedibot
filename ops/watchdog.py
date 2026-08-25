"""PediBot watchdog: API health, DeepSeek balance, disk, daily LLM cost → Telegram (push only on problems).

Runs every 10 min from pedibot-watchdog.timer. State in data/watchdog_state.json avoids repeating
the same alert more than once every 6 hours; a recovery message is sent when a problem clears.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shutil
import sys

import httpx

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "watchdog_state.json"
API = os.environ.get("PEDIBOT_API", "http://127.0.0.1:8601")
BALANCE_WARN_PCT = float(os.environ.get("BALANCE_WARN_PCT", "20"))
BALANCE_INITIAL_USD = float(os.environ.get("BALANCE_INITIAL_USD", "10"))
DAILY_COST_WARN_USD = float(os.environ.get("MAX_DAILY_LLM_USD", "2"))
DISK_WARN_PCT = 85


def telegram(text: str) -> None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("telegram not configured:", text)
        return
    try:
        httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat, "text": text}, timeout=15)
    except Exception as e:  # noqa: BLE001
        print("telegram failed:", e, file=sys.stderr)


def main() -> int:
    problems: dict[str, str] = {}
    # 1. API health
    try:
        r = httpx.get(f"{API}/api/health", timeout=10)
        r.raise_for_status()
        h = r.json()
        if float(h.get("cost_today_usd", 0)) >= DAILY_COST_WARN_USD:
            problems["daily_cost"] = f"⚠️ Coste LLM de hoy {h['cost_today_usd']} USD ≥ tope {DAILY_COST_WARN_USD} → modo degradado activo"
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
                problems["balance"] = f"🚨 Saldo DeepSeek bajo: {total:.2f} USD ({pct:.0f}% de {BALANCE_INITIAL_USD}). Recarga en platform.deepseek.com"
    except Exception as e:  # noqa: BLE001
        problems["balance_check"] = f"⚠️ No se pudo consultar el saldo de DeepSeek: {e}"
    # 3. disk
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
