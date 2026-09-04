"""Push a Telegram message when somebody buys or sells $PDBT — and stay silent otherwise.

Three chains, read two different ways. Base (Uniswap) and Solana (a Meteora bonding curve out
of Jupiter Studio) are both indexed by GeckoTerminal and answer with the same payload, so they
share a reader. HyperEVM trades in a LiquidLaunch bonding curve that nothing indexes, so that
one is read from the chain's own Transfer logs (curve → wallet is a buy, wallet → curve is a sell).

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
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

GECKO = "https://api.geckoterminal.com/api/v2/networks"
POOL = "0x94dfe42f6dc61d1caad037a79214b684f5377784"
TRADES_URL = f"{GECKO}/base/pools/{POOL}/trades"

# --- Solana: same aggregator, same payload, a different pool ----------------------------
# The Jupiter Studio launch trades in a Meteora dynamic bonding curve. PDBT is that pool's
# base token too, so `kind` is already from our point of view and needs no flipping.
SOLANA_POOL = "9TYrAWquKToiwJj4yX46rqhSjYSBHMWFQFLpndexoQCR"
SOLANA_TRADES_URL = f"{GECKO}/solana/pools/{SOLANA_POOL}/trades"
HEADERS = {"Accept": "application/json;version=20230302", "User-Agent": "PediBot-ops/1.0"}
MAX_LINES = 5  # a burst is summarised instead of flooding the chat

# --- HyperEVM: the bonding curve, read from the chain ------------------------------------------
#: Tried in order. The public endpoint caps eth_getLogs at a 1000-block window
#: and then rate-limits the queries a catch-up needs — it refused fifteen
#: consecutive runs on 3-sep and the alert went blind for fourteen hours.
#: Measured 4-sep: purroofgroup answers a 100.000-block window in under three
#: seconds, so one query now covers half a day of chain.
HYPEREVM_RPCS = (
    "https://rpc.purroofgroup.com",
    "https://rpc.hyperliquid.xyz/evm",
)
PDBT_HYPEREVM = "0x4a2caac88e85cc858a6265e773fc8db5aa40b5e5"
PDBT_HYPEREVM_DECIMALS = 6  # not 18 — checked on the contract before writing this
LIQUIDLAUNCH_CURVE = "0xdec3540f5ba6f2aa3764583a9c29501feb020030"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
RPC_MAX_RANGE = 50_000  # comfortably inside what the primary node serves in one call
RPC_MAX_CHUNKS = 20  # a million blocks per run: catches up from any realistic outage
BLIND_AFTER = 3  # consecutive failures before the operator is told it cannot see

EXPLORER = {
    "base": "https://basescan.org/tx/",
    # LiquidLaunch's own page rather than a block explorer: the HyperEVM explorers refuse
    # datacenter IPs, so this is the only link that was actually verified to load.
    "hyperevm": "https://liquidlaunch.app/token/" + PDBT_HYPEREVM + "?tx=",
    "solana": "https://solscan.io/tx/",
}
CHAIN_LABEL = {"base": "Base", "hyperevm": "HyperEVM", "solana": "Solana"}
#: Chains whose trades arrive with a dollar value already attached. The HyperEVM curve
#: does not, and printing 0,00 USD there would be inventing a number.
PRICED_CHAINS = ("base", "solana")


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


def parse_trades(payload: dict[str, Any], chain: str = "base") -> list[Trade]:
    """Trades out of a GeckoTerminal pool response.

    `chain` defaults to base because that was this function's only caller for a week. A
    Solana trade filed under it would be shown with a Basescan link to a hash that is not
    on Base, which is worse than not announcing it at all.
    """
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
                chain=chain,
            )
        )
    return out


def _rpc(method: str, params: list[Any], tries: int = 3) -> Any:
    """One JSON-RPC call: every node in turn, with backoff, before giving up.

    A node rate-limits a burst of range queries and answers that as a JSON error
    rather than an HTTP status, so a caller that does not check the body silently
    reads zero trades and reports "nothing happened" — the worst possible failure
    for an alert. One node refusing is not an outage while another answers, which
    is the whole point of there being more than one.
    """
    last = ""
    for url in HYPEREVM_RPCS:
        for attempt in range(tries):
            try:
                r = httpx.post(
                    url,
                    json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                    timeout=45,
                )
                r.raise_for_status()
                body = r.json()
                if "error" not in body:
                    return body["result"]
                last = f"{url}: {body['error']}"
                if "rate limit" not in last.lower():
                    break  # a real error repeats; only throttling is worth waiting out
            except Exception as e:  # noqa: BLE001 — try the next node, not the next run
                last = f"{url}: {e}"
            if attempt < tries - 1:
                time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(last)


def _addr(topic: str) -> str:
    return "0x" + topic[-40:]


def hyperevm_trades(from_block: int) -> tuple[list[Trade], int]:
    """Every buy and sell of PDBT on the curve since `from_block`, and the last block actually read.

    It returns what it covered, not where the chain is. Those differ whenever the
    scan is further behind than one run can travel, and conflating them is what
    lost a real purchase on 3-sep: the old version jumped to `head - 12000` when
    it fell behind and then saved `head`, marking as read twelve thousand blocks
    it had never looked at. Resuming from the watermark and persisting only the
    ground covered turns a long outage into a slow catch-up instead of a hole.
    """
    head = int(_rpc("eth_blockNumber", []), 16)
    out: list[Trade] = []
    stamps: dict[int, str] = {}
    a = from_block  # never skip ahead: what is not read must not be recorded as read
    scanned = from_block - 1
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
        scanned = b
        a = b + 1
        chunks += 1
        time.sleep(0.4)  # the node is free; do not make it regret that
    return out, scanned


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
        # The indexed pools know the dollar value; the HyperEVM curve does not, so it shows
        # what it has (the HYPE paid) and says nothing where it knows nothing.
        if t.chain in PRICED_CHAINS:
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
    priced = [t for t in trades if t.chain in PRICED_CHAINS]
    total = sum(t.usd for t in priced if t.kind == "buy") - sum(
        t.usd for t in priced if t.kind == "sell"
    )
    tail = (
        f"Saldo del lote: {'+' if total >= 0 else '−'}{_money(abs(total))} USD"
        if priced
        else f"{len(trades)} movimiento(s) en la curva de HyperEVM"
    )
    return f"{head}\n\n" + "\n".join(lines) + f"\n\n{tail}"


def record_and_select(
    db_path: Path, trades: list[Trade], baseline_chains: frozenset[str] = frozenset()
) -> list[Trade]:
    """Store the trades and return the ones worth announcing.

    The very first run only takes a baseline: without it the first poll would announce every
    trade the pool has had in the last 24 hours as if it had just happened.

    `baseline_chains` is that same idea for a chain that joins later, when the database is no
    longer new: Solana was wired up hours after its launch, with the launch trades already
    sitting in the pool. They are remembered so they are never announced, and everything after
    them is news.
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
    # only what has actually been delivered counts as seen: a row still waiting to be
    # sent must come back around, or a refused message loses the trade silently
    seen = {r[0] for r in con.execute("SELECT tx_hash FROM token_trades WHERE announced = 1")}
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
                # 1 means handled: delivered, or deliberately skipped as history
                1 if (first_run or t.chain in baseline_chains) else 0,
                t.chain,
                t.native,
            )
            for t in fresh
        ],
    )
    con.commit()
    con.close()
    if first_run:
        return []
    return [t for t in fresh if t.chain not in baseline_chains]


