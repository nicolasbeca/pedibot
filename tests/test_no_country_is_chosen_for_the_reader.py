"""El selector de país del chat no elige por nadie (19-sep-2026).

El día que el proyecto se presenta en MetaDAO, repasando lo vivo, encontré esto en la portada:

    <select id="country"><option value="AE">AE</option><option value="AO">AO</option>…

Dos averías en una línea. La que se ve: **los códigos ISO pelados**, así que para elegir España
había que saberse la sigla y bajar por sesenta líneas de dos letras. La que no se ve y es la
grave: **no había opción vacía**, y un `<select>` sin opción vacía viene con la primera elegida
de fábrica. La primera, por orden alfabético del código, era AE. Emiratos Árabes Unidos.

Ese valor viajaba en cada pregunta de quien no tocara el desplegable, que es casi todo el
mundo. Medido contra lo desplegado ese mismo día, en castellano, con «mi bebé de 6 meses tiene
los labios azules y no responde»:

    país AE (el de fábrica) → «🚨 Llama ahora al 998 / 999»
    sin país                → «llama al número de emergencias de tu país (112 en la UE…)»
    país ES                 → «🚨 Llama ahora al 112»

Un padre en Madrid con el niño morado recibía un teléfono del Golfo, escrito en rojo y en
grande. La frase general no es peor que un número: es la que vale en cualquier sitio.

Esto se comprueba en lo CONSTRUIDO y no en el `.astro`, porque lo que le llega al padre es el
HTML, y porque la avería no estaba en ninguna línea escrita a mano: estaba en lo que hace un
navegador con un `<select>` al que nadie le dijo qué opción va primero.
"""

from __future__ import annotations

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DIST = RAIZ / "web" / "site" / "dist"

#: Una por idioma, porque el chat vive en el componente pero la página lo monta cada lengua.
PAGINAS = ["index.html", "es/index.html", "ar/index.html", "hi/index.html"]


def _select(html: str, ident: str) -> str:
    m = re.search(rf'<select id="{ident}".*?</select>', html, re.S)
    assert m, f'no hay <select id="{ident}"> en la página'
    return m.group(0)


@pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")
@pytest.mark.parametrize("rel", PAGINAS)
def test_the_first_option_picks_no_country(rel: str) -> None:
    f = DIST / rel
    assert f.exists(), f"falta {rel} en el build"
    sel = _select(f.read_text(encoding="utf-8"), "country")
    opciones = re.findall(r'<option value="([^"]*)"', sel)
    assert opciones, "el selector de país se quedó sin opciones"
    assert opciones[0] == "", (
        f"{rel}: el primer país del desplegable es «{opciones[0]}» y sale elegido de fábrica; "
        "quien no lo toque preguntará como si viviera allí"
    )


@pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")
@pytest.mark.parametrize("rel", PAGINAS)
def test_a_country_is_offered_by_its_name(rel: str) -> None:
    """Un desplegable que hay que descifrar no lo usa nadie: el nombre va escrito, en el idioma
    de la página, y la bandera delante para encontrarlo de un vistazo."""
    sel = _select((DIST / rel).read_text(encoding="utf-8"), "country")
    etiquetas = [e for e in re.findall(r"<option[^>]*>([^<]*)</option>", sel) if e.strip()]
    siglas = [e for e in etiquetas if re.fullmatch(r"[A-Z]{2}", e.strip())]
    assert not siglas, f"{rel}: hay países ofrecidos como sigla suelta: {siglas[:5]}"
    # la bandera son dos «regional indicator», U+1F1E6..U+1F1FF; en Windows se ven como letras,
    # pero en el móvil —de donde entra el público de India, los países árabes y África— no
    con_bandera = [e for e in etiquetas if re.search(r"[\U0001F1E6-\U0001F1FF]{2}", e)]
    assert len(con_bandera) >= len(etiquetas) - 1, (
        f"{rel}: {len(etiquetas) - len(con_bandera)} países sin bandera"
    )
