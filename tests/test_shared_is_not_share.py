"""«shared» no es «share» (30-sep-2026).

El extractor tira todo lo que lleve en la clase una pista de ruido, y «share» está en la lista
por los botones de compartir. Pero la búsqueda era por subcadena, y el Manual de Inmunizaciones
de la AEP guarda el capítulo entero dentro de `field-field-shared-body`: «**share**d». Del
capítulo de prematuros —el que dice «el prematuro debe ser vacunado de acuerdo con su edad
cronológica»— sólo quedó el menú, en un fragmento.

Las pistas se buscan ahora como palabra dentro de la clase, no como trozo de otra palabra.
"""

from __future__ import annotations

import pathlib

from pedibot.ingest.extract_html import extract_html

HTML = """<!doctype html><html><head><title>Prematuros</title></head><body>
<div class="field field-type-text field-field-shared-body">
  <h1>Inmunizaciones en niños prematuros</h1>
  <p>El prematuro debe ser vacunado de acuerdo con su edad cronológica, independientemente de
  su edad gestacional y de su peso al nacimiento.</p>
  <p>Es sumamente importante iniciar la vacunación a los 2 meses.</p>
</div>
<div class="service-links-facebook-share"><a href="#">Compartir en Facebook</a></div>
</body></html>"""


def _texto(tmp_path: pathlib.Path) -> str:
    f = tmp_path / "cap.html"
    f.write_text(HTML, encoding="utf-8")
    return " ".join(ln.text for pag in extract_html(f).pages for ln in pag.lines)


def test_el_cuerpo_shared_se_queda(tmp_path: pathlib.Path) -> None:
    assert "edad cronológica" in _texto(tmp_path)


def test_el_boton_de_compartir_se_sigue_tirando(tmp_path: pathlib.Path) -> None:
    assert "Compartir en Facebook" not in _texto(tmp_path)
