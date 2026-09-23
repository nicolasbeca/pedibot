"""Un ancla vacía con el id bueno no es el contenido de la página (23-sep-2026).

Al traer las fichas de Familia y Salud (AEPap) la ingesta las rechazó las cuatro con
«no_text scanned or protected PDF — needs OCR», que ya de entrada es un mensaje equivocado para
un HTML. El motivo: su plantilla abre con

    <a id="main-content"></a>

y el extractor recorre sus selectores en orden, encuentra `#main-content` y se queda con él.
Como está vacío, la página entera —8.700 caracteres— se perdía detrás de un ancla de accesibilidad
de cero caracteres.

Se elige el primer selector que traiga texto de verdad, no el primero que exista.
"""

from __future__ import annotations

import pathlib

from pedibot.ingest.extract_html import extract_html

HTML = """<!doctype html><html><head><title>Antitérmicos</title></head><body>
<a id="main-content"></a>
<div class="region">
  <h1>Antitérmicos para la fiebre</h1>
  <p>Se podría repetir la dosis si el niño vomita antes de 10 a 15 minutos tras la ingesta.</p>
  <p>El ibuprofeno no se debe dar cuando hay vómitos continuados, según esta ficha.</p>
</div>
</body></html>"""


def test_the_text_behind_the_empty_anchor_is_found(tmp_path: pathlib.Path) -> None:
    f = tmp_path / "ficha.html"
    f.write_text(HTML, encoding="utf-8")
    texto = " ".join(ln.text for pag in extract_html(f).pages for ln in pag.lines)
    assert "repetir la dosis" in texto, texto[:200]
    assert "vómitos continuados" in texto, texto[:200]


def test_a_real_main_still_wins(tmp_path: pathlib.Path) -> None:
    """Y cuando el contenedor bueno tiene texto, se sigue prefiriendo a `body` entero."""
    f = tmp_path / "ficha.html"
    f.write_text(
        "<html><body><nav>menú que no queremos</nav>"
        "<main><p>Lo que dice la ficha de verdad, con su frase entera.</p></main>"
        "</body></html>",
        encoding="utf-8",
    )
    texto = " ".join(ln.text for pag in extract_html(f).pages for ln in pag.lines)
    assert "de verdad" in texto
    assert "menú" not in texto
