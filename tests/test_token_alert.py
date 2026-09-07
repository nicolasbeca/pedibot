"""Buy/sell alert for $PDBT (27-ago-2026).

The operator wants a push the moment somebody buys or sells, and *nothing at all* when nothing
happens. The daily snapshot only counts trades for the Sunday report; this reads the pool's actual
trades, so each one is identified by its transaction hash and can never be reported twice.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location("token_alert", ROOT / "ops" / "token_alert.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    sys.modules["token_alert"] = m
    spec.loader.exec_module(m)
    return m


PAYLOAD = {
    "data": [
        {
            "attributes": {
                "tx_hash": "0xaaa",
                "block_timestamp": "2026-08-27T09:45:45Z",
                "kind": "buy",
                "volume_in_usd": "41.2",
                "from_token_amount": "12.5",
                "to_token_amount": "1653000.0",
                "tx_from_address": "0x4337062690416e632d08d14e819892d6498f9ad4",
            }
        },
        {
            "attributes": {
                "tx_hash": "0xbbb",
                "block_timestamp": "2026-08-27T10:04:00Z",
                "kind": "sell",
                "volume_in_usd": "12.05",
                "from_token_amount": "483000.0",
                "to_token_amount": "3.6",
                "tx_from_address": "0xdead",
            }
        },
    ]
}


def test_a_buy_reports_the_tokens_received_and_a_sell_the_tokens_sold():
    m = _mod()
    buy, sell = m.parse_trades(PAYLOAD)
    assert (buy.kind, buy.usd, buy.tokens) == ("buy", 41.2, 1653000.0)
    assert (sell.kind, sell.usd, sell.tokens) == ("sell", 12.05, 483000.0)
    assert buy.tx_hash == "0xaaa"


def test_only_unseen_transactions_are_reported():
    m = _mod()
    trades = m.parse_trades(PAYLOAD)
    assert [t.tx_hash for t in m.new_trades(trades, {"0xaaa"})] == ["0xbbb"]
    assert m.new_trades(trades, {"0xaaa", "0xbbb"}) == []


def test_the_message_names_the_direction_the_money_and_the_wallet():
    m = _mod()
    text = m.format_message(m.parse_trades(PAYLOAD))
    assert "COMPRA" in text and "VENTA" in text
    assert "41,20" in text and "12,05" in text
    assert "basescan.org/tx/0xaaa" in text


def test_nothing_to_report_produces_no_message():
    m = _mod()
    assert m.format_message([]) == ""


def test_the_first_run_only_takes_a_baseline(tmp_path: pathlib.Path):
    """Otherwise the first poll would fire an alert for every historical trade."""
    m = _mod()
    db = tmp_path / "ops.db"
    trades = m.parse_trades(PAYLOAD)
    assert m.record_and_select(db, trades) == []  # first run: remembered, not announced
    assert m.record_and_select(db, trades) == []  # already seen
    more = m.parse_trades(
        {"data": [{"attributes": {**PAYLOAD["data"][0]["attributes"], "tx_hash": "0xccc"}}]}
    )
    assert [t.tx_hash for t in m.record_and_select(db, more)] == ["0xccc"]


def test_a_trade_without_a_hash_is_ignored():
    m = _mod()
    assert m.parse_trades({"data": [{"attributes": {"kind": "buy"}}]}) == []


@pytest.mark.parametrize("payload", [{}, {"data": None}, {"data": []}])
def test_an_empty_or_broken_answer_is_not_a_crash(payload):
    m = _mod()
    assert m.parse_trades(payload) == []


# ---------------------------------------------------------------- HyperEVM (3-sep-2026)
def test_a_transfer_to_the_curve_is_a_sale_and_from_it_a_purchase(monkeypatch) -> None:
    """The bonding curve has no aggregator, so direction is read off the Transfer itself.
    Getting this backwards would announce every sale as a purchase."""
    m = _mod()
    curve = m.LIQUIDLAUNCH_CURVE.lower()
    buyer = "0x" + "11" * 20

    def pad(a: str) -> str:
        return "0x" + "0" * 24 + a[2:]

    calls = {"blocks": 0}

    def fake_rpc(method, params):
        if method == "eth_blockNumber":
            return hex(1000)
        if method == "eth_getLogs":
            lo = int(params[0]["fromBlock"], 16)
            hi = int(params[0]["toBlock"], 16)
            everything = [
                {  # curve → buyer: a purchase
                    "topics": [m.TRANSFER_TOPIC, pad(curve), pad(buyer)],
                    "data": hex(5_000_000),  # 5 PDBT at 6 decimals
                    "blockNumber": hex(900),
                    "transactionHash": "0x" + "aa" * 32,
                },
                {  # buyer → curve: a sale
                    "topics": [m.TRANSFER_TOPIC, pad(buyer), pad(curve)],
                    "data": hex(2_000_000),
                    "blockNumber": hex(901),
                    "transactionHash": "0x" + "bb" * 32,
                },
                {  # wallet to wallet: not a trade at all
                    "topics": [m.TRANSFER_TOPIC, pad(buyer), pad("0x" + "22" * 20)],
                    "data": hex(1_000_000),
                    "blockNumber": hex(902),
                    "transactionHash": "0x" + "cc" * 32,
                },
                {  # the launch mint: not a purchase
                    "topics": [m.TRANSFER_TOPIC, pad("0x" + "00" * 20), pad(curve)],
                    "data": hex(10**15),
                    "blockNumber": hex(903),
                    "transactionHash": "0x" + "dd" * 32,
                },
            ]
            # a real node honours the window; a fake that ignores it hides double-counting
            return [x for x in everything if lo <= int(x["blockNumber"], 16) <= hi]
        if method == "eth_getBlockByNumber":
            calls["blocks"] += 1
            return {"timestamp": hex(1788400000)}
        if method == "eth_getTransactionByHash":
            return {"value": hex(3 * 10**17)}  # 0.3 HYPE
        raise AssertionError(method)

    monkeypatch.setattr(m, "_rpc", fake_rpc)
    trades, head = m.hyperevm_trades(0)
    assert head == 1000
    kinds = {t.tx_hash[:6]: t.kind for t in trades}
    assert len(trades) == 2, [t.tx_hash for t in trades]
    assert kinds["0xaaaa"] == "buy"
    assert kinds["0xbbbb"] == "sell"
    buy = next(t for t in trades if t.kind == "buy")
    assert buy.tokens == 5.0  # 6 decimals, not 18
    assert buy.native == 0.3
    assert buy.chain == "hyperevm"


def test_one_chain_failing_does_not_silence_the_other(monkeypatch, tmp_path) -> None:
    """A flaky public RPC must not swallow a Base trade, and a flaky aggregator must not swallow
    a HyperEVM one."""
    m = _mod()
    msg = {}
    monkeypatch.setattr(m, "telegram", lambda t: msg.setdefault("text", t) or True)

    class Boom:
        def get(self, *a, **k):
            raise RuntimeError("aggregator down")

        def post(self, *a, **k):
            raise RuntimeError("rpc down")

    monkeypatch.setattr(m, "httpx", Boom())
    db = tmp_path / "ops.db"
    monkeypatch.setattr(
        m, "get_settings", lambda: type("S", (), {"ops_db_path": db})(), raising=False
    )
    # both down → non-zero, and nothing announced
    import sys as _sys

    # setitem, not setdefault: monkeypatch puts the real module back afterwards. Replacing it
    # outright leaked a stub into every test that ran later.
    fake = type(
        "M", (), {"get_settings": staticmethod(lambda: type("S", (), {"ops_db_path": db})())}
    )
    monkeypatch.setitem(_sys.modules, "pedibot.settings", fake)
    assert m.main() == 1
    assert "text" not in msg


def test_the_message_never_invents_a_price() -> None:
    """Base knows the dollar value; the curve does not. A missing amount says so."""
    m = _mod()
    t = m.Trade(
        tx_hash="0x" + "ab" * 32,
        ts="2026-09-03T10:00:00Z",
        kind="buy",
        usd=0.0,
        tokens=1234.0,
        wallet="0x" + "11" * 20,
        chain="hyperevm",
        native=None,
    )
    text = m.format_message([t])
    assert "0,00 USD" not in text
    assert "importe no visible" in text
    assert "HyperEVM" in text


def test_the_first_hyperevm_run_takes_a_baseline_instead_of_announcing_history(
    monkeypatch, tmp_path
) -> None:
    """Without a watermark the first scan sees the curve's whole history. Announcing it would
    push last week's purchases as if they had just happened."""
    m = _mod()
    db = tmp_path / "ops.db"
    sent = []
    monkeypatch.setattr(m, "telegram", lambda t: sent.append(t) or True)
    old = m.Trade(
        tx_hash="0x" + "ee" * 32,
        ts="2026-09-01T10:00:00Z",
        kind="buy",
        usd=0.0,
        tokens=368.0,
        wallet="0x" + "11" * 20,
        chain="hyperevm",
        native=0.05,
    )
    monkeypatch.setattr(m, "hyperevm_trades", lambda frm: ([old], 44902000))
    monkeypatch.setattr(m, "_rpc", lambda method, params, tries=5: hex(44902000))

    class NoAggregator:
        def get(self, *a, **k):
            raise RuntimeError("skip base in this test")

        post = get

    monkeypatch.setattr(m, "httpx", NoAggregator())
    import sys as _sys

    monkeypatch.setitem(
        _sys.modules,
        "pedibot.settings",
        type("M", (), {"get_settings": staticmethod(lambda: type("S", (), {"ops_db_path": db})())}),
    )
    m.main()
    assert sent == [], sent  # nothing pushed on the baseline run
    assert m.scan_state(db, "hyperevm") == 44902000  # but the watermark moved

    # a genuinely new trade after the baseline IS announced
    fresh = m.Trade(
        tx_hash="0x" + "ff" * 32,
        ts="2026-09-03T10:00:00Z",
        kind="sell",
        usd=0.0,
        tokens=10.0,
        wallet="0x" + "22" * 20,
        chain="hyperevm",
        native=None,
    )
    monkeypatch.setattr(m, "hyperevm_trades", lambda frm: ([fresh], 44903000))
    m.main()
    assert len(sent) == 1 and "VENTA" in sent[0]


