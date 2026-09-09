"""Todo lo que el motor cuelga bajo una respuesta tiene que existir (9-sep-2026).

Un enlace roto debajo de una respuesta no es un detalle de mantenimiento: es la promesa del
producto —«te llevo a donde lo explico»— rota justo cuando el padre iba a comprobarnos.

Se comprueba contra el sitio CONSTRUIDO, que es lo que se despliega. En un clon sin build, se
salta: no tiene sentido pedirle a nadie que construya el sitio para correr los tests.

De 555 enlaces (8 a la calculadora, 64 al calendario y 483 a guías) no había ninguno roto. Se
queda porque el día que alguien renombre una ruta, lo que se rompe primero es esto, y en
silencio: la respuesta sigue saliendo bien y el enlace de abajo deja de llevar a ninguna parte.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.answer import SUPPORTED_LANGS, tool_link
from pedibot.bot.guides import GuideIndex
from pedibot.bot.vaccines import Vaccines

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DIST = RAIZ / "web" / "site" / "dist"

pytestmark = pytest.mark.skipif(not DIST.is_dir(), reason="sin sitio construido (make web-build)")


def _existe(url: str) -> bool:
    camino = url.strip("/")
    if not camino:
        return (DIST / "index.html").exists()
    return (DIST / camino / "index.html").exists() or (DIST / f"{camino}.html").exists()


@pytest.mark.parametrize("lang", SUPPORTED_LANGS)
def test_the_dose_link_exists(lang: str) -> None:
    u = tool_link("dose", lang).url
    assert _existe(u), f"[{lang}] la respuesta enlaza a {u} y esa página no existe"


@pytest.mark.parametrize("lang", SUPPORTED_LANGS)
def test_every_vaccine_link_exists(lang: str) -> None:
    v = Vaccines(RAIZ / "config" / "vaccines.yaml")
    for pais in [*v.countries, None]:
        u = tool_link("vaccines", lang, pais).url
        assert _existe(u), f"[{lang}/{pais}] la respuesta enlaza a {u} y esa página no existe"


def test_every_guide_link_exists() -> None:
    gi = GuideIndex(RAIZ / "web" / "content")
    rotos = [
        (lg, g.url) for lg, guias in gi.by_lang.items() for g in guias if not _existe(g.url)
    ]
    assert not rotos, f"guías cuyo enlace no existe: {rotos[:10]}"


def test_there_were_links_to_check() -> None:
    """El candado del candado: si el índice de guías se queda vacío, lo de arriba pasa solo."""
    gi = GuideIndex(RAIZ / "web" / "content")
    assert len(gi) > 400, f"solo veo {len(gi)} guías"
