"""The watchdog must notice when one of our own systemd units is down (26-ago-2026).

`ops/` is a scripts directory, not a package, so we load the module by path.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _watchdog():
    spec = importlib.util.spec_from_file_location("wd", ROOT / "ops" / "watchdog.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wd"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_all_active_means_no_problem():
    wd = _watchdog()
    assert wd.dead_units(status_of=lambda _u: "active") == []


def test_inactive_unit_is_reported():
    wd = _watchdog()
    dead = wd.dead_units(status_of=lambda u: "failed" if u == "pedibot-acp" else "active")
    assert dead == ["pedibot-acp"]


def test_unknown_status_counts_as_dead():
    """A systemctl call that errors out must not be read as healthy."""
    wd = _watchdog()
    assert wd.dead_units(status_of=lambda _u: "unknown") == list(wd.UNITS)


def test_the_units_we_actually_run_are_watched():
    wd = _watchdog()
    assert {"pedibot-api", "pedibot-telegram", "pedibot-acp", "caddy"} <= set(wd.UNITS)
