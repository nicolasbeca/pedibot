"""Daily snapshot of $PDBT market data into the ops DB → weekly report.

Source: GeckoTerminal public API (no key). Dexscreener does not list this token (checked 25-ago).
Only 24 h windows are exposed, so we store one row per day and the weekly report sums 7.
Run by pedibot-token.timer at 23:50 UTC.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
import sys

import httpx

from pedibot.settings import get_settings

TOKEN = "0x196A67BA334DbeD501E19BAEc47D217BB2FC15E1"
POOL = "0x94dfe42f6dc61d1caad037a79214b684f5377784"  # main Uniswap pool on Base
GT = "https://api.geckoterminal.com/api/v2/networks/base"
HEADERS = {"Accept": "application/json;version=20230302", "User-Agent": "PediBot-ops/1.0"}


def fetch() -> dict[str, float | int]:
    with httpx.Client(headers=HEADERS, timeout=30) as c:
        t = c.get(f"{GT}/tokens/{TOKEN}")
        t.raise_for_status()
        ta = t.json()["data"]["attributes"]
        p = c.get(f"{GT}/pools/{POOL}")
        p.raise_for_status()
        pa = p.json()["data"]["attributes"]
    tx = (pa.get("transactions") or {}).get("h24") or {}
    return {
        "price_usd": float(ta.get("price_usd") or 0),
        "fdv_usd": float(ta.get("fdv_usd") or 0),
        "liquidity_usd": float(pa.get("reserve_in_usd") or ta.get("total_reserve_in_usd") or 0),
        "volume_24h_usd": float((ta.get("volume_usd") or {}).get("h24") or 0),
        "buys_24h": int(tx.get("buys") or 0),
        "sells_24h": int(tx.get("sells") or 0),
    }


def main() -> int:
    s = get_settings()
    con = sqlite3.connect(s.ops_db_path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS token_daily (day TEXT PRIMARY KEY, price_usd REAL, fdv_usd REAL,"
        " liquidity_usd REAL, volume_24h_usd REAL, buys_24h INTEGER, sells_24h INTEGER, raw TEXT)"
    )
    try:
        d = fetch()
    except Exception as e:  # noqa: BLE001
        print("geckoterminal failed:", e, file=sys.stderr)
        return 1
    day = dt.datetime.now(dt.UTC).date().isoformat()
    con.execute(
        "INSERT OR REPLACE INTO token_daily VALUES (?,?,?,?,?,?,?,?)",
        (
            day,
            d["price_usd"],
            d["fdv_usd"],
            d["liquidity_usd"],
            d["volume_24h_usd"],
            d["buys_24h"],
            d["sells_24h"],
            json.dumps({"pool": POOL, "src": "geckoterminal"}),
        ),
    )
    con.commit()
    print(json.dumps({"day": day, **d}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
