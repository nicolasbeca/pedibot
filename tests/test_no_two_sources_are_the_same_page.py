"""Dos fuentes no pueden ser el mismo documento (24-sep-2026).

El NHS unificó sus páginas de medicamentos: `/medicines/paracetamol-for-children/about-…/`,
`/…/side-effects-of-…/` y las demás **ya no existen como páginas separadas** y redirigen todas a
`/medicines/paracetamol-for-children/`. El recolector las siguió sin rechistar y se trajo **seis
copias byte a byte** del paracetamol y otras seis del ibuprofeno.

No es sólo que sobren doce documentos en el catálogo. Es que el índice los puntúa por separado:
una pregunta sobre paracetamol recuperaba tres pasajes idénticos, que desplazaban a tres fuentes
distintas que sí tenían algo que añadir, y la respuesta citaba «[1] [2] [3]» siendo la misma
hoja tres veces.

Un fichero que llega por una redirección no avisa de nada. El hash sí.
"""

from __future__ import annotations

import collections
import hashlib
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
WEB = RAIZ / "FUENTES" / "web"


@pytest.mark.skipif(not WEB.is_dir(), reason="sin fuentes descargadas")
def test_no_two_downloaded_sources_are_byte_identical() -> None:
    por_hash: dict[str, list[str]] = collections.defaultdict(list)
    for f in sorted(WEB.glob("*.html")):
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        por_hash[h].append(f.name)

    repetidos = {h: n for h, n in por_hash.items() if len(n) > 1}
    assert not repetidos, (
        "estas fuentes son el mismo documento descargado con varios nombres —casi siempre porque"
        " el sitio unificó sus páginas y las viejas redirigen a una sola—, y el índice las"
        f" puntúa por separado: {[n for n in repetidos.values()]}"
    )
