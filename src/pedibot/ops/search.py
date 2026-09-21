"""Lo que Google enseña de nosotros, y con qué lo buscan (6-sep-2026).

El registro del servidor dice qué página pidieron. Esto dice qué **escribieron** para encontrarla,
cuántas veces salimos sin que nos pincharan y en qué puesto — que es la única forma de saber qué
escribir para que llegue alguien, en vez de adivinarlo.

La autenticación es una cuenta de servicio: un JWT firmado con su clave privada y canjeado por un
token. Sin dependencias nuevas — PyJWT y cryptography ya estaban.

**El panel no llama a Google.** Un timer diario escribe `data/gsc.json` y la página lee el fichero:
una llamada de red dentro de un `render()` convierte una página que tarda 200 ms en una que a
veces tarda diez segundos y a veces falla, y entonces se deja de abrir. El fichero lleva su propia
fecha, y el panel dice de cuándo es en vez de aparentar que es de ahora.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import time
from typing import Any

SITE = "https://pedibot.xyz/"
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
API = (
    "https://searchconsole.googleapis.com/webmasters/v3/sites/"
    + SITE.replace(":", "%3A").replace("/", "%2F")
    + "/searchAnalytics/query"
)

#: Google publica los datos con dos o tres días de retraso. Pedir hasta hoy devuelve días vacíos
#: que hunden la media y hacen creer que algo se ha roto.
LAG_DAYS = 3


def key_path() -> pathlib.Path:
    from pedibot.settings import ROOT

    return ROOT / "gsc_key.json"


def cache_path() -> pathlib.Path:
    from pedibot.settings import ROOT

    return ROOT / "data" / "gsc.json"


def token(key_file: pathlib.Path | None = None) -> str:
    import httpx
    import jwt

    k = json.loads((key_file or key_path()).read_text(encoding="utf-8"))
    now = int(time.time())
    assertion = jwt.encode(
        {
            "iss": k["client_email"],
            "scope": SCOPE,
            "aud": k["token_uri"],
            "iat": now,
            "exp": now + 3600,
        },
        k["private_key"],
        algorithm="RS256",
    )
    r = httpx.post(
        k["token_uri"],
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
        timeout=30,
    )
    r.raise_for_status()
    return str(r.json()["access_token"])


def query(tok: str, dims: list[str], start: str, end: str, rows: int = 1000) -> list[dict]:
    import httpx

    r = httpx.post(
        API,
        headers={"Authorization": f"Bearer {tok}"},
        json={"startDate": start, "endDate": end, "dimensions": dims, "rowLimit": rows},
        timeout=90,
    )
    r.raise_for_status()
    return list(r.json().get("rows", []))


def collect(days: int = 28, key_file: pathlib.Path | None = None) -> dict[str, Any]:
    """Everything the panel shows, in one pass, ready to be written to the cache."""
    end = dt.date.today() - dt.timedelta(days=LAG_DAYS)
    start = end - dt.timedelta(days=days)
    tok = token(key_file)
    s, e = start.isoformat(), end.isoformat()

    tot = query(tok, [], s, e, 1)
    t = tot[0] if tot else {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}

    def top(dim: str, n: int) -> list[dict[str, Any]]:
        rows = query(tok, [dim], s, e, 500)
        rows.sort(key=lambda r: -r["impressions"])
        return [
            {
                "key": r["keys"][0],
                "clicks": int(r["clicks"]),
                "impressions": int(r["impressions"]),
                "position": round(r["position"], 1),
            }
            for r in rows[:n]
        ]

    # what could actually be pushed: between 4th and 30th is a page that exists in the results
    # and is not on the first one. Below that, nothing moves it but authority.
    pairs = query(tok, ["query", "page"], s, e, 5000)
    close = [
        {
            "query": r["keys"][0],
            "page": r["keys"][1].replace("https://pedibot.xyz", ""),
            "impressions": int(r["impressions"]),
            "clicks": int(r["clicks"]),
            "position": round(r["position"], 1),
        }
        for r in pairs
        if 3.5 <= r["position"] <= 30
    ]
    close.sort(key=lambda r: -r["impressions"])

    return {
        "fetched": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "from": s,
        "to": e,
        "days": days,
        "clicks": int(t["clicks"]),
        "impressions": int(t["impressions"]),
        "ctr": round(float(t["ctr"]) * 100, 2),
        "position": round(float(t["position"]), 1),
        "queries": top("query", 20),
        "pages": top("page", 20),
        "countries": top("country", 10),
        "close": close[:20],
        # clics por día, para la línea de Google de la gráfica del panel (21-sep-2026)
        "per_day": {r["keys"][0]: int(r["clicks"]) for r in query(tok, ["date"], s, e, 500)},
    }


def load() -> dict[str, Any] | None:
    """What the timer left. None when there is nothing yet — the panel says so rather than
    showing zeros, because a zero here would read as "nobody searched for us"."""
    p = cache_path()
    if not p.exists():
        return None
    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else None
    except json.JSONDecodeError:
        return None


def save(data: dict[str, Any]) -> None:
    p = cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
