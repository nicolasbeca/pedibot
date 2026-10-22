"""Cada página de vacunas resume su propio calendario (22-oct-2026).

Search Console, 8-oct: de las páginas de vacunas por país, /vaccines/us, /vaccines/es,
/vaccines/de y /vaccines/br estaban «rastreadas, sin indexar», todas con unas 340 palabras y una
tabla que es la del organismo oficial, que Google ya tiene. Lo que añade PediBot tiene que ser de
ese país y salir de esa tabla, no relleno: cuántas visitas, qué se pone al nacer, la visita con más
vacunas, la última y el total de dosis. Se calcula de config/vaccines.yaml (vía vaccines.json), sin
modelo, en las ocho lenguas.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"
SCHEDULES = json.loads((ROOT / "web" / "site" / "src" / "data" / "vaccines.json").read_text(encoding="utf-8"))


def _resumen(path: pathlib.Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    node = soup.select_one("[data-vax-summary]")
    assert node is not None, f"sin resumen: {path}"
    return node.get_text(" ", strip=True)


@pytest.mark.parametrize("code", ["US", "ES", "DE", "BR", "GB", "IN"])
def test_the_english_page_counts_its_own_visits_and_doses(code: str) -> None:
    data = SCHEDULES[code]
    visitas = len(data["schedule"])
    dosis = sum(len(r.get("vaccines") or []) for r in data["schedule"])
    texto = _resumen(DIST / "vaccines" / code.lower() / "index.html")
    assert f"{visitas} vaccination visits" in texto, texto
    assert f"{dosis} vaccines in the table" in texto, texto


@pytest.mark.parametrize("prefijo", ["es", "fr", "de", "ru", "ar", "pt", "hi"])
def test_every_language_has_it(prefijo: str) -> None:
    texto = _resumen(DIST / prefijo / "vaccines" / "us" / "index.html")
    assert str(len(SCHEDULES["US"]["schedule"])) in texto, texto
    assert "{" not in texto, "un hueco sin rellenar"


def test_birth_doses_are_named_when_there_are_any() -> None:
    texto = _resumen(DIST / "vaccines" / "us" / "index.html")
    assert "Hepatitis B" in texto