# --- Solana, the third chain (3-sep-2026) ------------------------------------------------------
# Jupiter Studio's token trades in a Meteora bonding curve that GeckoTerminal indexes as
# `PDBT / USDC` with PDBT as the base token — the same shape as Base, so it is a third source of
# the same reader, not a third mechanism. What it must not do is inherit Base's label or link.

SOLANA_PAYLOAD = {
    "data": [
        {
            "attributes": {
                "tx_hash": "45CgFWEnFpjVtii9",
                "block_timestamp": "2026-09-03T18:45:22Z",
                "kind": "buy",
                "volume_in_usd": "38.38",
                "from_token_amount": "38.38",
                "to_token_amount": "7100000.0",
                "tx_from_address": "GyVBHu1Xexpa",
            }
        }
    ]
}


def test_a_solana_trade_is_tagged_solana_and_not_silently_filed_under_base():
    """`chain` defaults to base for the caller that has always existed; Solana must pass its own,
    or every Solana trade would show a Basescan link to a hash that is not on Base."""
    m = _mod()
    (trade,) = m.parse_trades(SOLANA_PAYLOAD, chain="solana")
    assert trade.chain == "solana"
    assert (trade.kind, trade.usd, trade.tokens) == ("buy", 38.38, 7100000.0)
    # the old signature keeps working untouched
    assert m.parse_trades(PAYLOAD)[0].chain == "base"


