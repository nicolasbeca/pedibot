"""Un selector escrito dos veces en el mismo fichero se contradice en silencio (20-sep-2026).

Repasando la cartilla de vacunación: `.vacunas li` estaba definido **dos veces** en
`Family.astro`, una arriba con `align-items: flex-start` y otra doscientas líneas más abajo con
`align-items: baseline` y `flex-wrap: wrap`. Gana la de abajo, que es la que ya existía, así que
la casilla de 44 píxeles se alineaba por la línea base del texto —torcida— y con el nombre de
vacuna largo se iba a su propia fila.

No hay error, no hay aviso, y en la pantalla no se ve *mal*: se ve *raro*, que es peor, porque
nadie sabe decir qué mirar.

El candado no prohíbe repetir un selector —hay motivos buenos: una consulta de medios, el modo
noche, un estado— sino **repetirlo declarando dos veces la misma propiedad de maquetación**. Ahí
una de las dos siempre sobra, y la que sobra es la que alguien escribió sin saber que la otra
existía.
"""

from __future__ import annotations

import re

import pytest

from pedibot.settings import ROOT

COMPONENTES = ROOT / "web" / "site" / "src"

#: Las propiedades donde una segunda declaración cambia dónde se pinta algo. El color o el
#: tamaño de letra se pisan a propósito todo el rato; `display` y `align-items`, no.
DE_MAQUETA = ("display", "align-items", "flex-wrap", "flex-direction", "position", "grid-template")

#: `<style>` de un .astro. Se mira sólo el CSS, no la plantilla ni el script.
_ESTILO = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
#: Una regla: selector y cuerpo. Sin anidar, que Astro no lo admite (L190).
_REGLA = re.compile(r"([^{}@]+)\{([^{}]*)\}")


def _reglas(css: str) -> list[tuple[str, str]]:
    """Las reglas de fuera de cualquier `@media`: dentro, repetir es lo normal y es correcto."""
    sin_media: list[str] = []
    profundidad = 0
    bloque: list[str] = []
    for trozo in re.split(r"(@media[^{]*\{|\}|\{)", css):
        if trozo.startswith("@media"):
            profundidad += 1
            continue
        if profundidad:
            if trozo == "{":
                profundidad += 1
            elif trozo == "}":
                profundidad -= 1
            continue
        bloque.append(trozo)
    sin_media.append("".join(bloque))
    fuera = []
    for sel, cuerpo in _REGLA.findall("".join(sin_media)):
        limpio = " ".join(sel.split())
        if limpio and not limpio.startswith(("@", "from", "to", "%")):
            fuera.append((limpio, cuerpo))
    return fuera


def _ficheros() -> list:
    return sorted(COMPONENTES.rglob("*.astro"))


@pytest.mark.parametrize("fichero", _ficheros(), ids=lambda f: f.name)
def test_ningun_selector_declara_dos_veces_la_misma_propiedad(fichero) -> None:
    texto = fichero.read_text(encoding="utf-8")
    choques: list[str] = []
    for css in _ESTILO.findall(texto):
        vistos: dict[tuple[str, str], int] = {}
        for selector, cuerpo in _reglas(css):
            for prop in DE_MAQUETA:
                if re.search(rf"(?:^|;|\s){prop}\s*:", cuerpo):
                    clave = (selector, prop)
                    vistos[clave] = vistos.get(clave, 0) + 1
                    if vistos[clave] == 2:
                        choques.append(f"«{selector}» declara «{prop}» dos veces")
    assert not choques, (
        f"{fichero.name}: dos reglas se contradicen y gana la de abajo, sin aviso:\n  "
        + "\n  ".join(sorted(set(choques)))
    )


def test_el_candado_encuentra_el_choque_que_hubo(tmp_path) -> None:
    """Con las dos reglas de `.vacunas li` tal y como estaban ayer.

    Un candado que no se prueba a sí mismo es una función que devuelve una lista vacía.
    """
    fichero = tmp_path / "Prueba.astro"
    fichero.write_text(
        "<div class='fam'></div>\n"
        "<style>\n"
        "  .fam :global(.vacunas li) { display: flex; align-items: flex-start; gap: 10px; }\n"
        "  .fam :global(.otra) { color: red; }\n"
        "  .fam :global(.vacunas li) { display: flex; align-items: baseline; flex-wrap: wrap; }\n"
        "</style>\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError) as e:
        test_ningun_selector_declara_dos_veces_la_misma_propiedad(fichero)
    assert "align-items" in str(e.value)


def test_el_candado_deja_en_paz_una_consulta_de_medios(tmp_path) -> None:
    """Repetir un selector dentro de `@media` es lo normal y es correcto: ahí cada uno manda en
    su tamaño de pantalla. Un candado que también fuera a por eso se desactivaría en una tarde."""
    fichero = tmp_path / "Prueba.astro"
    fichero.write_text(
        "<div></div>\n"
        "<style>\n"
        "  .x { display: flex; }\n"
        "  @media (width <= 520px) { .x { display: block; } }\n"
        "</style>\n",
        encoding="utf-8",
    )
    test_ningun_selector_declara_dos_veces_la_misma_propiedad(fichero)
