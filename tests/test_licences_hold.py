"""La regla de licencias, comprobada contra el índice de verdad (8-sep-2026).

CLAUDE.md la escribe así:

    «cada documento tiene en el catálogo un campo `uso` ∈ {publico, citar_solo, excluido}.
     `excluido` (p. ej. el tratado de dermatología de Elsevier) no entra en el índice del bot
     público»

Es una regla con consecuencias legales y **se rompe en silencio**: nadie se entera de que un
documento con copyright editorial ha entrado en el índice hasta que alguien lo cita en una
respuesta pública. El catálogo dice una cosa, el índice guarda otra, y no había nada que
comparase las dos.

Estas comprobaciones necesitan el índice construido (`make ingest`); si no está, se saltan, que
es lo correcto en un clon limpio.
"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest
import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
INDICE = RAIZ / "index" / "pedibot.db"

pytestmark = pytest.mark.skipif(not INDICE.exists(), reason="sin índice construido (make ingest)")


def _catalogo() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for nombre in ("fuentes.yaml", "fuentes_web.yaml"):
        ruta = RAIZ / "config" / nombre
        if not ruta.exists():
            continue
        crudo = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        entradas = crudo.get("sources", crudo) if isinstance(crudo, dict) else crudo
        for d in entradas or []:
            if isinstance(d, dict) and d.get("doc_id"):
                out.setdefault(str(d["doc_id"]), d)
    return out


def _indice() -> dict[str, str]:
    con = sqlite3.connect(INDICE)
    try:
        return dict(con.execute("SELECT DISTINCT doc_id, usage FROM chunks"))
    finally:
        con.close()


def test_the_catalogue_and_the_index_are_both_there() -> None:
    """El candado del candado: si una de las dos listas se queda vacía, lo de abajo pasa solo."""
    cat, idx = _catalogo(), _indice()
    assert len(cat) > 200, f"el catálogo solo tiene {len(cat)} documentos"
    assert len(idx) > 200, f"el índice solo tiene {len(idx)} documentos"
    assert any(d.get("usage") == "excluido" for d in cat.values()), (
        "no hay ningún documento excluido en el catálogo: esta comprobación ya no comprueba nada"
    )


def test_no_excluded_document_reached_the_index() -> None:
    """La regla dura. Un tratado con copyright editorial dentro del índice es una respuesta
    pública citando material que no se puede redistribuir."""
    cat, idx = _catalogo(), _indice()
    dentro = [d for d, v in cat.items() if v.get("usage") == "excluido" and d in idx]
    assert not dentro, f"documentos EXCLUIDOS que están en el índice: {dentro}"


def test_every_indexed_document_declares_a_licence() -> None:
    """Un documento sin entrada en el catálogo no tiene licencia conocida, y el motor lo citaría
    igual que a los demás."""
    cat, idx = _catalogo(), _indice()
    huerfanos = sorted(d for d in idx if d not in cat)
    assert not huerfanos, f"documentos indexados sin entrada en el catálogo: {huerfanos}"


def test_the_catalogue_and_the_index_agree_on_the_licence() -> None:
    """Las dos copias del mismo dato: si se separan, la que decide es la del índice y nadie lo
    ve. Es el patrón del clon podrido aplicado a una regla legal."""
    cat, idx = _catalogo(), _indice()
    discrepan = [
        (d, cat[d].get("usage"), idx[d])
        for d in sorted(idx)
        if d in cat and cat[d].get("usage") != idx[d]
    ]
    assert not discrepan, f"el catálogo y el índice discrepan: {discrepan}"


def test_nothing_allowed_is_silently_missing() -> None:
    """El otro lado: un documento permitido que no llegó al índice es una fuente que el bot no
    puede citar sin que nadie lo haya decidido."""
    cat, idx = _catalogo(), _indice()
    faltan = sorted(d for d, v in cat.items() if v.get("usage") != "excluido" and d not in idx)
    assert not faltan, f"permitidos que no están en el índice: {faltan}"
