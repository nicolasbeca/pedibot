"""Quitar una fuente del catálogo tiene que quitarla del índice (24-sep-2026).

`test_index_has_no_orphans` comprueba una dirección: que el catálogo no prometa documentos que
el índice no tiene. Faltaba la otra, y es la que tiene consecuencias: **que el índice no guarde
documentos que el catálogo ya no tiene**.

Se vio al retirar trece fuentes duplicadas. Se quitaron del recolector, se borraron sus ficheros,
se regeneró el catálogo y se reindexó con `--force`… y las trece seguían dentro, con sus pasajes
intactos y disponibles para ser citadas. `--force` rehace lo que encuentra; no borra lo que ya
no está.

Por qué importa más de lo que parece: una fuente se retira por tres motivos, y en los tres el
documento tiene que desaparecer de verdad —porque su licencia no permite redistribuirla, porque
el organismo la retiró, o porque ha dejado de ser cierta—. Un índice que la conserva convierte
las tres decisiones en un gesto vacío.
"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest
import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
INDICE = RAIZ / "index" / "pedibot.db"

pytestmark = pytest.mark.skipif(not INDICE.exists(), reason="sin índice construido")


def _catalogados() -> set[str]:
    out: set[str] = set()
    for nombre in ("fuentes.yaml", "fuentes_web.yaml"):
        ruta = RAIZ / "config" / nombre
        if not ruta.exists():
            continue
        crudo = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        entradas = crudo.get("sources", crudo) if isinstance(crudo, dict) else crudo
        for d in entradas or []:
            if isinstance(d, dict) and d.get("doc_id"):
                out.add(str(d["doc_id"]))
    return out


def test_the_index_holds_nothing_the_catalogue_has_dropped() -> None:
    con = sqlite3.connect(INDICE)
    indexados = {r[0] for r in con.execute("SELECT DISTINCT doc_id FROM chunks")}
    sobrantes = sorted(indexados - _catalogados())
    assert not sobrantes, (
        "estos documentos están en el índice y ya no están en el catálogo, así que el motor"
        " puede citarlos y nadie los vigila: reconstruye el índice desde cero"
        f" (`make reindex`). {sobrantes[:10]}"
    )