def test_the_solana_message_prices_the_trade_and_links_to_its_own_explorer():
    m = _mod()
    text = m.format_message(m.parse_trades(SOLANA_PAYLOAD, chain="solana"))
    assert "Solana" in text
    assert "38,38 USD" in text  # the aggregator knows the price here, unlike the HyperEVM curve
    assert "solscan.io/tx/45CgFWEnFpjVtii9" in text
    assert "basescan" not in text


def test_the_first_solana_run_takes_a_baseline_instead_of_announcing_the_launch(
    monkeypatch, tmp_path
) -> None:
    """The pool already had the launch snipes in it when the alert was wired up. Announcing them
    on the first poll would push hours-old trades as if they had just happened."""
    m = _mod()
    db = tmp_path / "ops.db"
    sent: list[str] = []
    monkeypatch.setattr(m, "telegram", lambda t: sent.append(t) or True)
    payload = {"data": list(SOLANA_PAYLOAD["data"])}

    class OnlySolana:
        def get(self, url, **k):
            if "solana" not in url:
                raise RuntimeError("base not under test here")
            return type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: payload})()

        def post(self, *a, **k):
            raise RuntimeError("hyperevm not under test here")

    monkeypatch.setattr(m, "httpx", OnlySolana())
    import sys as _sys

    monkeypatch.setitem(
        _sys.modules,
        "pedibot.settings",
        type("M", (), {"get_settings": staticmethod(lambda: type("S", (), {"ops_db_path": db})())}),
    )
    m.main()
    assert sent == [], sent
    assert m.scan_state(db, "solana") > 0  # seen once, so the next real trade is not swallowed

    payload["data"] = [
        {
            "attributes": {
                "tx_hash": "9zzNEWTRADEzz",
                "block_timestamp": "2026-09-04T08:00:00Z",
                "kind": "sell",
                "volume_in_usd": "7.5",
                "from_token_amount": "1000000.0",
                "to_token_amount": "7.5",
                "tx_from_address": "GyVBHu1Xexpa",
            }
        }
    ]
    m.main()
    assert len(sent) == 1 and "VENTA" in sent[0] and "Solana" in sent[0]


