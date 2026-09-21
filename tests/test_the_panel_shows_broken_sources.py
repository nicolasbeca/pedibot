"""Las fuentes rotas salen en el panel, ya no por Telegram (21-sep-2026)."""

from __future__ import annotations

import json

from pedibot.admin import _sources_card


def test_nothing_to_say_is_no_card(tmp_path) -> None:
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"checked": "2026-09-27T06:00:00+00:00", "lines": []}), "utf-8")
    assert _sources_card(f) == ""


def test_a_broken_source_is_a_card_with_the_date(tmp_path) -> None:
    f = tmp_path / "s.json"
    lineas = ["", "🔗 FUENTES ROTAS (1) — la web las enseña y no responden:", "  · MSCBS: 404"]
    f.write_text(json.dumps({"checked": "2026-09-27T06:00:00+00:00", "lines": lineas}), "utf-8")
    h = _sources_card(f)
    assert "Fuentes que revisar" in h
    assert "MSCBS: 404" in h
    assert "27 sep" in h


def test_never_run_yet_is_no_card(tmp_path) -> None:
    assert _sources_card(tmp_path / "no.json") == ""
