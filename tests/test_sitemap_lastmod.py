"""El sitemap decía que 296 páginas cambiaban cada día, y ninguna había cambiado (10-sep-2026).

`astro.config.mjs` daba a toda página que no fuera una guía la fecha **de la construcción**, y el
sitio se reconstruye a diario para publicar las guías. Así que cada mañana el sitemap anunciaba
las 168 páginas de dosis, las 64 de vacunas y las 64 sueltas como modificadas — 296 de 779 —
sin que ninguna hubiera cambiado.

Lo pagábamos dos veces. `lastmod` sólo sirve si es creíble: Google lo ignora en cuanto descubre
que un sitio lo mueve por costumbre. Y `ops/indexnow.py` decide qué mandar a Bing, Yandex, Seznam
y Naver comparando ese mismo campo, así que llevaba semanas enviando exactamente las mismas 296
URLs cada día — que es justo lo que la documentación de IndexNow pide no hacer.

La comprobación es la propiedad, no el mecanismo: **reconstruir sin tocar nada no puede cambiar
ni una fecha**. Se construye a un directorio aparte y se compara con el sitemap ya construido.
"""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "web" / "site"
DIST = SITE / "dist"


def _lastmods(xml: str) -> dict[str, str]:
    return {
        loc: mod
        for loc, mod in re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", xml)
    }


def test_rebuilding_without_changes_does_not_move_a_single_date():
    antes = DIST / "sitemap-0.xml"
    if not antes.exists():
        pytest.skip("el sitio no está construido en esta copia")
    if shutil.which("npx") is None:
        pytest.skip("sin Node en esta máquina")

    # dentro del propio sitio a propósito: con --outDir a la carpeta temporal del sistema, npx
    # se cae en Windows con una aserción de libuv antes de construir nada
    salida = SITE / ".sitemap-check"
    shutil.rmtree(salida, ignore_errors=True)
    try:
        r = subprocess.run(
            "npx astro build --outDir .sitemap-check",
            cwd=SITE, capture_output=True, text=True, timeout=900, shell=True,
        )
        if r.returncode != 0:
            pytest.skip(f"la construcción de comprobación no arrancó: {r.stderr[-200:]}")

        sitemap = salida / "sitemap-0.xml"
        assert sitemap.exists(), "la construcción no dejó sitemap"

        a = _lastmods(antes.read_text(encoding="utf-8"))
        b = _lastmods(sitemap.read_text(encoding="utf-8"))
        movidas = sorted(u for u in a.keys() & b.keys() if a[u] != b[u])
        assert not movidas, (
            f"{len(movidas)} URLs cambian de fecha al reconstruir sin tocar nada, y el sitemap "
            f"deja de ser creíble: {movidas[:4]}"
        )
    finally:
        shutil.rmtree(salida, ignore_errors=True)


def test_every_date_comes_from_a_file_and_not_from_the_clock():
    """La primera versión de este candado decía «ninguna fecha puede cubrir un tercio del
    sitemap», y se cayó en cuanto hubo un cambio legítimo en todas las páginas: tocar `i18n.ts`
    —donde vive el texto visible— cambia de verdad las 792. La heurística prohibía justo eso.

    Lo que hay que exigir es lo que se quería decir: **cada fecha sale de un fichero**. O es la
    del frontmatter de una guía (medianoche) o es la hora de modificación de algún fuente que
    alimenta la página. Si alguna vez vuelve a salir del reloj de la construcción, no casará con
    ninguna de las dos y esto lo dirá.
    """
    p = DIST / "sitemap-0.xml"
    if not p.exists():
        pytest.skip("el sitio no está construido en esta copia")
    fechas = set(_lastmods(p.read_text(encoding="utf-8")).values())
    if not fechas:
        pytest.skip("sitemap sin fechas")

    import datetime as dt

    mtimes = set()
    for base in (ROOT / "web" / "site" / "src", ROOT / "config"):
        for f in base.rglob("*"):
            if f.is_file():
                # al segundo, no al milisegundo: JavaScript y Python redondean distinto el
                # mismo mtime y se llevaban 1 ms de diferencia. Una fecha sacada del reloj de la
                # construcción no coincide con ningún fichero ni al segundo, que es lo que importa
                mtimes.add(
                    dt.datetime.fromtimestamp(f.stat().st_mtime, dt.UTC)
                    .isoformat(timespec="seconds")
                )

    huerfanas = sorted(
        f
        for f in fechas
        if not f.endswith("T00:00:00.000Z")
        and f[:19] + "+00:00" not in mtimes
    )
    assert not huerfanas, (
        "estas fechas del sitemap no son ni la de una guía ni la de ningún fichero fuente, "
        f"así que salen del reloj: {huerfanas}"
    )