# --- the day a real purchase was swallowed (4-sep-2026) ----------------------------------------
# The operator bought 1.317.824 PDBT on 3-sep at 19:03 UTC and no alert arrived. Two independent
# faults, either of which alone was enough to lose it:
#
#   1. the public node refused every single scan for fourteen hours straight, and
#   2. when a scan is behind, it used to jump to `head - 12000` and then save `head` as scanned —
#      so the blocks it skipped were marked as read and could never be looked at again.
#
# The second is the dangerous one: the first is a visible outage, the second is silent data loss.


def _fake_chain(monkeypatch, m, head: int, logs_at: dict[int, list] | None = None):
    """A chain that answers range queries and records exactly which ranges were asked for."""
    asked: list[tuple[int, int]] = []
    logs_at = logs_at or {}

    def fake_rpc(method, params, tries=5):
        if method == "eth_blockNumber":
            return hex(head)
        if method == "eth_getLogs":
            lo, hi = int(params[0]["fromBlock"], 16), int(params[0]["toBlock"], 16)
            asked.append((lo, hi))
            return [log for blk, ls in logs_at.items() if lo <= blk <= hi for log in ls]
        if method == "eth_getBlockByNumber":
            return {"timestamp": hex(1788000000)}
        if method == "eth_getTransactionByHash":
            return {"value": hex(10**17)}
        raise AssertionError(f"unexpected call {method}")

    monkeypatch.setattr(m, "_rpc", fake_rpc)
    monkeypatch.setattr(m, "time", type("T", (), {"sleep": staticmethod(lambda s: None)}))
    return asked


def test_a_scan_that_fell_behind_resumes_where_it_stopped_instead_of_jumping_to_the_head(
    monkeypatch,
) -> None:
    """The fault that lost the purchase. After a long outage the watermark is far behind; the
    scan used to start near the head, skip everything in between, and then record the head as
    read — quietly burying every trade in the gap."""
    m = _mod()
    watermark = 44_932_826
    head = watermark + 58_315  # the real gap on the morning of 4-sep
    asked = _fake_chain(monkeypatch, m, head)
    _, scanned = m.hyperevm_trades(watermark + 1)
    assert asked, "no llegó a preguntar nada"
    assert asked[0][0] == watermark + 1, f"empezó en {asked[0][0]}, saltándose el hueco"
    assert scanned == head


