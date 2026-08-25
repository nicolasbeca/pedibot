"""Daily snapshot of $PDBT market data (Dexscreener, no key) into the ops DB → weekly report.

Dexscreener only exposes 24 h windows (buys/sells/volume), so we store one row per day and the
weekly report sums the last 7. Run by pedibot-token.timer at 23:50 UTC.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
import sys

import httpx

from pedibot.settings import get_settings

TOKEN = "0x196A67BA334DbeD501E19BAEc47D217BB2FC15E1"
URL = f"https://api.dexscreener.com/latest/dex/tokens/{TOKEN}"


def main() -> int:
    s = get_settings()
    con = sqlite3.connect(s.ops_db_path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS token_daily (day TEXT PRIMARY KEY, price_usd REAL, fdv_usd REAL,"
        " liquidity_usd REAL, volume_24h_usd REAL, buys_24h INTEGER, sells_24h INTEGER, raw TEXT)"
    )
    try:
        r = httpx.get(URL, timeout=30)
        r.raise_for_status()
        pairs = r.json().get("pairs") or []
    except Exception as e:  # noqa: BLE001
        print("dexscreener failed:", e, file=sys.stderr)
        return 1
    if not pairs:
        print("no pairs")
        return 0
    p = max(pairs, key=lambda x: float((x.get("liquidity") or {}).get("usd") or 0))
    day = dt.datetime.now(dt.UTC).date().isoformat()
    tx = (p.get("txns") or {}).get("h24") or {}
    row = (
        day,
        float(p.get("priceUsd") or 0),
        float(p.get("fdv") or 0),
        float((p.get("liquidity") or {}).get("usd") or 0),
        float((p.get("volume") or {}).get("h24") or 0),
        int(tx.get("buys") or 0),
        int(tx.get("sells") or 0),
        json.dumps({"pair": p.get("pairAddress"), "dex": p.get("dexId")}),
    )
    con.execute("INSERT OR REPLACE INTO token_daily VALUES (?,?,?,?,?,?,?,?)", row)
    con.commit()
    print(
        json.dumps(
            {
                "day": day,
                "price": row[1],
                "fdv": row[2],
                "vol24h": row[4],
                "buys": row[5],
                "sells": row[6],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
