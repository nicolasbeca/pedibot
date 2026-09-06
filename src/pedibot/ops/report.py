"""Metrics shared by the weekly Telegram report and the /admin panel (operator-only)."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from typing import Any

from pedibot.ops.store import NOT_REAL, REAL_ONLY
from pedibot.settings import ROOT

_STATIC = re.compile(
    r"\.(xml|svg|png|ico|css|js|txt|woff2?|webmanifest)$|^/_astro/|^/api/|^/a/|^/admin", re.I
)
_BOT_UA = re.compile(r"bot|crawl|spider|curl|python|monitor|wget|httpx", re.I)


def _who(ip: object, ua: str) -> str:
    """A visitor, as the panel has always counted one: address and browser together, hashed. The
    hash is computed to be compared with other hashes and is never written anywhere."""
    return hashlib.sha256(f"{ip}|{ua}".encode()).hexdigest()[:16]


def _operator_hashes(lines: list[str]) -> set[str]:
    """Whoever OPENED /admin. Caddy guards it with a password, so that is the operator.

    Opened, not asked for: 65 different browsers have requested /admin on this server and 64 of
    them are scanners hunting for an admin panel, which Caddy answered with a 401. Taking the
    request alone as proof would have quietly deleted them from the visit count — flattering,
    and false in the same direction the rest of this change exists to prevent.
    """
    out: set[str] = set()
    for line in lines:
        if "/admin" not in line or '"handled request"' not in line:
            continue
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue
        req = j.get("request", {})
        if j.get("status") != 200 or not str(req.get("uri", "")).startswith("/admin"):
            continue
        out.add(_who(req.get("remote_ip"), (req.get("headers", {}).get("User-Agent") or [""])[0]))
    return out


def web_visits(days: int = 7) -> dict[str, Any]:
    """Page views, unique visitors (hash of IP+UA) and top pages from Caddy's JSON access log.

    `days <= 0` means "as much as there is". It is NOT all-time and must never be shown as such:
    the journal rotates, and this one was capped after it grew to 4 GB. The returned `covers`
    says which days were actually seen, so the panel can label the number with its own period.
    A year is the ceiling either way — beyond that the read costs more than the answer is worth.
    """
    since = f"-{days}d" if days > 0 else "-365d"
    try:
        out = subprocess.run(
            ["journalctl", "-u", "caddy", "--since", since, "-o", "cat", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=120,
        ).stdout
    except Exception as e:  # noqa: BLE001
        print("journalctl failed:", e, file=sys.stderr)
        return {
            "views": 0, "visitors": 0, "returning": 0, "chat_pageviews": 0,
            "top": [], "per_day": {}, "covers": (),
        }
    lines = out.splitlines()
    # who the operator is, before counting anybody: the panel is password-protected, so a browser
    # that asked for /admin is his. Costs one extra pass over the journal and no configuration.
    ours = _operator_hashes(lines)
    views, chat = 0, 0
    visitors: set[str] = set()
    # how many pages each one asked for: one page and gone is a crawler, whatever its user agent
    # says. 600 of 919 browser-labelled addresses did exactly that, and 1.505 of their hits were
    # the home page.
    pages_each: dict[str, int] = {}
    top: dict[str, int] = {}
    per_day: dict[str, int] = {}
    for line in lines:
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
        if _BOT_UA.search(ua):
            continue
        who = _who(req.get("remote_ip"), ua)
        if who in ours:
            # the operator looking at his own site is not a visit, and at this traffic one person
            # opening it twice a day would be most of the number he is looking at
            continue
        views += 1
        uri = uri.split("?")[0]
        if uri in ("/", "/es", "/es/"):
            chat += 1
        top[uri] = top.get(uri, 0) + 1
        day = dt.datetime.fromtimestamp(float(j.get("ts", 0)), dt.UTC).date().isoformat()
        per_day[day] = per_day.get(day, 0) + 1
        visitors.add(who)
        pages_each[who] = pages_each.get(who, 0) + 1
    return {
        "views": views,
        "visitors": len(visitors),
        "returning": sum(1 for n in pages_each.values() if n > 1),
        "chat_pageviews": chat,
        "top": sorted(top.items(), key=lambda kv: -kv[1])[:10],
        "per_day": dict(sorted(per_day.items())),
        # what the journal actually held, so the panel never calls a rotated log a total
        "covers": (min(per_day), max(per_day)) if per_day else (),
    }


def questions(con: sqlite3.Connection, days: int = 7, include_test: bool = False) -> dict[str, Any]:
    """`days <= 0` counts everything: these rows live in the ops database and nothing deletes
    them, so unlike the visits this really is every question ever asked. Every ISO timestamp
    sorts after the empty string, which is why "everything" needs no separate query.

    Readers only, unless `include_test`. Our own test traffic is real work against a real engine
    and it belongs in the database, but it is not somebody asking about their child, and every
    number on this panel is read as if it were. `test` counts them so the operator can see how
    much of the day was us; `cost` is money and always counts every question, ours included.
    """
    since = (
        (dt.datetime.now(dt.UTC) - dt.timedelta(days=days)).isoformat(timespec="seconds")
        if days > 0
        else ""
    )
    only = "" if include_test else REAL_ONLY
    q = con.execute
    total = q("SELECT COUNT(*) FROM answers WHERE ts>=?" + only, (since,)).fetchone()[0]
    tg = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=?" + only + " AND source='telegram'", (since,)
    ).fetchone()[0]
    ours = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=?" + NOT_REAL, (since,)
    ).fetchone()[0]
    alarms = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=?" + only + " AND level<>'routine'", (since,)
    ).fetchone()[0]
    nosrc = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=?"
        + only
        + " AND verification IN ('no_source','fallback')",
        (since,),
    ).fetchone()[0]
    up = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=?" + only + " AND feedback=1", (since,)
    ).fetchone()[0]
    down = q(
        "SELECT COUNT(*) FROM answers WHERE ts>=?" + only + " AND feedback=-1", (since,)
    ).fetchone()[0]
    # money is never filtered: a test question is charged exactly like a real one
    cost = q("SELECT COALESCE(SUM(cost_usd),0) FROM answers WHERE ts>=?", (since,)).fetchone()[0]
    langs = dict(
        q(
            "SELECT lang, COUNT(*) FROM answers WHERE ts>=?" + only + " GROUP BY 1", (since,)
        ).fetchall()
    )
    levels = dict(
        q(
            "SELECT level, COUNT(*) FROM answers WHERE ts>=?" + only + " GROUP BY 1", (since,)
        ).fetchall()
    )
    per_day = dict(
        q(
            "SELECT substr(ts,1,10), COUNT(*) FROM answers WHERE ts>=?"
            + only
            + " GROUP BY 1 ORDER BY 1",
            (since,),
        ).fetchall()
    )
    first = q(
        "SELECT MIN(substr(ts,1,10)) FROM answers WHERE ts>=?" + only, (since,)
    ).fetchone()[0]
    return {
        "first_day": first,
        "total": total,
        "telegram": tg,
        "web": total - tg,
        "test": ours,
        "alarms": alarms,
        "no_source": nosrc,
        "up": up,
        "down": down,
        "cost": float(cost),
        "langs": langs,
        "levels": levels,
        "per_day": per_day,
    }


def token(con: sqlite3.Connection, days: int = 7) -> dict[str, Any] | None:
    try:
        rows = con.execute(
            "SELECT day, price_usd, fdv_usd, volume_24h_usd, buys_24h, sells_24h, liquidity_usd FROM token_daily ORDER BY day DESC LIMIT ?",
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
        "liquidity": rows[0][6],
        "volume": sum(r[3] for r in rows),
        "buys": sum(r[4] for r in rows),
        "sells": sum(r[5] for r in rows),
        "price_change_pct": (rows[0][1] / rows[-1][1] - 1) * 100 if rows[-1][1] else 0.0,
        "series": [(r[0], r[1], r[4], r[5]) for r in reversed(rows)],
    }


def guides(days: int = 7) -> int:
    """`days <= 0` counts every published guide, which is the number the operator asks for."""
    n = 0
    since = dt.date.today() - dt.timedelta(days=days) if days > 0 else dt.date.min
    for f in (ROOT / "web" / "content").rglob("*.md"):
        m = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", f.read_text(encoding="utf-8"), re.M)
        if m and dt.date.fromisoformat(m.group(1)) >= since:
            n += 1
    return n


def balance() -> float | None:
    try:
        from pedibot.bot.llm import deepseek_balance
        from pedibot.settings import get_settings

        s = get_settings()
        b = deepseek_balance(s.deepseek_api_key, s.deepseek_base_url)
        t = b.get("total_usd")
        return float(t) if isinstance(t, (int, float)) else None
    except Exception:  # noqa: BLE001
        return None


def recent_answers(
    con: sqlite3.Connection, limit: int = 50, include_test: bool = False
) -> list[dict[str, Any]]:
    """The cards under the numbers. Same rule: ours are not shown unless asked for, and when they
    are, the card says so — a test answer read as a parent's is how a fake problem gets chased."""
    rows = con.execute(
        "SELECT id, ts, lang, country, level, verification, feedback, cost_usd, latency_ms, question, answer, source"
        " FROM answers WHERE 1=1" + ("" if include_test else REAL_ONLY) + " ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    keys = (
        "id",
        "ts",
        "lang",
        "country",
        "level",
        "verification",
        "feedback",
        "cost_usd",
        "latency_ms",
        "question",
        "answer",
        "source",
    )
    out = []
    for r in rows:
        d = dict(zip(keys, r, strict=True))
        d["channel"] = _CHANNEL.get(str(d["source"]), str(d["source"]))
        out.append(d)
    return out


#: for the little tag on each card
_CHANNEL = {
    "web": "web",
    "telegram": "telegram",
    "agent": "agente",
    "test": "prueba nuestra",
    "unknown": "sin identificar",
}


def weekly_text(con: sqlite3.Connection) -> str:
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
        lines.append("🪙 PDBT: sin datos aún")
    lines.append(f"📝 Guías publicadas: {g}")
    if bal is not None and bal < 2:
        lines.append("⚠️ Saldo DeepSeek bajo: recarga en platform.deepseek.com")
    return "\n".join(lines)
