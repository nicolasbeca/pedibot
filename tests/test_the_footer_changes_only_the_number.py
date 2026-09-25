"""Un pie de página no deja de serlo porque cambie el número (25-sep-2026).

El limpiador quita las líneas que se repiten en casi todas las páginas —cabeceras y pies— porque
no son contenido. Compara el texto tal cual, así que

    Calendario común de vacunación … | Página 1 de 3
    Calendario común de vacunación … | Página 2 de 3
    Calendario común de vacunación … | Página 3 de 3

le parecen tres líneas distintas, cada una vista una sola vez, y las tres se quedan dentro.

Se vio persiguiendo por qué cualquier pregunta sobre una vacuna concreta —«la vacuna del
rotavirus», «sus efectos secundarios», «cuándo se pone»— devolvía siempre el mismo pasaje: la
leyenda de la tabla del calendario español, 232 palabras de «Administración sistemática», «Con
rayas» y el pie repetido, que no contestan nada.

Comparar con los números sustituidos por un hueco no cambia qué se considera un pie: sigue
haciendo falta que aparezca en la mayoría de las páginas.
"""

from __future__ import annotations

from pedibot.ingest.clean import repeated_lines
from pedibot.ingest.extract import Extracted, Line, PageText


def _pdf(paginas: list[list[str]]) -> Extracted:
    return Extracted(
        path=None,  # type: ignore[arg-type]
        sha256="x",
        pages=[
            PageText(number=i + 1, lines=[Line(text=t, size=10.0) for t in lineas])
            for i, lineas in enumerate(paginas)
        ],
        body_size=10.0,
    )


def test_a_footer_with_a_page_number_is_still_a_footer() -> None:
    ex = _pdf(
        [
            ["Calendario común de vacunación | Página 1 de 3", "A los 2 meses: hexavalente."],
            ["Calendario común de vacunación | Página 2 de 3", "A los 4 meses: hexavalente."],
            ["Calendario común de vacunación | Página 3 de 3", "A los 12 meses: triple vírica."],
        ]
    )
    fuera = repeated_lines(ex)
    assert any("calendario común" in x for x in fuera), fuera
    assert not any("hexavalente" in x for x in fuera), "el contenido no se toca"


def test_a_line_that_happens_to_carry_a_number_is_not_a_footer() -> None:
    """Dos páginas con una cifra distinta no hacen un pie: tiene que estar en casi todas."""
    ex = _pdf(
        [
            ["A los 2 meses: hexavalente.", "Pie del documento"],
            ["A los 4 meses: hexavalente.", "Pie del documento"],
            ["Otra cosa distinta aquí.", "Pie del documento"],
        ]
    )
    fuera = repeated_lines(ex)
    assert any("pie del documento" in x for x in fuera)
    assert not any("meses" in x for x in fuera), fuera


def test_short_documents_are_left_alone() -> None:
    """Con dos páginas no hay suficiente para decir que algo es un pie."""
    ex = _pdf([["Página 1 de 2", "Texto."], ["Página 2 de 2", "Más texto."]])
    assert repeated_lines(ex) == set()
