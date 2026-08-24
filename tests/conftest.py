from __future__ import annotations

import os
from pathlib import Path

import pytest

# AVG on the dev machine injects SSLKEYLOGFILE and kills Python processes that open TLS (L06).
os.environ.pop("SSLKEYLOGFILE", None)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
FUENTES = ROOT / "FUENTES"


@pytest.fixture(scope="session")
def config_dir() -> Path:
    return CONFIG


@pytest.fixture(scope="session")
def fuentes_dir() -> Path:
    if not FUENTES.exists() or not any(FUENTES.rglob("*.pdf")):
        pytest.skip("FUENTES/ PDFs not available")
    return FUENTES