def test_a_scan_too_far_behind_to_finish_records_only_the_ground_it_covered(monkeypatch) -> None:
    """A gap wider than one run's budget must be caught up across runs, never abandoned. Saving
    the head here is what turns a slow catch-up into permanent loss."""
    m = _mod()
    start = 40_000_000
    head = start + m.RPC_MAX_RANGE * m.RPC_MAX_CHUNKS * 3  # three runs' worth
    _fake_chain(monkeypatch, m, head)
    _, scanned = m.hyperevm_trades(start)
    assert scanned < head, "dijo haber leído hasta la cabeza sin haber llegado"
    assert scanned == start + m.RPC_MAX_RANGE * m.RPC_MAX_CHUNKS - 1


def test_a_purchase_sitting_in_the_gap_is_found_and_reported(monkeypatch) -> None:
    """The concrete case: the operator's own buy, 1.317.824 PDBT at block 44942765."""
    m = _mod()
    watermark, block = 44_932_826, 44_942_765
    buy = {
        "topics": [
            m.TRANSFER_TOPIC,
            "0x" + "0" * 24 + m.LIQUIDLAUNCH_CURVE[2:],
            "0x" + "0" * 24 + "804404c8d293197b76d9fc524d1ea25f830b12f1",
        ],
        "data": hex(1_317_824_300000),
        "blockNumber": hex(block),
        "transactionHash": "0x5bb5a6dc",
    }
    _fake_chain(monkeypatch, m, block + 100, {block: [buy]})
    trades, _ = m.hyperevm_trades(watermark + 1)
    assert len(trades) == 1
    assert trades[0].kind == "buy"
    assert round(trades[0].tokens) == 1_317_824


def test_a_scan_blind_for_hours_says_so_instead_of_looking_like_a_quiet_market(tmp_path) -> None:
    """The failure that made this invisible. Fifteen consecutive refusals produced no message of
    any kind, so silence read as "nobody is trading" — the one thing an alert must never do."""
    m = _mod()
    db = tmp_path / "ops.db"
    assert m.note_scan_health(db, "hyperevm", ok=False) is None  # one blip is not news
    assert m.note_scan_health(db, "hyperevm", ok=False) is None
    warning = m.note_scan_health(db, "hyperevm", ok=False)
    assert warning and "hyperevm" in warning.lower()
    # ...and it does not repeat itself every hour once it has been said
    assert m.note_scan_health(db, "hyperevm", ok=False) is None
    recovered = m.note_scan_health(db, "hyperevm", ok=True)
    assert recovered and ("recuper" in recovered.lower() or "vuelve" in recovered.lower())
    assert m.note_scan_health(db, "hyperevm", ok=True) is None  # healthy is not news either


# --- delivery, not intent (4-sep-2026) ---------------------------------------------------------
# `telegram()` has always returned whether the API accepted the message and nobody looked. The
# row was marked announced before the send was attempted, so a refusal buried the trade exactly
# the way the scan gap did — and the run printed "announced 1 trade(s)" either way.

CCC = {
    "data": [
        {
            "attributes": {
                "tx_hash": "0xccc",
                "block_timestamp": "2026-08-27T11:00:00Z",
                "kind": "buy",
                "volume_in_usd": "9.9",
                "from_token_amount": "3.0",
                "to_token_amount": "120000.0",
                "tx_from_address": "0xfeed",
            }
        }
    ]
}


def test_a_trade_stays_queued_until_telegram_actually_takes_it(tmp_path: pathlib.Path):
    m = _mod()
    db = tmp_path / "ops.db"
    m.record_and_select(db, m.parse_trades(PAYLOAD))  # first run: baseline, nothing to say
    assert m.pending_trades(db) == []

    m.record_and_select(db, m.parse_trades(CCC))
    assert [t.tx_hash for t in m.pending_trades(db)] == ["0xccc"]

    # a later run that finds nothing new must not lose the one still waiting
    m.record_and_select(db, [])
    assert [t.tx_hash for t in m.pending_trades(db)] == ["0xccc"]

    # and it survives the round trip through the database intact
    (queued,) = m.pending_trades(db)
    assert (queued.kind, queued.usd, queued.tokens, queued.chain) == ("buy", 9.9, 120000.0, "base")

    m.mark_announced(db, m.pending_trades(db))
    assert m.pending_trades(db) == []


