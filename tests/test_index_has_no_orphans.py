"""Nada en el índice sin licencia registrada (11-sep-2026).

Al ampliar el corpus de la OMS aparecieron **cuatro documentos en el índice sin entrada de
catálogo**: `cdc_en_colds`, `cdc_en_ear_infection` y las dos de vacunación infantil de
MedlinePlus. Eran sobras de un renombrado: el mismo contenido vive hoy bajo otro identificador
(`mlp_en_childhoodvaccines`), y las piezas viejas seguían ahí porque **la ingesta sólo añade**.

Por qué importa, y no es burocracia: el catálogo es donde vive el campo `usage`
—`publico` / `citar_solo` / `excluido`—. Un documento sin entrada no tiene licencia registrada, y
sin embargo el buscador lo recupera y el bot lo cita. Es exactamente el agujero que la regla de
licencias existe para cerrar, abierto por el lado por el que nadie mira. Una auditoría del 8-sep
dio «0 huérfanos», así que se coló después y en silencio.

Se mira el índice contra los DOS catálogos, que es de donde salen todas las entradas.
"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
INDEX = ROOT / "index" / "pedibot.db"


def _catalogados() -> set[str]:
    ids: set[str] = set()
    for nombre in ("fuentes.yaml", "fuentes_web.yaml"):
        d = yaml.safe_load((ROOT / "config" / nombre).read_text(encoding="utf-8"))
        filas = d.get("sources") if isinstance(d, dict) else d
        if filas is None:
            filas = list(d.values()) if isinstance(d, dict) else []
        ids |= {x["doc_id"] for x in filas}
    return ids


def _en_el_indice() -> set[str]:
    con = sqlite3.connect(f"file:{INDEX}?mode=ro", uri=True)
    try:
        return {r[0] for r in con.execute("SELECT DISTINCT doc_id FROM chunks")}
    finally:
        con.close()


def test_todo_lo_indexado_tiene_licencia_registrada():
    if not INDEX.exists():
        pytest.skip("sin índice en esta copia")
    huerfanos = sorted(_en_el_indice() - _catalogados())
    assert not huerfanos, (
        "estos documentos se pueden recuperar y citar y no tienen entrada de catálogo, así que "
        "nadie sabe con qué licencia: borra sus .jsonl de index/chunks/ y vuelve a ingerir, o "
        f"dales entrada. {huerfanos}"
    )


def test_el_catalogo_no_promete_lo_que_el_indice_no_tiene():
    """La dirección contraria avisa de otra cosa: una fuente catalogada que nunca se ingirió.

    No es un fallo por sí sola —hay tres `excluido` a propósito y alguna puede estar sin
    descargar—, así que sólo se vigila que no se dispare: si un día son decenas, es que la
    ingesta lleva tiempo fallando en silencio.
    """
    if not INDEX.exists():
        pytest.skip("sin índice en esta copia")
    sin_ingerir = _catalogados() - _en_el_indice()
    assert len(sin_ingerir) <= 8, (
        f"{len(sin_ingerir)} fuentes catalogadas y no indexadas; si no es deliberado, la "
        f"ingesta está fallando: {sorted(sin_ingerir)[:10]}"
    )
