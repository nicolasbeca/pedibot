"""El CSS de un componente no alcanza lo que pinta JavaScript (19-sep-2026).

El operador mandó pantallazos de la ficha de su hijo y se veía tosca: las etiquetas pegadas a los
campos, las medidas sin rejilla, las curvas ocupando media pantalla. No era cuestión de gusto.

**Astro limita el CSS de cada componente al HTML que escribe él**: le pone a cada etiqueta un
`data-astro-cid-…` y reescribe los selectores para que sólo casen con eso. Las fichas de los
hijos las pinta el navegador con `innerHTML`, así que nacen sin ese atributo y **no les llegaba
ni una regla**. Medido en lo construido antes de arreglarlo: cero reglas para `.kid`,
`.medidas`, `.vacunas`, `.curva`, `.rejilla` y `.f`.

Lo peor es que ya estaba escrito en este repositorio, en `Chat.astro`, con su comentario: las
burbujas del chat usan `:global(...)` por exactamente esto. Lo tenía delante.

Esta prueba mira lo construido, que es donde se ve: por cada clase que sólo existe dentro del
`<script>` de un componente, tiene que haber una regla en el CSS que salga de él.
"""

from __future__ import annotations

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
SITE = RAIZ / "web" / "site"
DIST = SITE / "dist"

pytestmark = pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")

#: Clases que sólo existen porque las escribe el JavaScript de su componente, y el componente
#: donde viven. Si una deja de tener estilo, la pantalla se ve rota y nadie recibe un error.
PINTADAS_POR_JS = {
    "Family": ["kid", "curvas", "curva", "medidas", "vacunas", "rejilla", "siguiente"],
    "Chat": ["msg", "banner", "sources", "conquien"],
}


def _css_de(componente: str) -> str:
    hojas = list((DIST / "_astro").glob(f"{componente}.*.css"))
    if not hojas:
        # Astro puede fundir la hoja de un componente en la del layout cuando es pequeña
        hojas = list((DIST / "_astro").glob("*.css"))
    return "\n".join(h.read_text(encoding="utf-8") for h in hojas)


@pytest.mark.parametrize(
    ("componente", "clase"),
    [(c, k) for c, clases in PINTADAS_POR_JS.items() for k in clases],
)
def test_a_class_drawn_by_javascript_still_has_its_rules(componente: str, clase: str) -> None:
    css = _css_de(componente)
    assert re.search(rf"\.{re.escape(clase)}[\s.,:{{\[]", css), (
        f"{componente}: la clase «{clase}» la pinta el navegador y no tiene ni una regla en el "
        "CSS construido. Le falta `:global(...)`, como en Chat.astro"
    )


def test_the_rule_is_written_down_where_it_will_be_read() -> None:
    """Un comentario en el sitio donde se vuelve a tropezar vale más que esta prueba."""
    familia = (SITE / "src" / "components" / "Family.astro").read_text(encoding="utf-8")
    assert ":global(" in familia
    assert "innerHTML" in familia
    assert "data-astro-cid" in familia, (
        "el porqué tiene que estar escrito al lado del estilo, no sólo en una prueba"
    )
