"""Ninguna página puede pedirle nada a un tercero (11-sep-2026).

`/legal` promete que el sitio no hace peticiones a otros dominios, y esa promesa sólo vale si
alguien la comprueba. La escribió un caso real: la insignia de una competición de startups, que
se sirvió desde nuestro dominio precisamente para no entregar la dirección IP de cada padre a
otra empresa a cambio de una imagen decorativa. La insignia se retiró el 2-sep-2026 después de
medirla —veinte visitantes en siete días y ni una sola consulta al bot— y sus dos ficheros se
han borrado hoy, a petición del operador.

Lo que se queda es la regla, que vale para cualquier insignia, tipografía o script que venga
después: **si hace falta un recurso de fuera, se copia y se sirve desde aquí**.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"
SRC = ROOT / "web" / "site" / "src"

#: de dónde puede cargar recursos una página: de sí misma y de nadie más
_EXTERNO = re.compile(r"""(?:src|href)\s*=\s*["']https?://(?!pedibot\.xyz)([a-z0-9.-]+)""", re.I)
#: enlaces que un humano pulsa a propósito (nuestras cuentas, las fuentes citadas) no son
#: peticiones automáticas: lo que se prohíbe es que el navegador salga solo
_CARGA = re.compile(
    r"""<(?:img|script|link|iframe|video|audio|source|embed)\b[^>]*?(?:src|href)\s*=\s*["']"""
    r"""https?://(?!pedibot\.xyz)([a-z0-9.-]+)""",
    re.I,
)


def test_ninguna_pagina_construida_carga_nada_de_fuera():
    paginas = sorted(DIST.rglob("index.html"))
    if not paginas:
        import pytest

        pytest.skip("el sitio no está construido en esta copia")
    culpables: dict[str, set[str]] = {}
    for p in paginas:
        fuera = set(_CARGA.findall(p.read_text(encoding="utf-8")))
        if fuera:
            culpables[str(p.relative_to(DIST))] = fuera
    assert not culpables, (
        "estas páginas le piden un recurso a otro dominio, y /legal promete que no: "
        f"{sorted(culpables.items())[:4]}"
    )


def test_no_queda_ni_rastro_de_la_insignia_retirada():
    assert not list((SRC / ".." / "public").resolve().glob("launchleague*")), (
        "los ficheros de la insignia siguen ahí"
    )
    for f in SRC.rglob("*.astro"):
        assert "launchleague" not in f.read_text(encoding="utf-8").lower(), f
