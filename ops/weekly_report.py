"""Weekly report → operator's Telegram (Sunday 08:00 Madrid). Short by design.

Sections: web visits (Caddy access log in journald), questions (ops DB: web + Telegram, alarms,
👍/👎, cost), token (sum of daily Dexscreener snapshots), guides published, DeepSeek balance.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys

import httpx

from pedibot.settings import ROOT, get_settings

_STATIC = re.compile(r"\.(xml|svg|png|ico|css|js|txt|woff2?)$|^/_astro/|^/api/|^/a/", re.I)


def web_visits(days: int = 7) -> dict[str, int]:
    """Page views and unique visitors (hashed IP+UA, daily salt) from Caddy's JSON access log."""
    try:
        out = subprocess.run(
            ["journalctl", "-u", "caddy", "--since", f"-{days}d", "-o", "cat", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=120,
        ).stdout
    except Exception as e:  # noqa: BLE001
        print("journalctl failed:", e, file=sys.stderr)
        return {"views": 0, "visitors": 0, "chat_pageviews": 0}
    views, chat = 0, 0
    visitors: set[str] = set()
    for line in out.splitlines():
        if '"handled request"' not in line:
            continue
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue
        req = j.get("request", {})
        uri, status = req.get("uri", ""), j.get("status", 0)
        if status != 200 or _STATIC.search(uri) or req.get("method") != "GET":
            continue
        ua = (req.get("headers", {}).get("User-Agent") or [""])[0]
        if re.search(r"bot|crawl|spider|curl|python|monitor", ua, re.I):
            continue
        views += 1
        if uri in ("/", "/es", "/es/"):
            chat += 1
        visitors.add(hashlib.sha256(f"{req.get('remote_ip')}|{ua}".encode()).hexdigest()[:16])
    return {"views": views, "visitors": len(visitors), "chat_pageviews": chat}


def questions(con: sqlite3.Connection, days: int = 7) -> dict[str, object]:
    since = (dt.datetime.now(dt.UTC) - dt.timedelta(days=days)).isoformat(timespec="seconds")
    q = con.execute
    total = q("SELECT COUNT(*) FROM answers WHERE ts>=?", (since,)).fetchone()[0]
    tg = q("SELECT COUNT(*) FROM answers WHERE ts>=? AND session LIKE 'tg_%'", (since,)).fetchone()[
        0
    ]
    alarms = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=? AND level<>'routine'", (since,)
    ).fetchone()[0]
    nosrc = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=? AND verification IN ('no_source','fallback')",
        (since,),
    ).fetchone()[0]
    up = q("SELECT COUNT(*) FROM answers WHERE ts>=? AND feedback=1", (since,)).fetchone()[0]
    down = q("SELECT COUNT(*) FROM answers WHERE ts>=? AND feedback=-1", (since,)).fetchone()[0]
    cost = q("SELECT COALESCE(SUM(cost_usd),0) FROM answers WHERE ts>=?", (since,)).fetchone()[0]
    langs = dict(
        q("SELECT lang, COUNT(*) FROM answers WHERE ts>=? GROUP BY 1", (since,)).fetchall()
    )
    return {
        "total": total,
        "telegram": tg,
        "web": total - tg,
        "alarms": alarms,
        "no_source": nosrc,
        "up": up,
        "down": down,
        "cost": float(cost),
        "langs": langs,
    }


def token(con: sqlite3.Connection, days: int = 7) -> dict[str, object] | None:
    try:
        rows = con.execute(
            "SELECT day, price_usd, fdv_usd, volume_24h_usd, buys_24h, sells_24h FROM token_daily ORDER BY day DESC LIMIT ?",
            (days,),
        ).fetchall()
    except sqlite3.OperationalError:
        return None
    if not rows:
        return None
    return {
        "days": len(rows),
        "price": rows[0][1],
        "fdv": rows[0][2],
        "volume": sum(r[3] for r in rows),
        "buys": sum(r[4] for r in rows),
        "sells": sum(r[5] for r in rows),
        "price_change_pct": (rows[0][1] / rows[-1][1] - 1) * 100 if rows[-1][1] else 0.0,
    }


def guides(days: int = 7) -> int:
    n = 0
    since = dt.date.today() - dt.timedelta(days=days)
    for f in (ROOT / "web" / "content").rglob("*.md"):
        m = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", f.read_text(encoding="utf-8"), re.M)
        if m and dt.date.fromisoformat(m.group(1)) >= since:
            n += 1
    return n


def balance() -> float | None:
    try:
        from pedibot.bot.llm import deepseek_balance

        s = get_settings()
        b = deepseek_balance(s.deepseek_api_key, s.deepseek_base_url)
        t = b.get("total_usd")
        return float(t) if isinstance(t, (int, float)) else None
    except Exception:  # noqa: BLE001
        return None


def build(con: sqlite3.Connection) -> str:
    w, qn, tk, g, bal = web_visits(), questions(con), token(con), guides(), balance()
    end = dt.date.today()
    start = end - dt.timedelta(days=7)
    lines = [f"📊 PediBot · semana {start.strftime('%d %b')} – {end.strftime('%d %b')}", ""]
    lines.append(
        f"🌐 Web: {w['views']} páginas vistas · {w['visitors']} visitantes · {w['chat_pageviews']} en el chat"
    )
    fb = f" · 👍 {qn['up']} / 👎 {qn['down']}" if (qn["up"] or qn["down"]) else ""
    langs = " · ".join(f"{k} {v}" for k, v in sorted(qn["langs"].items())) if qn["langs"] else ""
    lines.append(f"💬 Consultas: {qn['total']} (web {qn['web']}, Telegram {qn['telegram']}){fb}")
    if langs:
        lines.append(
            f"   idiomas: {langs} · alarmas: {qn['alarms']} · sin fuente: {qn['no_source']}"
        )
    lines.append(
        f"🤖 Coste IA: {qn['cost']:.3f} $"
        + (f" · saldo DeepSeek {bal:.2f} $" if bal is not None else "")
    )
    if tk:
        lines.append(
            f"🪙 PDBT ({tk['days']} d): {tk['buys']} compras / {tk['sells']} ventas · volumen {tk['volume']:.0f} $ · precio {tk['price']:.7f} $ ({tk['price_change_pct']:+.1f} %) · FDV {tk['fdv']:.0f} $"
        )
    else:
        lines.append("🪙 PDBT: sin datos aún (la foto diaria empieza hoy)")
    lines.append(f"📝 Guías publicadas: {g}")
    if bal is not None and bal < 2:
        lines.append("⚠️ Saldo DeepSeek bajo: recarga en platform.deepseek.com")
    return "\n".join(lines)


def send(text: str) -> bool:
    token_, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token_ or not chat:
        print(text)
        return False
    r = httpx.post(
        f"https://api.telegram.org/bot{token_}/sendMessage",
        json={"chat_id": chat, "text": text},
        timeout=20,
    )
    return r.status_code == 200


def main() -> int:
    s = get_settings()
    con = sqlite3.connect(s.ops_db_path)
    text = build(con)
    print(text)
    send(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