def test_a_refused_send_is_retried_on_the_next_run(monkeypatch, tmp_path) -> None:
    """End to end through main(): Telegram says no, so the trade is still there afterwards."""
    m = _mod()
    db = tmp_path / "ops.db"
    payload = {"data": []}
    accepted: list[str] = []
    refused: list[str] = []

    class OnlySolana:
        def get(self, url, **k):
            if "solana" not in url:
                raise RuntimeError("base not under test here")
            return type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: payload})()

        def post(self, *a, **k):
            raise RuntimeError("hyperevm not under test here")

    monkeypatch.setattr(m, "httpx", OnlySolana())
    import sys as _sys

    monkeypatch.setitem(
        _sys.modules,
        "pedibot.settings",
        type("M", (), {"get_settings": staticmethod(lambda: type("S", (), {"ops_db_path": db})())}),
    )
    monkeypatch.setattr(m, "telegram", lambda t: refused.append(t) and False)
    m.main()  # baseline run, empty pool

    payload["data"] = list(CCC["data"])
    m.main()  # a real trade arrives, but the send is refused
    assert refused, "no llegó a intentar el envío"
    assert [t.tx_hash for t in m.pending_trades(db)] == ["0xccc"], "se dio por anunciada sin salir"

    monkeypatch.setattr(m, "telegram", lambda t: accepted.append(t) or True)
    payload["data"] = []  # the aggregator has already forgotten it; the outbox has not
    m.main()
    # the queued trade goes out; the other messages are the blindness warnings for the two
    # chains this test keeps broken on purpose, which is them working, not noise
    trade_msgs = [msg for msg in accepted if "0xccc" in msg]
    assert len(trade_msgs) == 1, accepted
    assert "COMPRA" in trade_msgs[0]
    assert m.pending_trades(db) == []


# --- la cadena de Robinhood (7-sep-2026) -------------------------------------------------------
# El operador lanzo PDBT en la L2 de Robinhood y pidio que entrara en las alertas de compra y
# venta "pero ni en la web ni nada". Las dos mitades de esa frase son requisitos, y las dos tienen
# su candado aqui: que las operaciones se lean y se anuncien, y que el contrato NO aparezca en
# ninguna parte publica.

ROBINHOOD_PAYLOAD = {
    "data": [
        {
            "attributes": {
                "tx_hash": "0xe29bdb2bb379c93d20e70a87398ef8e7bd1b0ed5584b4e4e972dc751f0e7b23b",
                "block_timestamp": "2026-09-07T08:27:42Z",
                "kind": "buy",
                "volume_in_usd": "22.42",
                "from_token_amount": "22.42",
                "to_token_amount": "5078920.51",
                "tx_from_address": "0x1111111111111111111111111111111111111111",
            }
        }
    ]
}


def test_a_robinhood_trade_is_tagged_and_not_filed_under_base():
    """Igual que Solana: sin pasar su cadena, el enlace apuntaria a Basescan, a un hash que no
    esta en Base."""
    m = _mod()
    (t,) = m.parse_trades(ROBINHOOD_PAYLOAD, chain="robinhood")
    assert t.chain == "robinhood"
    # PDBT es el token BASE del pool, asi que el `kind` ya viene desde nuestro punto de vista:
    # una compra es una compra y los PDBT son los que se RECIBEN. Comprobado en la API antes de
    # cablearlo, porque tomarlo al reves anunciaria cada compra como una venta.
    assert (t.kind, t.usd, t.tokens) == ("buy", 22.42, 5078920.51)


def test_the_robinhood_message_prices_the_trade_and_links_to_blockscout():
    m = _mod()
    text = m.format_message(m.parse_trades(ROBINHOOD_PAYLOAD, chain="robinhood"))
    assert "Robinhood" in text
    assert "22,42 USD" in text  # el agregador si conoce el precio aqui
    # Etherscan no indexa la cadena 4663. Blockscout es la fuente, y se comprobo que su pagina
    # carga de verdad (90 KB) antes de ponerla: HoodScan contesta 200 con el armazon vacio.
    assert "robinhoodchain.blockscout.com/tx/0xe29bdb2b" in text
    assert "basescan" not in text and "solscan" not in text