def note_scan_health(db_path: Path, chain: str, ok: bool) -> str | None:
    """Track whether a chain can be read at all, and speak when that changes.

    The alert was refused fifteen times in a row and said nothing, so its silence
    read as "nobody is trading". An alert whose failure is indistinguishable from
    good news is worse than no alert, because it is trusted. One blip is not news;
    three in a row is, once, and so is coming back.
    """
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS token_scan_health (chain TEXT PRIMARY KEY,"
        " streak INTEGER NOT NULL DEFAULT 0, warned INTEGER NOT NULL DEFAULT 0)"
    )
    row = con.execute(
        "SELECT streak, warned FROM token_scan_health WHERE chain = ?", (chain,)
    ).fetchone()
    streak, warned = row if row else (0, 0)
    label = CHAIN_LABEL.get(chain, chain)
    message: str | None = None
    if ok:
        if warned:
            message = (
                f"PediBot · $PDBT: el rastreo de {label} vuelve a funcionar tras "
                f"{streak} intentos fallidos. Nada se ha perdido: la marca de "
                f"agua no avanza sobre lo que no llegó a leerse, así que los "
                f"movimientos de ese rato se anuncian ahora."
            )
        streak, warned = 0, 0
    else:
        streak += 1
        if streak >= BLIND_AFTER and not warned:
            warned = 1
            message = (
                f"PediBot · $PDBT: llevo {streak} intentos seguidos sin poder "
                f"leer {label}. Que no lleguen avisos de esa red NO significa "
                f"que no haya movimientos: significa que no los estoy viendo."
            )
    con.execute(
        "INSERT INTO token_scan_health (chain, streak, warned) VALUES (?, ?, ?)"
        " ON CONFLICT(chain) DO UPDATE SET streak = excluded.streak,"
        " warned = excluded.warned",
        (chain, streak, warned),
    )
    con.commit()
    con.close()
    return message


