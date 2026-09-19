"""Todos los iconos, sacados del logo de verdad (19-sep-2026).

El operador: «tienes este logo en la carpeta LOGOS. Has usado a veces uno inventado de la cara
sin texto en la web». Era cierto: `web/site/public/logo.svg` es un dibujo mío que se le parece,
con el bocadillo y la cara en otro sitio. Esto deja de dibujar y usa el archivo suyo.

La trampa de este logo concreto, y por eso no vale un «blanco a transparente» de una línea: **la
cara del bebé es crema, (255, 249, 235), que está a seis niveles del blanco del fondo**. Cualquier
umbral que borre el fondo se come la cara. Lo que se hace es una inundación desde las cuatro
esquinas —como la varita mágica— que sólo alcanza el blanco que está conectado con el borde, así
que la cara, rodeada de menta, se queda.

De aquí salen los iconos de la web y los de la app, del mismo archivo y con el mismo recorte, que
es lo que hace que no se separen con el tiempo.
"""

from __future__ import annotations

import pathlib
import sys
from collections import deque

from PIL import Image

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "LOGOS" / "LOGO_PEDIBOT_CARA.jpg"
WEB = RAIZ / "web" / "site" / "public"
APP = RAIZ / "app" / "assets"

#: Cuánto se aparta del blanco puro un píxel para seguir contando como fondo. La cara crema está
#: a 6 niveles, así que el umbral va por debajo de eso y además sólo se aplica a lo conectado
#: con el borde.
TOLERANCIA = 12
#: Aire alrededor del dibujo, en tanto por uno del lado. Los iconos de las tiendas se ven mal
#: pegados al borde y iOS además les recorta las esquinas.
MARGEN = 0.06


def _fondo_fuera(im: Image.Image) -> Image.Image:
    """El blanco que toca el borde se vuelve transparente. El de dentro, no."""
    im = im.convert("RGBA")
    ancho, alto = im.size
    px = im.load()
    visto = bytearray(ancho * alto)
    cola: deque[tuple[int, int]] = deque()

    def blanco(x: int, y: int) -> bool:
        r, g, b, _ = px[x, y]
        return r >= 255 - TOLERANCIA and g >= 255 - TOLERANCIA and b >= 255 - TOLERANCIA

    for x in range(ancho):
        for y in (0, alto - 1):
            if blanco(x, y):
                cola.append((x, y))
    for y in range(alto):
        for x in (0, ancho - 1):
            if blanco(x, y):
                cola.append((x, y))
    while cola:
        x, y = cola.popleft()
        i = y * ancho + x
        if visto[i]:
            continue
        visto[i] = 1
        px[x, y] = (255, 255, 255, 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < ancho and 0 <= ny < alto and not visto[ny * ancho + nx] and blanco(nx, ny):
                cola.append((nx, ny))
    return im


def _cuadrado(im: Image.Image, margen: float = MARGEN) -> Image.Image:
    """Recorta lo dibujado, lo centra en un cuadrado y le deja aire."""
    caja = im.getbbox()
    recorte = im.crop(caja)
    lado = int(max(recorte.size) * (1 + margen * 2))
    lienzo = Image.new("RGBA", (lado, lado), (255, 255, 255, 0))
    lienzo.paste(
        recorte,
        ((lado - recorte.width) // 2, (lado - recorte.height) // 2),
        recorte,
    )
    return lienzo


def _sobre_fondo(im: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    """La misma imagen sobre un color, para donde la transparencia no vale (iOS, og:image)."""
    fondo = Image.new("RGBA", im.size, (*color, 255))
    fondo.alpha_composite(im)
    return fondo.convert("RGB")


def main() -> int:
    if not ORIGEN.exists():
        print(f"no encuentro {ORIGEN}", file=sys.stderr)
        return 1
    limpio = _cuadrado(_fondo_fuera(Image.open(ORIGEN)))
    WEB.mkdir(parents=True, exist_ok=True)
    (APP).mkdir(parents=True, exist_ok=True)
    hechos: list[str] = []

    def guarda(destino: pathlib.Path, lado: int, fondo: tuple[int, int, int] | None = None) -> None:
        img = limpio.resize((lado, lado), Image.LANCZOS)
        if fondo is not None:
            img = _sobre_fondo(img, fondo)
        destino.parent.mkdir(parents=True, exist_ok=True)
        img.save(destino)
        hechos.append(f"{destino.relative_to(RAIZ)} ({lado}px)")

    # ── la web ────────────────────────────────────────────────────────────────────────────────
    guarda(WEB / "logo.png", 512)
    guarda(WEB / "logo-192.png", 192)
    # apple-touch-icon no admite transparencia: iOS la pinta de negro
    guarda(WEB / "apple-touch-icon.png", 180, fondo=(255, 255, 255))
    limpio.resize((256, 256), Image.LANCZOS).save(
        WEB / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)]
    )
    hechos.append("web/site/public/favicon.ico (16/32/48)")

    # ── la app ────────────────────────────────────────────────────────────────────────────────
    guarda(APP / "icon-1024.png", 1024, fondo=(255, 255, 255))  # App Store y Play
    guarda(APP / "icon.png", 512)
    guarda(APP / "adaptive-foreground.png", 432)  # Android adaptativo
    guarda(APP / "splash.png", 512)
    for lado in (48, 72, 96, 144, 192):
        guarda(APP / f"android/mipmap-{lado}.png", lado)

    print(f"{len(hechos)} ficheros desde {ORIGEN.name}:")
    for h in hechos:
        print("  ", h)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
