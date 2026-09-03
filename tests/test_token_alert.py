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
    fake = type("M", (), {"get_settings": staticmethod(lambda: type("S", (), {"ops_db_path": db})())})
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


def test_the_first_hyperevm_run_takes_a_baseline_instead_of_announcing_history(monkeypatch, tmp_path) -> None:
    """Without a watermark the first scan sees the curve's whole history. Announcing it would
    push last week's purchases as if they had just happened."""
    m = _mod()
    db = tmp_path / "ops.db"
    sent = []
    monkeypatch.setattr(m, "telegram", lambda t: sent.append(t) or True)
    old = m.Trade(
        tx_hash="0x" + "ee" * 32, ts="2026-09-01T10:00:00Z", kind="buy", usd=0.0,
        tokens=368.0, wallet="0x" + "11" * 20, chain="hyperevm", native=0.05,
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
        tx_hash="0x" + "ff" * 32, ts="2026-09-03T10:00:00Z", kind="sell", usd=0.0,
        tokens=10.0, wallet="0x" + "22" * 20, chain="hyperevm", native=None,
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
