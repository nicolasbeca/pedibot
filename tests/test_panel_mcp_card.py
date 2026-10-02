"""El panel cuenta las llamadas por MCP (2-oct-2026).

El servidor MCP se monta para ver si algún asistente nos llama. Sin la cifra en el panel sería
otra cosa que creer en vez de comprobar: el agente de ACP pasó dieciocho días con cero trabajos
sin que nada lo enseñara. Cero también es una medida, así que la tarjeta sale aunque no haya
llamadas.
"""

from __future__ import annotations

import datetime as dt
import json

from pedibot.admin import _mcp_card


def _write(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def test_the_card_counts_calls_clients_and_tools(tmp_path):
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    log = tmp_path / "mcp_uso.jsonl"
    _write(log, [
        {"ts": f"{today} 10:00:00", "tool": "child_medicine_dose", "client": "claude-ai", "no_data": False},
        {"ts": f"{today} 11:00:00", "tool": "child_medicine_dose", "client": "cursor", "no_data": True},
        {"ts": f"{today} 12:00:00", "tool": "oral_rehydration_plan", "client": "claude-ai", "no_data": False},
        {"ts": "2026-01-01 12:00:00", "tool": "oral_rehydration_plan", "client": "x", "no_data": False},
    ])
    last_day = _mcp_card(1, log)
    assert "3 llamadas" in last_day
    assert "2 clientes" in last_day
    assert "1 sin dato" in last_day
    assert "child_medicine_dose" in last_day and "claude-ai" in last_day
    assert "4 llamadas" in _mcp_card(0, log)


def test_zero_is_shown_too(tmp_path):
    card = _mcp_card(0, tmp_path / "missing.jsonl")
    assert "0 llamadas" in card
    assert "https://pedibot.xyz/mcp" in card