def test_the_first_robinhood_run_takes_a_baseline_instead_of_announcing_the_launch(
    monkeypatch, tmp_path
) -> None:
    """Cuando se cableo ya habia doce operaciones de las ultimas 24 h en el pool. Soltarlas todas
    en el primer sondeo diria que acaban de pasar."""
    m = _mod()
    db = tmp_path / "ops.db"
    sent: list[str] = []
    monkeypatch.setattr(m, "telegram", lambda t: sent.append(t) or True)
    payload = {"data": list(ROBINHOOD_PAYLOAD["data"])}

    class SoloRobinhood:
        def get(self, url, **k):
            if "robinhood" not in url:
                raise RuntimeError("las otras cadenas no se prueban aqui")
            return type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: payload})()

        def post(self, *a, **k):
            raise RuntimeError("hyperevm no se prueba aqui")

    monkeypatch.setattr(m, "httpx", SoloRobinhood())
    import sys as _sys

    monkeypatch.setitem(
        _sys.modules,
        "pedibot.settings",
        type("M", (), {"get_settings": staticmethod(lambda: type("S", (), {"ops_db_path": db})())}),
    )
    m.main()
    assert sent == [], sent
    assert m.scan_state(db, "robinhood") > 0  # visto una vez: la siguiente de verdad no se pierde

    payload["data"] = [
        {
            "attributes": {
                "tx_hash": "0xdeadbeefcafe0001",
                "block_timestamp": "2026-09-07T09:00:00Z",
                "kind": "sell",
                "volume_in_usd": "66.72",
                "from_token_amount": "15427613.37",
                "to_token_amount": "66.72",
                "tx_from_address": "0x2222222222222222222222222222222222222222",
            }
        }
    ]
    m.main()
    assert len(sent) == 1 and "VENTA" in sent[0] and "Robinhood" in sent[0]


def test_a_total_blackout_is_counted_not_hardcoded():
    """El codigo de salida decia `failures == 3` a mano. Con la cuarta cadena, un apagon completo
    habria salido con 0 — o sea, "todo bien" — y el vigilante lo habria dado por bueno."""
    m = _mod()
    fuente = (ROOT / "ops" / "token_alert.py").read_text(encoding="utf-8")
    assert "failures == len(WATCHED_CHAINS)" in fuente, "el numero de fuentes vuelve a estar a mano"
    assert len(m.WATCHED_CHAINS) == 4
    # y cada cadena que se mira tiene que saber decir de donde viene y adonde enlaza
    for c in m.WATCHED_CHAINS:
        assert c in m.CHAIN_LABEL, f"{c} sin nombre para el mensaje"
        assert c in m.EXPLORER, f"{c} sin enlace de explorador"


def test_the_robinhood_contract_stays_out_of_everything_public():
    """La otra mitad de lo que pidio el operador, y la que se olvida: "ni en la web ni nada".

    El token se retiro de la web por decision suya y no se vuelve a poner. Este candado recorre
    todo lo que se publica —la web, sus textos, las guias, la configuracion— y falla si el
    contrato de la cadena de Robinhood aparece en cualquiera de esos sitios. Vive en las alertas
    de operaciones y en ningun otro lugar.
    """
    contrato = "0xaac715d4d8555337e8dec34f174ecb8fb47c21eb"
    publico = [
        ROOT / "web" / "site" / "src",
        ROOT / "web" / "content",
        ROOT / "config",
    ]
    culpables = []
    for raiz in publico:
        if not raiz.exists():
            continue
        for f in raiz.rglob("*"):
            if not f.is_file() or f.suffix in (".png", ".jpg", ".woff2", ".ico", ".webp"):
                continue
            try:
                t = f.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                continue
            if contrato in t:
                culpables.append(str(f.relative_to(ROOT)))
    assert not culpables, f"el contrato de Robinhood no puede salir en la web: {culpables}"
