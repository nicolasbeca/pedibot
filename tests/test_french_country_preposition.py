"""«Courbe de croissance en Tchad» (30-sep-2026).

En francés el país lleva «en», «au» o «aux» según su género y número: «en France», «au Tchad»,
«aux États-Unis». Las frases de la curva por país escribían «en {country}» para los 79, así que
salían «en Canada», «en Brésil» o «en Tchad» en el título que enseña Google. Se reescriben sin
preposición; esto fija que no vuelva.
"""

from __future__ import annotations

import pathlib

import pytest

DIST = pathlib.Path(__file__).resolve().parents[1] / "web" / "site" / "dist" / "fr" / "growth"
MASCULINOS = ("en Tchad", "en Canada", "en Brésil", "en Portugal", "en Japon", "en Mexique")


def test_la_curva_francesa_no_dice_en_tchad():
    if not DIST.exists():
        pytest.skip("el sitio no está construido en esta copia")
    malos = []
    for p in sorted(DIST.rglob("index.html")):
        texto = p.read_text(encoding="utf-8")
        malos += [(p.parent.name, m) for m in MASCULINOS if m in texto]
    assert not malos, f"preposición equivocada: {malos[:6]}"
