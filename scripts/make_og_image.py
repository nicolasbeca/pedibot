"""La tarjeta que se ve al compartir un enlace (26-ago-2026; el logo real, 19-sep-2026).

`og:image` apuntaba a /og.png, que no existía: cada enlace compartido en WhatsApp, X o Bluesky
salía sin imagen. Se vuelve a lanzar sólo si cambia la marca:

    uv run python scripts/make_icons.py && uv run python scripts/make_og_image.py

Escribe web/site/public/og.png (1200x630, el tamaño del que recorta cualquier plataforma).

**Hasta hoy la cara la dibujaba yo con elipses y arcos**, copiando de memoria un logo que ya
existía en LOGOS/. Se parecía, y por eso tardó en verse: el bocadillo era redondo con el rabo
pegado abajo a la izquierda, la cara estaba descentrada y la oreja sobraba. Ahora se pega
`web/site/public/logo.png`, que sale del JPG del operador, así que esta imagen y el icono del
navegador no pueden volver a separarse. El texto sigue yendo a píxeles, para que el sitio no
arrastre una dependencia de fuentes.

El favicon ya no se hace aquí: lo escribe `scripts/make_icons.py`, con los demás tamaños.
"""

from __future__ import annotations

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

PUBLIC = pathlib.Path(__file__).resolve().parents[1] / "web" / "site" / "public"
LOGO = PUBLIC / "logo.png"
GROUND, MINT, SAGE, INK = "#FFFDF9", "#A9DED2", "#2F6B57", "#2B3A35"
FONTS = pathlib.Path("C:/Windows/Fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for candidate in (name, "seguisb.ttf", "segoeui.ttf", "arial.ttf"):
        path = FONTS / candidate
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def make_og() -> pathlib.Path:
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), GROUND)
    d = ImageDraw.Draw(img)
    d.rectangle([0, h - 14, w, h], fill=MINT)
    marca = Image.open(LOGO).convert("RGBA").resize((330, 330), Image.LANCZOS)
    img.paste(marca, (86, 146), marca)
    d.text((470, 196), "PediBot", font=font("seguisb.ttf", 96), fill=INK)
    d.text(
        (476, 318),
        "Paediatric answers for parents,\nstraight from published guidelines.",
        font=font("segoeui.ttf", 40),
        fill=SAGE,
        spacing=14,
    )
    d.text(
        (476, 452),
        "pedibot.xyz · free · not medical advice",
        font=font("segoeui.ttf", 28),
        fill="#7C8A84",
    )
    out = PUBLIC / "og.png"
    img.save(out, "PNG", optimize=True)
    return out


if __name__ == "__main__":
    if not LOGO.exists():
        print("falta logo.png: lanza antes scripts/make_icons.py", file=sys.stderr)
        raise SystemExit(1)
    path = make_og()
    print(f"{path.relative_to(PUBLIC.parents[2])}  {path.stat().st_size / 1024:.0f} KB")
