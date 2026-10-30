"""Cada punto de una lista termina donde termina (30-oct-2026).

Prueba en vivo: «My 6 week old has a temperature of 38.2» contestó «Do not give them in too many
clothes». La página del NHS dice bien «do not cover them up in too many clothes or bedclothes»,
pero la ingesta pegaba los `<li>` con un espacio y el pasaje quedaba como una sola frase sin un
signo: «…too many clothes or bedclothes do not give aspirin to children under 16…». El redactor
cosió dos puntos en uno.

Ahora un punto de lista sin puntuación final se cierra con «;» al unir el texto. Con «;» y no con
«.»: el separador de frases no corta por él, así que los pasajes no cambian de límites ni de
número, y los `source_chunk` de las reglas siguen apuntando a lo mismo. Y se pone al unir, no en la
línea: una línea que acaba en «;» deja de poder ser un encabezado.
"""

from __future__ import annotations

import pathlib

from pedibot.ingest.clean import clean
from pedibot.ingest.extract_html import extract_html
from pedibot.ingest.sections import split_sections
from pedibot.settings import get_settings

HTML = """<!doctype html><html><head><title>High temperature</title></head><body><main>
<h1>High temperature (fever) in children</h1>
<h2>Don't</h2>
<ul>
  <li>do not undress your child or sponge them down to cool them</li>
  <li>do not cover them up in too many clothes or bedclothes</li>
  <li>do not give aspirin to children under 16 years of age.</li>
  <li>Is it serious?</li>
</ul>
<p>Read more about giving medicines to babies and children, and when to get help for a
child with a high temperature that is not going down.</p>
</main></body></html>"""


def _texto(tmp_path: pathlib.Path) -> str:
    f = tmp_path / "fiebre.html"
    f.write_text(HTML, encoding="utf-8")
    # por `clean`, como en la ingesta: la primera versión del arreglo se perdía ahí, que rehace
    # cada línea, y el índice no cambió
    return " ".join(s.text for s in split_sections(clean(extract_html(f))))


def test_los_puntos_de_la_lista_no_se_pegan(tmp_path: pathlib.Path) -> None:
    t = _texto(tmp_path)
    assert "to cool them; do not cover them up" in t, t
    assert "or bedclothes; do not give aspirin" in t, t


def test_lo_que_ya_tiene_puntuacion_no_se_toca(tmp_path: pathlib.Path) -> None:
    t = _texto(tmp_path)
    assert "16 years of age. Is it serious? Read more" in t, t
    assert ".;" not in t and "?;" not in t


def test_los_parrafos_siguen_como_estaban(tmp_path: pathlib.Path) -> None:
    assert "babies and children, and when to get help" in _texto(tmp_path)


def test_el_pasaje_del_nhs_ya_tiene_sus_bordes() -> None:
    import pytest

    from pedibot.index.store import Index

    s = get_settings()
    if not s.index_db_path.exists():
        pytest.skip("sin índice")
    t = Index(s.index_db_path).get("nhs_en_fever_in_children#don_t#1").text
    assert "too many clothes or bedclothes; do not give aspirin" in t, t[:300]
