"""Las direcciones viejas de las guías (16-sep-2026).

Regenerar una guía le cambia el título y, con él, el nombre del fichero. Eso se conserva —así se
arreglaron slugs mal transliterados— pero la dirección vieja es lo que Google tiene indexado y lo
que alguien tiene enlazado: no puede quedarse en nada. El 16-sep se regeneraron 118 guías de una
tanda, así que esto pasó de ser un detalle a ser casi todo el sitio.

La lista vive en `web/content/_redirects.json`, la escribe el publicador cada vez que renombra, y
tiene dos consumidores: **Caddy**, que las sirve como 301 (lo que Google respeta sin discusión), y
**Astro**, que además genera la página vieja con su `canonical`. Antes había dos listas —un bloque
a mano en el Caddyfile y lo que reescribía `dedupe_guides.py`, que borraba lo que no conociera—.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAPA = ROOT / "web" / "content" / "_redirects.json"
CADDY = ROOT / "ops" / "Caddyfile"
DIST = ROOT / "web" / "site" / "dist"


def mapa() -> dict[str, str]:
    return json.loads(MAPA.read_text(encoding="utf-8")) if MAPA.exists() else {}


def test_ninguna_redireccion_apunta_a_una_pagina_que_no_existe() -> None:
    """Una redirección rota es peor que ninguna: el lector acaba en un 404 con dos saltos."""
    guias = {
        f"{'' if d.name == 'en' else '/' + d.name}/guides/{f.stem}"
        for d in (ROOT / "web" / "content").iterdir()
        if d.is_dir()
        for f in d.glob("*.md")
    }
    rotas = {v for v in mapa().values() if v not in guias}
    assert not rotas, f"redirecciones a guías que ya no existen: {sorted(rotas)[:5]}"


def test_ninguna_guia_viva_esta_redirigida() -> None:
    """El origen de una redirección tiene que ser una dirección MUERTA."""
    guias = {
        f"{'' if d.name == 'en' else '/' + d.name}/guides/{f.stem}"
        for d in (ROOT / "web" / "content").iterdir()
        if d.is_dir()
        for f in d.glob("*.md")
    }
    vivas = {k for k in mapa() if k in guias}
    assert not vivas, f"guías vivas que además se redirigen: {sorted(vivas)[:5]}"


def test_no_hay_cadenas_de_dos_saltos() -> None:
    m = mapa()
    encadenadas = {k: v for k, v in m.items() if v in m}
    assert not encadenadas, f"redirecciones que llevan a otra redirección: {encadenadas}"


def test_el_servidor_las_sirve_como_301() -> None:
    """Astro genera una página con meta refresh; Google la respeta, pero un 301 no se discute."""
    texto = CADDY.read_text(encoding="utf-8")
    en_caddy = dict(re.findall(r"redir (/\S+) (/\S+) permanent", texto))
    faltan = {k: v for k, v in mapa().items() if en_caddy.get(k) != v}
    assert not faltan, (
        f"{len(faltan)} redirecciones no están en el Caddyfile; "
        "pasa `uv run python scripts/sync_redirects.py --apply`"
    )


@pytest.mark.skipif(not DIST.is_dir(), reason="sin sitio construido")
def test_y_el_sitio_construido_tambien() -> None:
    faltan = [
        viejo
        for viejo in mapa()
        if not (DIST / viejo.strip("/") / "index.html").exists()
        and not (DIST / f"{viejo.strip('/')}.html").exists()
    ]
    assert not faltan, f"{len(faltan)} direcciones viejas sin página en el build: {faltan[:3]}"
