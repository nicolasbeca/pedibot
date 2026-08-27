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
