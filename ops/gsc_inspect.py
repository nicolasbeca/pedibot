"""Pregunta a Google, URL por URL, qué ha hecho con cada página. A mano, no por temporizador.

Search Console avisa por correo de «páginas no indexadas» sin decir cuáles. La URL Inspection
API sí lo dice, pero tarda ~7 s por URL y deja 2.000 al día: por eso se inspeccionan las páginas
con impresiones de los últimos 90 días y una muestra al azar del sitemap, no todo.

Escrito el 8-oct-2026, cuando dio que Google dejaba fuera /dose/tylenol y metía
/de/dose/apirofeno (tests/test_brand_pages_index_where_sold.py). Repetirlo a las pocas semanas
dice si aquello sirvió.

    python3 ops/gsc_inspect.py           # con impresiones + 60 al azar
    python3 ops/gsc_inspect.py 200       # con impresiones + 200 al azar

Escribe `data/gsc_inspect.json` y saca por pantalla el recuento por estado y tipo de página.
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import random
import re
import sys

import httpx

from pedibot.ops.search import LAG_DAYS, SITE, cache_path, key_path, query, token

INSPECT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
LOCALES = {"es", "fr", "de", "ru", "ar", "pt", "hi"}


def tipo(url: str) -> str:
    partes = [p for p in url.replace(SITE, "/").split("/") if p and p not in LOCALES]
    return partes[0] if partes else "/"


def main() -> int:
    if not key_path().exists():
        print(f"no hay clave en {key_path()}", file=sys.stderr)
        return 0
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    tok = token()
    hoy = dt.date.today()
    fin = (hoy - dt.timedelta(days=LAG_DAYS)).isoformat()
    ini = (hoy - dt.timedelta(days=90)).isoformat()
    con_impresiones = [r["keys"][0] for r in query(tok, ["page"], ini, fin, rows=1000)]
    sitemap = re.findall(r"<loc>([^<]+)", httpx.get(f"{SITE}sitemap-0.xml", timeout=30).text)
    random.seed(hoy.toordinal())
    urls = list(dict.fromkeys(con_impresiones + random.sample(sitemap, min(n, len(sitemap)))))
    print(f"{len(con_impresiones)} con impresiones, {len(urls)} a inspeccionar", flush=True)

    out = []
    for i, u in enumerate(urls, 1):
        r = httpx.post(
            INSPECT,
            headers={"Authorization": f"Bearer {tok}"},
            json={"inspectionUrl": u, "siteUrl": SITE},
            timeout=30,
        )
        if r.status_code != 200:
            # la cuota es de 2.000 al día: si se acaba, se guarda lo que haya
            print(f"parado en {i}: {r.status_code} {r.text[:200]}", file=sys.stderr)
            break
        s = r.json()["inspectionResult"]["indexStatusResult"]
        out.append(
            {
                "url": u,
                "estado": s.get("coverageState"),
                "canonica_nuestra": s.get("userCanonical"),
                "canonica_google": s.get("googleCanonical"),
                "rastreada": s.get("lastCrawlTime"),
            }
        )
        if i % 25 == 0:
            print(f"{i}/{len(urls)}", flush=True)

    destino = cache_path().with_name("gsc_inspect.json")
    destino.write_text(json.dumps({"fecha": hoy.isoformat(), "urls": out}, indent=1), "utf-8")
    cuenta = collections.Counter((o["estado"], tipo(o["url"])) for o in out)
    for (estado, t), k in sorted(cuenta.items(), key=lambda x: -x[1]):
        print(f"{k:5}  {estado}  ·  {t}")
    for o in out:
        if o["canonica_google"] and o["canonica_nuestra"] and o["canonica_google"] != o["canonica_nuestra"]:
            print("otra canónica:", o["url"], "→", o["canonica_google"])
    print(f"→ {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
