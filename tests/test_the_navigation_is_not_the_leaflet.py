"""El menú del sitio no es el contenido de la hoja (23-sep-2026).

Las fichas de Familia y Salud entraron con su plantilla dentro: cada una abría con «Noticias
Quienes somos Se encuentra usted aquí» y cerraba con «Divulga la Web: Cartel-recortable Cartel
con bidi…», que son el menú y el pie de la web. Eso no es información para un padre, y peor: es
texto que el motor puede acabar citando como si lo fuera.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from pedibot.settings import ROOT

BD = ROOT / "index" / "pedibot.db"

#: Lo que es plantilla y nunca es contenido, con el sitio del que viene cada frase.
PLANTILLA = ("Divulga la Web", "Se encuentra usted aquí", "Quienes somos Se encuentra")


@pytest.mark.skipif(not BD.exists(), reason="sin índice construido")
@pytest.mark.parametrize("frase", PLANTILLA)
def test_no_chunk_is_made_of_navigation(frase: str) -> None:
    c = sqlite3.connect(BD)
    filas = c.execute("select chunk_id, data from chunks where data like ?", (f"%{frase}%",))
    culpables = [
        cid for cid, data in filas if frase.lower() in json.loads(data)["text"][:400].lower()
    ]
    assert not culpables, f"«{frase}» dentro del texto de: {culpables[:5]}"
