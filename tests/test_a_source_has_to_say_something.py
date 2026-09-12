"""Una fuente tiene que decir algo, y llamarse por su nombre (12-sep-2026).

Salió tirando del hilo de los tres temas hindi que seguían citando hojas españolas. Mirando qué
material inglés había —que lo hay, y bueno— aparecieron dos cosas que no son de ranking sino de
integridad del corpus:

1. **`nhs_en_breath_holding_in_babies_and_children` se titulaba «This page has been removed».**
   El contenido indexado está bien —«Breath-holding is when a baby or child stops breathing for
   up to 1 minute and may faint…», 578 palabras—; lo que el recolector se trajo mal fue el
   título. Y el título es **justo lo que el padre ve en la cita**: `NHS — "This page has been
   removed"` debajo de una respuesta sobre su hijo.

2. **Dos «fuentes» del NHS eran índices de navegación.** `nhs_en_ibuprofen_for_children`, 59
   palabras, cuyo texto entero es «Find out how ibuprofen for children treats pain… About
   ibuprofen / Who can and cannot take it / How and when to give it / Side effects» — o sea, los
   nombres de las pestañas. **Ni una dosis.** Y `nhs_en_caring_for_a_newborn`, 49 palabras, una
   lista de enlaces. Las dos se habían citado ya a alguien: el registro de producción las tiene.

La diferencia con los 22 documentos cortos de MedlinePlus es de naturaleza, no de tamaño: aquéllos
son resúmenes breves con frases de verdad; éstos son tablas de contenidos. El suelo se pone en
**60 palabras**, que es donde la medición separa unos de otros (49 y 59 contra 69 y más).

El título se arregló a mano el mismo día. Los dos índices de navegación **no**, y el motivo es
parte de la lección: al marcarlos `excluido` cayeron **siete candados** —hay guías publicadas
que los citan como ancla, y sacarles la fuente de debajo las deja huérfanas—. O sea que quitar
una fuente del catálogo no es una línea de YAML: es una operación con consecuencias aguas abajo.
El arreglo bueno tampoco es excluirlos sino **traerse el contenido de verdad**: las páginas de
medicamentos del NHS reparten el texto en pestañas (`/how-and-when-to-give-it`), y el recolector
sólo se trajo la portada. Queda apuntado con nombre y apellidos en `CONOCIDOS`, para que el
candado pille los que aparezcan **nuevos** y no se coma el aviso de éstos.
"""

from __future__ import annotations

import collections
import json
import re
import sqlite3

import pytest
import yaml

from pedibot.settings import ROOT

INDICE = ROOT / "index" / "pedibot.db"

#: Cómo se llama una página que ya no es una página. Un título así llega tal cual a la cita.
PAGINA_MUERTA = re.compile(
    r"page (has been |was )?(removed|moved|not found)|no longer available|"
    r"\b404\b|access denied|"
    r"página (no encontrada|no disponible|ha sido retirada)|"
    r"sorry, (we )?(can.t find|the page)",
    re.I,
)

#: Por debajo de esto no hay documento: hay un índice de navegación (medido: 49 y 59 palabras
#: contra 69 del más corto de MedlinePlus, que sí dice algo).
SUELO_PALABRAS = 60


def _catalogo() -> dict[str, dict]:
    fuera: dict[str, dict] = {}
    for f in ("fuentes.yaml", "fuentes_web.yaml"):
        for d in yaml.safe_load((ROOT / "config" / f).read_text(encoding="utf-8"))["sources"]:
            fuera[d["doc_id"]] = d
    return fuera


def _palabras_por_doc() -> dict[str, int]:
    con = sqlite3.connect(f"file:{INDICE}?mode=ro", uri=True)
    try:
        largo: dict[str, int] = collections.defaultdict(int)
        for doc_id, data in con.execute("SELECT doc_id, data FROM chunks"):
            largo[doc_id] += len((json.loads(data).get("text") or "").split())
        return dict(largo)
    finally:
        con.close()


def test_ninguna_fuente_se_llama_como_una_pagina_muerta():
    """El título va en la cita: es lo que el padre lee debajo de la respuesta sobre su hijo."""
    malos = [
        (doc_id, d.get("title", ""))
        for doc_id, d in _catalogo().items()
        if PAGINA_MUERTA.search(str(d.get("title") or ""))
    ]
    assert not malos, (
        "estas fuentes se citarían con un título que dice que la página ya no existe; el "
        f"contenido puede estar bien, el título no: {malos}"
    )


#: Los que ya están y hay que arreglar trayéndose sus sub-páginas, no excluyéndolos: hay guías
#: publicadas ancladas en ellos. Con la fecha, para que no se queden aquí de adorno.
CONOCIDOS = {
    "nhs_en_ibuprofen_for_children": "12-sep-2026: falta /how-and-when-to-give-it",
    "nhs_en_caring_for_a_newborn": "12-sep-2026: falta el texto de las secciones",
}


def test_ningun_documento_indexado_es_un_indice_de_navegacion():
    if not INDICE.exists():
        pytest.skip("sin índice en esta copia")
    largo = _palabras_por_doc()
    cat = _catalogo()
    stubs = sorted(
        (n, d)
        for d, n in largo.items()
        if n < SUELO_PALABRAS
        and d not in CONOCIDOS
        and (cat.get(d) or {}).get("usage") != "excluido"
    )
    assert not stubs, (
        f"documentos con menos de {SUELO_PALABRAS} palabras indexadas: su texto es una lista de "
        f"enlaces, no una fuente, y aun así se pueden citar: {stubs}"
    )


def test_y_el_catalogo_no_promete_lo_que_el_indice_no_tiene():
    """Una entrada de catálogo sin nada indexado es una promesa vacía."""
    if not INDICE.exists():
        pytest.skip("sin índice en esta copia")
    largo = _palabras_por_doc()
    vacios = sorted(
        d
        for d, e in _catalogo().items()
        if e.get("usage") != "excluido" and d in largo and largo[d] == 0
    )
    assert not vacios, f"documentos en el catálogo con cero palabras indexadas: {vacios}"
