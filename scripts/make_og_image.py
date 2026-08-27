"""Generate the social preview image and the .ico favicon (26-ago-2026).

`og:image` pointed at /og.png, which did not exist: every link shared on WhatsApp, X or Bluesky
showed no preview. Run it again only if the brand changes:

    uv run python scripts/make_og_image.py

It writes web/site/public/og.png (1200x630, the size every platform crops from) and favicon.ico
(browsers ask for /favicon.ico even when an SVG icon is declared). The mark is the same speech
bubble as logo.svg, redrawn with primitives; the text is rendered to pixels, so the site carries
no font dependency.
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw, ImageFont

PUBLIC = pathlib.Path(__file__).resolve().parents[1] / "web" / "site" / "public"
GROUND, MINT, CREAM, SAGE, INK = "#FFFDF9", "#A9DED2", "#FFF8E7", "#2F6B57", "#2B3A35"
FONTS = pathlib.Path("C:/Windows/Fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for candidate in (name, "seguisb.ttf", "segoeui.ttf", "arial.ttf"):
        path = FONTS / candidate
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def bubble(d: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """The logo: a round speech bubble with a face, as in logo.svg."""
    u = size / 100
    d.ellipse([x + 6 * u, y + 6 * u, x + 94 * u, y + 94 * u], fill=MINT)
    d.polygon(
        [(x + 30 * u, y + 78 * u), (x + 12 * u, y + 96 * u), (x + 18 * u, y + 76 * u)], fill=MINT
    )
    d.ellipse([x + 26 * u, y + 24 * u, x + 80 * u, y + 76 * u], fill=CREAM)  # face
    d.ellipse([x + 20 * u, y + 44 * u, x + 32 * u, y + 56 * u], fill=CREAM)  # ear
    for cx in (43, 63):
        d.ellipse([x + (cx - 4) * u, y + 43 * u, x + (cx + 4) * u, y + 51 * u], fill=SAGE)  # eyes
    d.arc(
        [x + 42 * u, y + 48 * u, x + 64 * u, y + 66 * u],
        start=20,
        end=160,
        fill=SAGE,
        width=max(2, int(4.5 * u)),
    )  # smile
    d.arc(
        [x + 56 * u, y + 14 * u, x + 74 * u, y + 32 * u],
        start=200,
        end=20,
        fill=SAGE,
        width=max(2, int(5 * u)),
    )  # curl


def make_og() -> pathlib.Path:
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), GROUND)
    d = ImageDraw.Draw(img)
    d.rectangle([0, h - 14, w, h], fill=MINT)
    bubble(d, 96, 150, 300)
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


def make_favicon() -> pathlib.Path:
    base = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    bubble(ImageDraw.Draw(base), 0, 0, 256)
    out = PUBLIC / "favicon.ico"
    base.save(out, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    return out


if __name__ == "__main__":
    for path in (make_og(), make_favicon()):
        print(f"{path.relative_to(PUBLIC.parents[2])}  {path.stat().st_size / 1024:.0f} KB")
