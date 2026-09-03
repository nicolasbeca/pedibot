"""Push a Telegram message when somebody buys or sells $PDBT — and stay silent otherwise.

Two chains, read two different ways. Base trades in a Uniswap pool that GeckoTerminal indexes;
HyperEVM trades in a LiquidLaunch bonding curve that nothing indexes, so that one is read from
the chain's own Transfer logs (curve → wallet is a buy, wallet → curve is a sell).

The daily snapshot (`token_snapshot.py`) only counts trades for the Sunday report, so a purchase
on a Tuesday was not known until the weekend. This reads the pool's actual trades from the free
GeckoTerminal API, remembers each transaction hash, and announces only the ones it has not seen.

The pool is PDBT / VIRTUAL on Base (`virtuals-unicorn-base`) and **PDBT is its base token**, so
the API's `kind` is already from our point of view: `buy` means somebody bought PDBT.

Run hourly by pedibot-token-alert.timer. Nothing new → no message, no noise. The endpoint only
returns the last 24 h of trades: if this stops running for a whole day the trade is still counted
in the daily snapshot and shows up in the Sunday report, just without a push.
"""

from __future__ import annotations

import datetime as dt
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

POOL = "0x94dfe42f6dc61d1caad037a79214b684f5377784"
TRADES_URL = f"https://api.geckoterminal.com/api/v2/networks/base/pools/{POOL}/trades"
HEADERS = {"Accept": "application/json;version=20230302", "User-Agent": "PediBot-ops/1.0"}
MAX_LINES = 5  # a burst is summarised instead of flooding the chat

# --- HyperEVM: the bonding curve, read from the chain ------------------------------------------
HYPEREVM_RPC = "https://rpc.hyperliquid.xyz/evm"
PDBT_HYPEREVM = "0x4a2caac88e85cc858a6265e773fc8db5aa40b5e5"
PDBT_HYPEREVM_DECIMALS = 6  # not 18 — checked on the contract before writing this
LIQUIDLAUNCH_CURVE = "0xdec3540f5ba6f2aa3764583a9c29501feb020030"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
RPC_MAX_RANGE = 1000  # the public node refuses a wider eth_getLogs window
RPC_MAX_CHUNKS = 40  # ~22 h of chain per run; the timer is hourly, so this is slack, not a cap

EXPLORER = {
    "base": "https://basescan.org/tx/",
    # LiquidLaunch's own page rather than a block explorer: the HyperEVM explorers refuse
    # datacenter IPs, so this is the only link that was actually verified to load.
    "hyperevm": "https://liquidlaunch.app/token/" + PDBT_HYPEREVM + "?tx=",
}
CHAIN_LABEL = {"base": "Base", "hyperevm": "HyperEVM"}


@dataclass(frozen=True)
class Trade:
    tx_hash: str
    ts: str
    kind: str  # buy | sell, already from PDBT's point of view
    usd: float
    tokens: float
    wallet: str
    chain: str = "base"
    # HYPE paid, for HyperEVM buys only. None means "not known", never zero-as-unknown.
    native: float | None = None


def parse_trades(payload: dict[str, Any]) -> list[Trade]:
    out: list[Trade] = []
    for item in (payload or {}).get("data") or []:
        a = (item or {}).get("attributes") or {}
        tx = a.get("tx_hash")
        if not tx:
            continue
        kind = str(a.get("kind") or "").lower()
        # from/to are the sides of the swap: buying PDBT receives it, selling it gives it away
        tokens = a.get("to_token_amount") if kind == "buy" else a.get("from_token_amount")
        out.append(
            Trade(
                tx_hash=str(tx),
                ts=str(a.get("block_timestamp") or ""),
                kind=kind,
                usd=float(a.get("volume_in_usd") or 0),
                tokens=float(tokens or 0),
                wallet=str(a.get("tx_from_address") or ""),
            )
        )
    return out


