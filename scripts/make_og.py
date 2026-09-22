"""La tarjeta que se ve cuando alguien comparte el enlace (22-sep-2026).

El operador, mirando una en WhatsApp: «las tarjetas tienen el logo antiguo, por cierto. Podrían
ser más espectaculares». Las dos cosas eran ciertas. `make_icons.py` saca desde el 19-sep todos
los iconos del logo de verdad —`LOGOS/LOGO_PEDIBOT_CARA.jpg`— pero **la tarjeta no**: se quedó
con el dibujo a mano que la imitaba, sobre crema, con la cara pequeña y una frase fina que en la
miniatura de un móvil no se lee.

Lo que se ve de una tarjeta en una lista de mensajes es del tamaño de un sello. Así que:

- fondo oscuro, que es lo que la separa de la línea de tiempo (y de las otras tarjetas, que en
  salud son todas blancas);
- la cara del logo grande, la de verdad, sobre un halo claro para que no se funda con el fondo;
- el nombre enorme, y debajo UNA frase, no dos;
- y la prueba, que es lo que PediBot tiene y nadie más pone en una tarjeta: los nombres de los
  organismos de los que sale cada respuesta.

Cada color se comprueba contra el fondo antes de dibujarlo (`contraste`), porque el aviso vino
de ver el logo original de la carpeta, donde «pedibot» está escrito en verde sobre verde y no se
lee. Un texto que no llega a 4,5:1 no se pinta: falla el script.
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "LOGOS" / "LOGO_PEDIBOT_CARA.jpg"
FUENTES = RAIZ / "scripts" / "fonts"
DESTINOS = (RAIZ / "web" / "site" / "public" / "og.png", RAIZ / "app" / "www" / "og.png")

ANCHO, ALTO = 1200, 630

# La paleta del sitio (`web/site/src/styles/global.css`), lado oscuro.
VERDE_HONDO = (18, 46, 38)
VERDE_MEDIO = (31, 79, 64)
CREMA = (255, 246, 234)
MENTA = (200, 233, 224)
MENTA_VIVA = (141, 209, 190)


def _luminancia(c: tuple[int, int, int]) -> float:
    def canal(v: int) -> float:
        x = v / 255
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = (canal(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """La razón de contraste de la WCAG entre dos colores."""
    la, lb = _luminancia(a), _luminancia(b)
    claro, oscuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (oscuro + 0.05)


def _fuente(nombre: str, tamano: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FUENTES / f"{nombre}.ttf"), tamano)


def _fondo() -> Image.Image:
    """Verde hondo con una luz en diagonal, que es lo que le da profundidad al sello."""
    base = Image.new("RGB", (ANCHO, ALTO), VERDE_HONDO)
    px = base.load()
    assert px is not None
    for y in range(ALTO):
        for x in range(0, ANCHO, 2):
            # la diagonal va de arriba-izquierda (más claro) a abajo-derecha
            t = (x / ANCHO * 0.65 + (1 - y / ALTO) * 0.35) ** 1.6
            c = tuple(int(VERDE_HONDO[i] + (VERDE_MEDIO[i] - VERDE_HONDO[i]) * t) for i in range(3))
            px[x, y] = c
            if x + 1 < ANCHO:
                px[x + 1, y] = c
    return base.filter(ImageFilter.GaussianBlur(1.2))


def _halo(lienzo: Image.Image, centro: tuple[int, int], radio: int) -> None:
    """Una luz detrás de la cara: sin esto, el verde del logo se funde con el verde del fondo."""
    capa = Image.new("L", (ANCHO, ALTO), 0)
    d = ImageDraw.Draw(capa)
    d.ellipse(
        [centro[0] - radio, centro[1] - radio, centro[0] + radio, centro[1] + radio],
        fill=90,
    )
    capa = capa.filter(ImageFilter.GaussianBlur(radio // 3))
    lienzo.paste(Image.new("RGB", (ANCHO, ALTO), MENTA_VIVA), (0, 0), capa)


def _cara(lado: int) -> Image.Image:
    """El logo de verdad, recortado como en `make_icons.py`: el JPG trae fondo blanco."""
    img = Image.open(ORIGEN).convert("RGB")
    # El fondo que sobra es el blanco que ROZA EL BORDE, no todo lo claro: el interior de la
    # cara es crema (#FFF6EA, casi 250) y una máscara por umbral se lo lleva por delante. Se
    # rellena desde las cuatro esquinas y se quita sólo lo que está conectado con ellas.
    plano = img.copy()
    for esquina in (
        (0, 0),
        (img.width - 1, 0),
        (0, img.height - 1),
        (img.width - 1, img.height - 1),
    ):
        ImageDraw.floodfill(plano, esquina, (255, 0, 255), thresh=18)
    mascara = Image.new("L", img.size, 255)
    px_plano, px_mascara = plano.load(), mascara.load()
    assert px_plano is not None and px_mascara is not None
    for y in range(img.height):
        for x in range(img.width):
            if px_plano[x, y] == (255, 0, 255):
                px_mascara[x, y] = 0
    caja = mascara.getbbox()
    assert caja is not None, "el logo salió vacío al recortarlo"
    img, mascara = img.crop(caja), mascara.crop(caja)
    lado_original = max(img.size)
    cuadro = Image.new("RGBA", (lado_original, lado_original), (0, 0, 0, 0))
    cuadro.paste(
        img,
        ((lado_original - img.width) // 2, (lado_original - img.height) // 2),
        mascara,
    )
    return cuadro.resize((lado, lado), Image.LANCZOS)


def _chips(d: ImageDraw.ImageDraw, x: int, y: int, nombres: list[str]) -> None:
    """Los organismos, en cápsulas. Es la promesa del producto dicha sin adjetivos."""
    fuente = _fuente("Nunito-ExtraBold", 27)
    for nombre in nombres:
        ancho = d.textlength(nombre, font=fuente)
        d.rounded_rectangle([x, y, x + ancho + 34, y + 50], radius=25, fill=(255, 255, 255, 255))
        assert contraste(VERDE_MEDIO, (255, 255, 255)) > 4.5
        d.text((x + 17, y + 25), nombre, font=fuente, fill=VERDE_MEDIO, anchor="lm")
        x += int(ancho) + 34 + 14


def construye() -> Image.Image:
    lienzo = _fondo()
    _halo(lienzo, (300, 300), 250)

    cara = _cara(360)
    lienzo.paste(cara, (120, 120), cara)

    d = ImageDraw.Draw(lienzo)
    fondo_texto = VERDE_MEDIO  # el más claro de la zona del texto, que es el caso peor

    titulo = _fuente("Nunito-ExtraBold", 108)
    assert contraste(CREMA, fondo_texto) >= 4.5, "el título no se leería"
    assert 560 + d.textlength("PediBot", font=titulo) < ANCHO - 60, "el título se sale"
    d.text((560, 150), "PediBot", font=titulo, fill=CREMA, anchor="lt")

    claim = _fuente("Nunito-SemiBold", 38)
    assert contraste(MENTA, fondo_texto) >= 4.5, "la frase no se leería"
    for i, linea in enumerate(("What the guidelines say", "about your child, tonight.")):
        assert 560 + d.textlength(linea, font=claim) < ANCHO - 60, f"se sale: {linea}"
        d.text((560, 284 + i * 52), linea, font=claim, fill=MENTA, anchor="lt")

    _chips(d, 560, 420, ["WHO", "NHS", "CDC", "AEP"])

    pie = _fuente("AtkinsonHyperlegible-Regular", 27)
    assert contraste(MENTA_VIVA, VERDE_HONDO) >= 4.5, "el pie no se leería"
    linea_pie = (
        "pedibot.xyz  ·  free, no account  ·  8 languages  ·  every sentence shows its source"
    )
    assert 120 + d.textlength(linea_pie, font=pie) < ANCHO - 60, "el pie se sale"
    d.text((120, 540), linea_pie, font=pie, fill=MENTA_VIVA, anchor="lt")
    return lienzo


def main() -> int:
    tarjeta = construye()
    for destino in DESTINOS:
        destino.parent.mkdir(parents=True, exist_ok=True)
        tarjeta.save(destino, optimize=True)
        print(
            f"{destino.relative_to(RAIZ)} ({tarjeta.width}×{tarjeta.height}, "
            f"{destino.stat().st_size / 1024:.1f} kB)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
