"""¿Siguen vivos los enlaces que la web enseña como fuente? (6-sep-2026)

La promesa entera de PediBot es «te enseño de dónde sale». Un enlace de fuente que da 404 no es un
detalle de mantenimiento: es esa promesa rota, y encima en la única página donde el lector iba a
comprobarnos.

Se descubrió por casualidad al auditar los calendarios: el del **Ministerio de Sanidad español
llevaba 404**, en la página de vacunas del idioma con más lectores. No lo vigilaba nadie.

Se comprueba semanalmente, con el informe. Y se avisa de dos cosas distintas:

  · **Roto** (4xx/5xx o no responde): hay que arreglarlo.
  · **Movido** (redirige a otra dirección): funciona hoy, pero el que guardamos ya no es el bueno,
    y una redirección puede desaparecer en cualquier momento. El del NHS estaba así.
"""

from __future__ import annotations

import pathlib
from typing import Any

UA = "Mozilla/5.0 (compatible; PediBot/1.0; +https://pedibot.xyz)"
TIMEOUT = 25.0


def vaccine_sources(config_dir: pathlib.Path) -> list[tuple[str, str]]:
    """(de quién es, dirección) para cada calendario publicado."""
    import yaml

    raw = yaml.safe_load((config_dir / "vaccines.yaml").read_text(encoding="utf-8"))
    return [
        (f"calendario {code}", str(c["source_url"]))
        for code, c in raw["countries"].items()
        if c.get("source_url")
    ]


def check(pairs: list[tuple[str, str]]) -> dict[str, list[Any]]:
    """Sin excepciones hacia arriba: esto corre dentro del informe semanal y una web caída no
    puede dejar al operador sin su resumen."""
    import httpx

    roto: list[tuple[str, str, str]] = []
    movido: list[tuple[str, str, str]] = []
    for que, url in pairs:
        try:
            r = httpx.get(url, follow_redirects=True, timeout=TIMEOUT, headers={"User-Agent": UA})
        except Exception as e:  # noqa: BLE001 — cualquier fallo de red es «no se pudo comprobar»
            roto.append((que, url, type(e).__name__))
            continue
        if r.status_code >= 400:
            roto.append((que, url, f"HTTP {r.status_code}"))
        elif str(r.url).rstrip("/") != url.rstrip("/"):
            movido.append((que, url, str(r.url)))
    return {"roto": roto, "movido": movido}


def report_lines(config_dir: pathlib.Path) -> list[str]:
    """Lo que se añade al informe semanal. Vacío cuando todo está bien: un aviso que aparece cada
    semana diciendo «todo correcto» deja de leerse, y este existe para ser leído."""
    res = check(vaccine_sources(config_dir))
    out: list[str] = []
    if res["roto"]:
        out.append("")
        out.append(f"🔗 FUENTES ROTAS ({len(res['roto'])}) — la web las enseña y no responden:")
        for que, url, por in res["roto"]:
            out.append(f"  · {que}: {por}")
            out.append(f"    {url}")
    if res["movido"]:
        out.append("")
        out.append(f"🔗 Fuentes movidas ({len(res['movido'])}) — funcionan por una redirección:")
        for que, _url, ahora in res["movido"]:
            out.append(f"  · {que} → {ahora}")
    return out