def pending_trades(db_path: Path) -> list[Trade]:
    """Trades found but not yet delivered, oldest first.

    A message Telegram refused is not a message that happened. These come back on
    the next run rather than being written off, which matters most for HyperEVM:
    its watermark has already moved past them, so nothing would ever find them
    again.
    """
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT tx_hash, ts, kind, usd, tokens, wallet, chain, native"
            " FROM token_trades WHERE announced = 0 ORDER BY ts"
        ).fetchall()
    except sqlite3.OperationalError:
        return []  # nothing has ever been recorded
    finally:
        con.close()
    return [
        Trade(
            tx_hash=r[0], ts=r[1], kind=r[2], usd=r[3], tokens=r[4],
            wallet=r[5], chain=r[6] or "base", native=r[7],
        )
        for r in rows
    ]


def mark_announced(db_path: Path, trades: list[Trade]) -> None:
    """Called only after Telegram has accepted the message."""
    if not trades:
        return
    con = sqlite3.connect(db_path)
    con.executemany(
        "UPDATE token_trades SET announced = 1 WHERE tx_hash = ?",
        [(t.tx_hash,) for t in trades],
    )
    con.commit()
    con.close()


def telegram(text: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("telegram not configured:", text, file=sys.stderr)
        return False
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
            timeout=20,
        )
    except Exception as e:  # noqa: BLE001 — a blip queues the message, not crashes the run
        print("telegram unreachable:", e, file=sys.stderr)
        return False
    if r.status_code != 200:
        print("telegram refused the message:", r.status_code, r.text[:200], file=sys.stderr)
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
    baseline: set[str] = set()

    notes: list[str | None] = []

    # Base, through the pool aggregator
    try:
        r = httpx.get(TRADES_URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        trades += parse_trades(r.json())
        notes.append(note_scan_health(db, "base", ok=True))
    except Exception as e:  # noqa: BLE001 — a flaky public API must not page the operator
        print("geckoterminal trades failed:", e, file=sys.stderr)
        failures += 1
        notes.append(note_scan_health(db, "base", ok=False))

    # Solana, through the same aggregator. Its first sighting is a baseline, not an
    # announcement. The watermark is written even when the pool answers with nothing, so a
    # chain that has not traded yet cannot stay "new" and swallow its first real trade.
    try:
        if not scan_state(db, "solana"):
            baseline.add("solana")
        r = httpx.get(SOLANA_TRADES_URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        trades += parse_trades(r.json(), chain="solana")
        save_scan_state(db, "solana", int(time.time()))
        notes.append(note_scan_health(db, "solana", ok=True))
    except Exception as e:  # noqa: BLE001
        print("solana trades failed:", e, file=sys.stderr)
        failures += 1
        notes.append(note_scan_health(db, "solana", ok=False))

    # HyperEVM, straight off the chain. One chain failing must not silence the others.
    try:
        last = scan_state(db, "hyperevm")
        if not last:
            # First run: just note where the chain is and watch from there. Reading the curve's
            # whole history would announce last week's trades as if they had just happened, and
            # asking the free node for forty range queries at once gets the door shut anyway.
            head = int(_rpc("eth_blockNumber", []), 16)
            save_scan_state(db, "hyperevm", head)
            print(f"hyperevm baseline set at block {head}; watching from here")
        else:
            found, scanned = hyperevm_trades(last + 1)
            trades += found
            # only what was actually covered; a partial catch-up resumes here
            save_scan_state(db, "hyperevm", scanned)
        notes.append(note_scan_health(db, "hyperevm", ok=True))
    except Exception as e:  # noqa: BLE001
        print("hyperevm scan failed:", e, file=sys.stderr)
        failures += 1
        notes.append(note_scan_health(db, "hyperevm", ok=False))

    record_and_select(db, trades, frozenset(baseline))
    # everything still undelivered, including anything a previous run could not send
    pending = pending_trades(db)
    if pending:
        if telegram(format_message(pending)):
            mark_announced(db, pending)
            print(f"announced {len(pending)} trade(s)")
        else:
            print(
                f"telegram did not take {len(pending)} trade(s); they stay queued",
                file=sys.stderr,
            )
    for note in notes:
        if note:
            telegram(note)
            print(note)
    # only a total blackout is worth a non-zero exit; one flaky source is not an incident
    return 1 if failures == 3 else 0


if __name__ == "__main__":
    raise SystemExit(main())
