"""Sin red, la app encuentra lo guardado aunque la dirección lleve `?source=android` (1-oct-2026).

La app de Google Play abre la web con la marca `?source=android` (`appgoogle.md` §3). El service
worker guarda `/emergency` al instalarse, pero sin red buscaba la dirección exacta, con la marca,
y no la encontraba: en el emulador, en modo avión, el buscador de urgencias salía como «sin
conexión» mientras esa misma página decía que los números de emergencia funcionan sin red. La
marca que esconde las donaciones rompía justo lo que la app promete en su ficha.
"""

from __future__ import annotations

import re

from pedibot.settings import ROOT

SW = (ROOT / "web" / "site" / "public" / "sw.js").read_text(encoding="utf-8")


def test_the_offline_fallback_ignores_the_query() -> None:
    i = SW.index("sin red: primero esta misma página")
    trozo = SW[i : i + 400]
    assert "ignoreSearch: true" in trozo, trozo


def test_the_home_page_is_kept_on_install() -> None:
    cimientos = SW[SW.index("const CIMIENTOS") : SW.index("];", SW.index("const CIMIENTOS"))]
    assert re.search(r"^\s*'/',", cimientos, re.M), "la app arranca en / y tiene que abrir sin red"


def test_the_cache_version_moved_on() -> None:
    """Sin cambiar la versión, los móviles que ya tienen el trabajador viejo no se enteran."""
    assert "const VERSION = 'pedibot-v2'" not in SW