def _rpc(method: str, params: list[Any]) -> Any:
    r = httpx.post(
        HYPEREVM_RPC,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(str(body["error"]))
    return body["result"]


def _addr(topic: str) -> str:
    return "0x" + topic[-40:]


def hyperevm_trades(from_block: int) -> tuple[list[Trade], int]:
    """Every buy and sell of PDBT on the curve since `from_block`, and the block it read up to.

    Returns the head it scanned to so the caller can persist it: without that the next run either
    rescans from genesis or misses the gap.
    """
    head = int(_rpc("eth_blockNumber", []), 16)
    out: list[Trade] = []
    stamps: dict[int, str] = {}
    a = max(from_block, head - RPC_MAX_RANGE * RPC_MAX_CHUNKS)
    chunks = 0
    while a <= head and chunks < RPC_MAX_CHUNKS:
        b = min(a + RPC_MAX_RANGE - 1, head)
        logs = _rpc(
            "eth_getLogs",
            [
                {
                    "address": PDBT_HYPEREVM,
                    "topics": [TRANSFER_TOPIC],
                    "fromBlock": hex(a),
                    "toBlock": hex(b),
                }
            ],
        )
        for log in logs:
            topics = log.get("topics") or []
            if len(topics) < 3:
                continue
            src, dst = _addr(topics[1]).lower(), _addr(topics[2]).lower()
            curve = LIQUIDLAUNCH_CURVE.lower()
            if curve not in (src, dst):
                continue  # a wallet-to-wallet transfer is not a trade
            if src == "0x" + "0" * 40:
                continue  # the mint at launch is not a purchase
            kind = "buy" if src == curve else "sell"
            wallet = dst if kind == "buy" else src
            block = int(log["blockNumber"], 16)
            if block not in stamps:
                blk = _rpc("eth_getBlockByNumber", [hex(block), False])
                ts = int(blk["timestamp"], 16)
                stamps[block] = (
                    dt.datetime.fromtimestamp(ts, dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                )
            native = None
            if kind == "buy":
                try:
                    tx = _rpc("eth_getTransactionByHash", [log["transactionHash"]])
                    native = int(tx["value"], 16) / 1e18
                except Exception:  # noqa: BLE001 — the amount is a nicety, the alert is not
                    native = None
            out.append(
                Trade(
                    tx_hash=str(log["transactionHash"]),
                    ts=stamps[block],
                    kind=kind,
                    usd=0.0,
                    tokens=int(log["data"], 16) / (10**PDBT_HYPEREVM_DECIMALS),
                    wallet=wallet,
                    chain="hyperevm",
                    native=native,
                )
            )
        a = b + 1
        chunks += 1
    return out, head


def new_trades(trades: list[Trade], seen: set[str]) -> list[Trade]:
    return [t for t in trades if t.tx_hash not in seen]


def _money(value: float) -> str:
    return f"{value:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _amount(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def format_message(trades: list[Trade]) -> str:
    if not trades:
        return ""
    trades = sorted(trades, key=lambda t: t.ts)
    head = "PediBot · $PDBT: " + (
        "1 movimiento nuevo" if len(trades) == 1 else f"{len(trades)} movimientos nuevos"
    )
    lines = []
    for t in trades[:MAX_LINES]:
        arrow = "🟢 COMPRA" if t.kind == "buy" else "🔴 VENTA "
        clock = t.ts[11:16] + " UTC" if len(t.ts) >= 16 else t.ts
        # Base knows the dollar value from the pool; the curve does not, so it shows what it has
        # (the HYPE paid) and says nothing where it knows nothing.
        if t.chain == "base":
            size = f"{_money(t.usd)} USD"
        elif t.native is not None:
            size = f"{t.native:.4f} HYPE".replace(".", ",")
        else:
            size = "importe no visible"
        lines.append(
            f"{arrow}  {size} · {_amount(t.tokens)} PDBT · {CHAIN_LABEL.get(t.chain, t.chain)}"
            f" · {clock}\n   {EXPLORER.get(t.chain, '')}{t.tx_hash}"
        )
    if len(trades) > MAX_LINES:
        rest = trades[MAX_LINES:]
        lines.append(f"…y {len(rest)} más, {_money(sum(t.usd for t in rest))} USD en total.")
    priced = [t for t in trades if t.chain == "base"]
    total = sum(t.usd for t in priced if t.kind == "buy") - sum(
        t.usd for t in priced if t.kind == "sell"
    )
    tail = (
        f"Saldo del lote (Base): {'+' if total >= 0 else '−'}{_money(abs(total))} USD"
        if priced
        else f"{len(trades)} movimiento(s) en la curva de HyperEVM"
    )
    return f"{head}\n\n" + "\n".join(lines) + f"\n\n{tail}"


def record_and_select(db_path: Path, trades: list[Trade]) -> list[Trade]:
    """Store the trades and return the ones worth announcing.

    The very first run only takes a baseline: without it the first poll would announce every
    trade the pool has had in the last 24 hours as if it had just happened.
    """
    con = sqlite3.connect(db_path)
    first_run = not con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='token_trades'"
    ).fetchone()
    con.execute(
        "CREATE TABLE IF NOT EXISTS token_trades (tx_hash TEXT PRIMARY KEY, ts TEXT, kind TEXT,"
        " usd REAL, tokens REAL, wallet TEXT, announced INTEGER NOT NULL DEFAULT 0)"
    )
    # the table predates the second chain; the rows already in it are all Base
    cols = {r[1] for r in con.execute("PRAGMA table_info(token_trades)")}
    if "chain" not in cols:
        con.execute("ALTER TABLE token_trades ADD COLUMN chain TEXT NOT NULL DEFAULT 'base'")
    if "native" not in cols:
        con.execute("ALTER TABLE token_trades ADD COLUMN native REAL")
    con.execute(
        "CREATE TABLE IF NOT EXISTS token_scan_state (chain TEXT PRIMARY KEY, last_block INTEGER)"
    )
    seen = {r[0] for r in con.execute("SELECT tx_hash FROM token_trades")}
    fresh = new_trades(trades, seen)
    con.executemany(
        "INSERT OR IGNORE INTO token_trades"
        " (tx_hash, ts, kind, usd, tokens, wallet, announced, chain, native)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (
                t.tx_hash,
                t.ts,
                t.kind,
                t.usd,
                t.tokens,
                t.wallet,
                0 if first_run else 1,
                t.chain,
                t.native,
            )
            for t in fresh
        ],
    )
    con.commit()
    con.close()
    return [] if first_run else fresh


