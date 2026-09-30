"""El mapamundi de la página de urgencias y el continente de cada país (30-sep-2026).

El operador, sobre /emergency: «infumable, todo ahí al mogollón. Mejor un mapamundi que te diga
el número de cada sitio pinchando el país, y un desplegable doble de continente y país». Esto
fabrica las dos piezas que eso necesita, a partir de Natural Earth (dominio público):

- `web/site/public/world.svg`: el mapa de 110 m en proyección Equal Earth, un <path> por país con
  su código ISO en `data-cc`. Sólo se descarga en pantallas anchas.
- `web/site/src/data/continents.json`: el continente de cada país con número de urgencias, del
  mapa de 50 m, que trae también los pequeños (Baréin, Comoras, Singapur) que el de 110 m no pinta.

    uv run python scripts/build_world_map.py        # baja los mapas si no están y lo genera

Los mapas en bruto se quedan en FUENTES/geo/ (fuera del repositorio).
"""

from __future__ import annotations

import json
import math
import pathlib
import sys
import urllib.request

import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
GEO = RAIZ / "FUENTES" / "geo"
URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_{r}_admin_0_countries.geojson"
SVG = RAIZ / "web" / "site" / "public" / "world.svg"
CONT = RAIZ / "web" / "site" / "src" / "data" / "continents.json"

# Natural Earth → las seis claves del desplegable. América va partida en dos porque juntas son
# 35 países en un solo desplegable; Centroamérica y el Caribe van con el norte, como en NE.
CONTINENTE = {
    "Africa": "africa",
    "Asia": "asia",
    "Europe": "europe",
    "North America": "north_america",
    "South America": "south_america",
    "Oceania": "oceania",
}
# Lo que Natural Earth no clasifica como uno de los seis (o no trae con código)
A_MANO = {"XK": "europe", "MV": "asia", "MU": "africa", "SC": "africa", "CV": "africa", "BH": "asia", "SG": "asia"}


def _baja(r: str) -> dict:
    f = GEO / f"ne_{r}.geojson"
    if not f.exists():
        GEO.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL.format(r=r), f)
    return json.loads(f.read_text(encoding="utf-8"))


def _cc(props: dict) -> str | None:
    for k in ("ISO_A2_EH", "ISO_A2", "WB_A2"):
        v = props.get(k)
        if v and v != "-99" and len(v) == 2:
            return v.upper()
    return None


def _equal_earth(lon: float, lat: float) -> tuple[float, float]:
    """La proyección Equal Earth (Šavrič, Patterson y Jenny, 2018): áreas verdaderas y una forma
    que no infla Europa ni encoge África, que es donde está la mitad de los países de la lista."""
    a1, a2, a3, a4 = 1.340264, -0.081106, 0.000893, 0.003796
    m = math.sqrt(3) / 2
    lam, phi = math.radians(lon), math.radians(lat)
    th = math.asin(m * math.sin(phi))
    t2 = th * th
    t6 = t2 * t2 * t2
    x = lam * math.cos(th) / (m * (a1 + 3 * a2 * t2 + t6 * (7 * a3 + 9 * a4 * t2)))
    y = th * (a1 + a2 * t2 + t6 * (a3 + a4 * t2))
    return x, y


def main() -> int:
    # Los países de las dos páginas que usan el buscador: urgencias y vacunas (30-sep-2026). El
    # mapa marca todos los que tienen algo; cada página enciende los suyos.
    numeros = yaml.safe_load((RAIZ / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8"))
    vacunas = yaml.safe_load((RAIZ / "config" / "vaccines.yaml").read_text(encoding="utf-8"))["countries"]
    paises = {k for k in numeros if k != "default"} | set(vacunas)

    # continentes, del mapa de 50 m
    cont: dict[str, str] = {}
    for f in _baja("50m")["features"]:
        cc = _cc(f["properties"])
        c = CONTINENTE.get(f["properties"].get("CONTINENT", ""))
        if cc and c and cc not in cont:
            cont[cc] = c
    cont.update(A_MANO)
    faltan = sorted(p for p in paises if p not in cont)
    if faltan:
        print(f"sin continente: {faltan} — añadirlos a A_MANO", file=sys.stderr)
        return 1
    CONT.write_text(
        json.dumps({cc: cont[cc] for cc in sorted(paises)}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )

    # el mapa, del de 110 m. Escala a 1000 de ancho; la Antártida fuera (nadie llama desde allí
    # y ocupa un tercio del alto).
    xmax, _ = _equal_earth(180, 0)
    _, ymax = _equal_earth(0, 90)
    esc = 500 / xmax

    def anillo_d(anillo: list) -> str:
        # enteros y sin repetir el punto anterior: a 1000 de ancho medio píxel no se ve, y el
        # mapa baja de 118 kB a la mitad
        pts: list[str] = []
        for lon, lat in anillo:
            x, y = _equal_earth(lon, lat)
            p = f"{round(x * esc + 500)},{round(ymax * esc - y * esc)}"
            if not pts or pts[-1] != p:
                pts.append(p)
        return "M" + "L".join(pts) + "Z" if len(pts) > 2 else ""

    trazos = []
    for f in _baja("110m")["features"]:
        props = f["properties"]
        if props.get("CONTINENT") == "Antarctica":
            continue
        cc = _cc(props)
        g = f["geometry"]
        polis = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        d = ""
        for poli in polis:
            for anillo in poli:
                d += anillo_d(anillo)
        attrs = f' data-cc="{cc}"' if cc in paises else ""
        trazos.append(f'<path class="c"{attrs} d="{d}"/>')
    y_sur = ymax * esc - _equal_earth(0, -58)[1] * esc
    SVG.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {round(y_sur)}" role="img">'
        + "".join(trazos)
        + "</svg>\n",
        encoding="utf-8",
    )
    print(f"continents.json: {len(paises)} países · world.svg: {SVG.stat().st_size // 1024} kB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
