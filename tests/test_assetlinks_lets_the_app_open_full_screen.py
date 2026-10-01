"""`assetlinks.json`: lo que hace que la app de Android abra la web a pantalla completa (1-oct-2026).

La app de Google Play es pedibot.xyz abierta por Chrome (TWA, `appgoogle.md`). Chrome sólo quita
la barra de direcciones si la web declara que esa app es suya, con la huella SHA-256 de la clave
que la firma. Sin esto la app abre con la barra arriba, que es justo lo que Play rechaza como
«una web envuelta». Hay dos claves: la de SUBIDA (la nuestra, la que está aquí desde el primer
día) y la que pone Google con Play App Signing, que se añade cuando exista la cuenta.
"""

from __future__ import annotations

import json
import re

from pedibot.settings import ROOT

FICHERO = ROOT / "web" / "site" / "public" / ".well-known" / "assetlinks.json"
HUELLA = re.compile(r"^([0-9A-F]{2}:){31}[0-9A-F]{2}$")


def _declaracion() -> dict:
    datos = json.loads(FICHERO.read_text(encoding="utf-8"))
    assert isinstance(datos, list) and len(datos) == 1
    return datos[0]


def test_it_names_our_app() -> None:
    d = _declaracion()
    assert d["relation"] == ["delegate_permission/common.handle_all_urls"]
    assert d["target"]["namespace"] == "android_app"
    assert d["target"]["package_name"] == "xyz.pedibot.app"


def test_the_fingerprints_are_well_formed() -> None:
    huellas = _declaracion()["target"]["sha256_cert_fingerprints"]
    assert huellas, "sin huella, la app abre con la barra de direcciones"
    assert all(HUELLA.match(h) for h in huellas), huellas


def test_the_app_package_matches_the_twa_manifest() -> None:
    twa = json.loads((ROOT / "app" / "twa" / "twa-manifest.json").read_text(encoding="utf-8"))
    assert twa["packageId"] == _declaracion()["target"]["package_name"]