def telegram(text: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("telegram not configured:", text, file=sys.stderr)
        return False
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    return r.status_code == 200


def scan_state(db_path: Path, chain: str) -> int:
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS token_scan_state (chain TEXT PRIMARY KEY, last_block INTEGER)"
    )
    row = con.execute(
        "SELECT last_block FROM token_scan_state WHERE chain = ?", (chain,)
    ).fetchone()
    con.close()
    return int(row[0]) if row else 0


def save_scan_state(db_path: Path, chain: str, block: int) -> None:
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS token_scan_state (chain TEXT PRIMARY KEY, last_block INTEGER)"
    )
    con.execute(
        "INSERT INTO token_scan_state (chain, last_block) VALUES (?, ?)"
        " ON CONFLICT(chain) DO UPDATE SET last_block = excluded.last_block",
        (chain, block),
    )
    con.commit()
    con.close()


def main() -> int:
    from pedibot.settings import get_settings

    db = get_settings().ops_db_path
    trades: list[Trade] = []
    failures = 0

    # Base, through the pool aggregator
    try:
        r = httpx.get(TRADES_URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        trades += parse_trades(r.json())
    except Exception as e:  # noqa: BLE001 — a flaky public API must not page the operator
        print("geckoterminal trades failed:", e, file=sys.stderr)
        failures += 1

    # HyperEVM, straight off the chain. One chain failing must not silence the other.
    try:
        last = scan_state(db, "hyperevm")
        found, head = hyperevm_trades(last + 1 if last else 0)
        trades += found
        save_scan_state(db, "hyperevm", head)
    except Exception as e:  # noqa: BLE001
        print("hyperevm scan failed:", e, file=sys.stderr)
        failures += 1

    fresh = record_and_select(db, trades)
    if fresh:
        telegram(format_message(fresh))
        print(f"announced {len(fresh)} trade(s)")
    return 1 if failures == 2 else 0


if __name__ == "__main__":
    raise SystemExit(main())
