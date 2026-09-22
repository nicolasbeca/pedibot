"""La tarjeta que se ve al compartir el enlace (22-sep-2026).

El operador: «las tarjetas tienen el logo antiguo, por cierto. Podrían ser más espectaculares».
`make_icons.py` sacaba desde el 19-sep todos los iconos del logo de verdad y la tarjeta no: se
había quedado con el dibujo a mano que lo imitaba.

Y al rehacerla cometí en dos minutos el error que él acababa de señalar en el logo original de
la carpeta: recorté el fondo por umbral de claridad, se fue también el crema del interior de la
cara, y el bebé salió **verde sobre verde**. Por eso el candado mira un píxel del centro de la
cara: si vuelve a fundirse con el fondo, esto falla.
"""

from __future__ import annotations

import importlib.util

from PIL import Image

from pedibot.settings import ROOT


def _generador():  # noqa: ANN202 — el script vive fuera del paquete, como los demás de scripts/
    spec = importlib.util.spec_from_file_location("make_og", ROOT / "scripts" / "make_og.py")
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


TARJETA = ROOT / "web" / "site" / "public" / "og.png"


def test_it_is_the_size_a_card_has_to_be() -> None:
    with Image.open(TARJETA) as img:
        assert img.size == (1200, 630)


def test_the_face_is_not_green_on_green() -> None:
    """El centro de la cara es crema claro, y el fondo de al lado es verde hondo."""
    with Image.open(TARJETA) as img:
        rgb = img.convert("RGB")
        cara = rgb.getpixel((300, 300))
        fondo = rgb.getpixel((1150, 60))
    assert isinstance(cara, tuple) and isinstance(fondo, tuple)
    assert min(cara) > 200, f"el interior de la cara salió oscuro: {cara}"
    assert max(fondo) < 120, f"el fondo salió claro: {fondo}"


def test_every_colour_it_paints_clears_the_contrast_bar() -> None:
    """Lo que comprueba el propio generador, comprobado también aquí."""
    m = _generador()

    assert m.contraste(m.CREMA, m.VERDE_MEDIO) >= 4.5
    assert m.contraste(m.MENTA, m.VERDE_MEDIO) >= 4.5
    assert m.contraste(m.MENTA_VIVA, m.VERDE_HONDO) >= 4.5


def test_the_card_in_the_repo_is_the_one_the_script_makes() -> None:
    """Si alguien cambia el logo y no regenera la tarjeta, esto falla — que es el fallo que
    estuvo tres días vivo."""
    import io

    hecha = io.BytesIO()
    _generador().construye().save(hecha, format="PNG", optimize=True)
    assert hecha.getvalue() == TARJETA.read_bytes(), "la tarjeta del repo no es la del logo de hoy"
