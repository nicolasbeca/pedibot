"""La página de fuentes enlaza a quien nos lo pidió al darnos permiso (1-oct-2026).

Vikaspedia, en su permiso: «It would be preferred if you can also provide a backlink to
Vikaspedia at appropriate places». En el agradecimiento nos comprometimos a ponerlo en la página
de fuentes. Immunize.org pide enlazar su web y sus PDF. El encabezado de cada organización en
/sources (las ocho lenguas usan el mismo componente) lleva a su web. Condiciones: ops/PERMISOS.md.
"""

from __future__ import annotations

import yaml

from pedibot.settings import ROOT

TABLA = ROOT / "web" / "site" / "src" / "components" / "SourcesTable.astro"


def _org_full(org: str) -> str:
    for nombre in ("fuentes.yaml", "fuentes_web.yaml"):
        datos = yaml.safe_load((ROOT / "config" / nombre).read_text(encoding="utf-8"))
        docs = datos if isinstance(datos, list) else next(
            v for v in datos.values() if isinstance(v, list)
        )
        for d in docs:
            if d["org"] == org:
                return d["org_full"]
    raise AssertionError(f"{org} no está en el catálogo")


def test_vikaspedia_heading_links_to_vikaspedia() -> None:
    fuente = TABLA.read_text(encoding="utf-8")
    assert f"'{_org_full('Vikaspedia')}': 'https://vikaspedia.in/'" in fuente


def test_immunize_heading_links_to_immunize() -> None:
    fuente = TABLA.read_text(encoding="utf-8")
    assert f"'{_org_full('Immunize.org')}': 'https://www.immunize.org/'" in fuente


def test_the_heading_uses_the_link() -> None:
    fuente = TABLA.read_text(encoding="utf-8")
    assert "ORG_HOME[org]" in fuente and "<a href={ORG_HOME[org]}" in fuente
