"""¿Siguen vivas las fuentes que la web enseña? (6-sep-2026)

La promesa entera de PediBot es «te enseño de dónde sale». Un enlace de fuente que no lleva a
ninguna parte no es un detalle de mantenimiento: es esa promesa rota, y justo en el sitio donde el
lector iba a comprobarnos.

Se descubrió por casualidad auditando los calendarios — el del **Ministerio de Sanidad español
llevaba 404** — y al mirar las 243 direcciones del corpus salió lo demás. Ninguna estaba rota,
pero 17 respondían por una redirección, y **la redirección de hoy es el 404 de mañana**.

Tres formas de estar mal, y solo la primera es obvia:

  · **Rota** — 4xx, 5xx o no responde.
  · **Retirada de servicio** — responde 200 y te lleva a una página que dice que ya no existe. El
    NHS retiró la de espasmos del sollozo y redirige a `/page-removed/`: un 200 impecable que no
    contiene nada de lo que citamos. La primera versión de esta comprobación lo dio por bueno.
  · **Cambió de tema** — redirige a otra cosa. `medlineplus.gov/bedwetting` acaba en la página
    general de desarrollo infantil, y la del NHS sobre cefaleas *en niños* acaba en la de cefaleas
    a secas. Se detecta porque el nombre del destino ya no se parece al del origen.

Se comprueba con el informe semanal, y **calla cuando todo está bien**: un aviso que aparece cada
domingo diciendo «correcto» deja de leerse, y este existe para leerse.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from typing import Any

UA = "Mozilla/5.0 (compatible; PediBot/1.0; +https://pedibot.xyz)"
TIMEOUT = 30.0
WORKERS = 8

#: Direcciones a las que un sitio te manda cuando la página ya no existe pero no quiere decir 404.
RETIRADA = re.compile(r"page-?removed|page-?not-?found|/404|content-?unavailable|/gone", re.I)

#: Palabras que no distinguen un tema de otro y no cuentan al comparar dos direcciones.
VACIAS = {
    "www",
    "com",
    "org",
    "es",
    "en",
    "uk",
    "gov",
    "htm",
    "html",
    "conditions",
    "symptoms",
    "health",
    "topics",
    "about",
    "baby",
    "children",
    "child",
    "index",
    "page",
    "de",
    "the",
}


def _palabras(url: str) -> set[str]:
    """Las palabras propias del CAMINO de una dirección, sin el sitio.

    El sitio se quita a propósito. Con él dentro, «medlineplus» aparecía en las dos direcciones de
    cualquier redirección interna y la comparación nunca podía decir «cambió de tema»: el salto de
    `medlineplus.gov/bedwetting.html` a `medlineplus.gov/childdevelopment.html` pasaba por una
    mudanza inocente (7-sep-2026). Y esa es la avería peligrosa —el enlace responde, así que nada
    parece roto, pero la página ya no sostiene lo que se cita.
    """
    camino = re.sub(r"^https?://[^/]+", "", url)
    # las de dos letras o menos no distinguen nada, y compartir un «in» no puede tapar un
    # cambio de tema
    return {p for p in re.split(r"[^a-z0-9]+", camino.lower()) if len(p) > 2} - VACIAS


def catalogued(root: pathlib.Path) -> list[tuple[str, str]]:
    """(de quién es, dirección): los calendarios de vacunas y cada documento del corpus."""
    import yaml

    fuera: dict[str, str] = {}
    vac = yaml.safe_load((root / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    for code, c in vac["countries"].items():
        if c.get("source_url"):
            fuera[f"calendario {code}"] = str(c["source_url"])

    idx = root / "index" / "pedibot.db"
    if idx.exists():
        con = sqlite3.connect(idx)
        for (raw,) in con.execute("SELECT data FROM chunks"):
            d = json.loads(raw)
            u = d.get("source_url")
            if u and str(u).startswith("http"):
                fuera.setdefault(str(d["doc_id"]), str(u))
        con.close()
    return sorted(fuera.items())


def _probe(par: tuple[str, str]) -> tuple[str, str, str, str]:
    """(qué, dirección, veredicto, detalle). Nunca lanza: esto corre dentro del informe semanal y
    una web caída no puede dejar al operador sin su resumen."""
    import httpx

    que, url = par
    try:
        r = httpx.get(url, follow_redirects=True, timeout=TIMEOUT, headers={"User-Agent": UA})
    except Exception as e:  # noqa: BLE001
        return que, url, "rota", type(e).__name__
    final = str(r.url)
    if r.status_code >= 400:
        return que, url, "rota", f"HTTP {r.status_code}"
    if RETIRADA.search(final):
        return que, url, "retirada", final
    if final.rstrip("/") != url.rstrip("/"):
        antes, ahora = _palabras(url), _palabras(final)
        # si el destino ya no comparte ninguna palabra propia, no es una mudanza: es otro tema
        clase = "tema" if antes and not (antes & ahora) else "movida"
        return que, url, clase, final
    return que, url, "ok", ""


def check(pairs: list[tuple[str, str]]) -> dict[str, list[tuple[str, str, str, str]]]:
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(_probe, pairs))
    fuera: dict[str, list[tuple[str, str, str, str]]] = {}
    for r in res:
        fuera.setdefault(r[2], []).append(r)
    return fuera


def report_lines(root: pathlib.Path) -> list[str]:
    """Lo que se añade al informe semanal. Vacío cuando no hay nada que contar."""
    res = check(catalogued(root))
    out: list[str] = []

    # Lo primero, porque es lo unico de aqui que ya sabemos que ha pasado de verdad: el calendario
    # de Portugal estuvo cinco anos derogado dando HTTP 200 (7-sep-2026). Detectarlo y no contarlo
    # no habria arreglado nada.
    ilegibles: list[tuple[str, str, str]] = []
    try:
        viejas = superseded(root, unreadable=ilegibles)
    except Exception:  # noqa: BLE001 - el informe semanal no se cae por esto
        viejas = []
    if viejas:
        out.append("")
        out.append(
            f"\U0001f4c5 FUENTES QUE PUEDEN ESTAR CADUCADAS ({len(viejas)}) - responden bien, "
            "pero su pagina habla de una edicion posterior a la que citamos:"
        )
        for que, nuestra, suya, url in viejas:
            out.append(f"  \u00b7 {que}: citamos {nuestra} y la fuente menciona {suya}")
            out.append(f"    {url[:100]}")
        out.append("  (es un indicio, no una prueba: hay que abrir el documento y mirarlo)")
    if ilegibles:
        out.append("")
        out.append(
            f"\U0001f441 FUENTES QUE NO SE PUDIERON LEER ({len(ilegibles)}) - contestan, pero no "
            "devuelven pagina suficiente para comprobar nada:"
        )
        for que, motivo, url in ilegibles:
            out.append(f"  \u00b7 {que}: {motivo}")
            out.append(f"    {url[:100]}")
        out.append(
            "  (no es 'no hay nada nuevo': es 'no se ha podido mirar'. Abrelo en el navegador)"
        )
    TITULOS = [
        ("rota", "🔗 FUENTES ROTAS", "la web las enseña y no responden"),
        ("retirada", "🔗 FUENTES RETIRADAS", "responden, pero el sitio dice que ya no existen"),
        ("tema", "🔗 Fuentes que cambiaron de tema", "redirigen a otra cosa distinta"),
    ]
    for clave, titulo, porque in TITULOS:
        items = res.get(clave, [])
        if not items:
            continue
        out.append("")
        out.append(f"{titulo} ({len(items)}) — {porque}:")
        for que, url, _clase, detalle in items[:10]:
            out.append(f"  · {que}: {detalle[:80]}")
            out.append(f"    {url[:100]}")
        if len(items) > 10:
            out.append(f"  … y {len(items) - 10} más")
    movidas = res.get("movida", [])
    if len(movidas) >= 5:
        # una o dos son ruido; cinco es que un organismo ha reorganizado su web
        out.append("")
        out.append(
            f"🔗 {len(movidas)} fuentes funcionan por una redirección — conviene actualizarlas"
        )
    return out


def summary(root: pathlib.Path) -> dict[str, Any]:
    res = check(catalogued(root))
    return {k: len(v) for k, v in sorted(res.items())}


# --------------------------------------------------------------------------------------------
# Una fuente puede caducar sin morir (7-sep-2026)
#
# Todo lo de arriba busca fuentes ROTAS. El calendario de vacunas de Portugal daba HTTP 200, no
# redirigía a ninguna parte y pasaba todas las comprobaciones — y llevaba desde octubre de 2025
# derogado: la DGS lo había sustituido por el PNV 2025, con MenACWY en lugar de MenC a los 12
# meses. Estuvimos publicando un calendario que ya no era el vigente, y nada podía notarlo,
# porque **una dirección viva no dice nada sobre si su contenido sigue siendo el mismo**.
#
# Esto no lo demuestra: lo sugiere. Si la página de una fuente cuya edición es de 2020 habla de
# 2025, puede ser una edición nueva o puede ser una nota al pie. Por eso el informe dice «conviene
# mirar» y no «está caducado»: la decisión es de una persona, con el documento delante.
# --------------------------------------------------------------------------------------------

#: Las palabras con las que se anuncia una edición. Un año solo cuenta si aparece cerca de una de
#: ellas: «PNV 2025», «Calendario recomendado año 2026», «2026 schedule», «last reviewed 2023».
#: Sin esto el detector engancha cohortes y campañas —«MenB hasta marzo de 2027», «nacidos a
#: partir de enero de 2025»—, que no son ediciones nuevas y harían saltar el aviso cada semana.
#: Medido sobre la página del NHS: de cuatro años señalados a uno, y ese uno es su `dateModified`.
EDICION = re.compile(
    r"calendari|schedule|edici[oó]n|edition|vers[iã]o|version|PNV|recomendado|recommended"
    r"|last reviewed|updated|actualizado|revisado|programa|programme|plan",
    re.I,
)
#: Cuánto texto se mira a cada lado del año para buscar esas palabras.
VENTANA = 90

#: Por debajo de esto una página no puede contener un calendario: viene vacía, cortada o es un
#: muro anti-robots. La del CDC devuelve 427 bytes de HTML truncado con un 200 limpio, y sin esta
#: comprobación se leería como «no hay nada más nuevo», que es justo lo contrario de la verdad.
MINIMO_LEGIBLE = 2000

#: Un año más allá del actual todavía es creíble (los calendarios se aprueban en diciembre para el
#: año siguiente: el español de 2026 se aprobó el 12 de diciembre de 2025). Más lejos ya no es una
#: edición, es un objetivo o una fecha de caducidad.
MARGEN_FUTURO = 1


def _años(texto: str) -> set[int]:
    """Todos los años que aparecen. Se usa para leer NUESTRA cita, que es corta y toda ella habla
    de la edición."""
    return {int(a) for a in re.findall(r"\b(20\d\d)\b", texto)}


def _texto_visible(html: str) -> str:
    """Lo que leería una persona: sin etiquetas, sin scripts, sin metadatos.

    El aviso saltaba por la fecha de compilación de una página (7-sep-2026, el CDC), que no es la
    fuente diciendo nada sobre su edición. Lo que cuenta es lo que se ve.
    """
    sin_script = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", sin_script))


def _años_de_edicion(texto: str) -> set[int]:
    """Solo los años que están pegados a una palabra de edición. Se usa para leer la PÁGINA, que
    es larga y está llena de años que no son ediciones."""
    fuera = set()
    for m in re.finditer(r"\b(20\d\d)\b", texto):
        if EDICION.search(texto[max(0, m.start() - VENTANA) : m.end() + VENTANA]):
            fuera.add(int(m.group(1)))
    return fuera


def _edicion_citada(fuente: str) -> int | None:
    a = _años(fuente)
    return max(a) if a else None


def superseded(
    root: pathlib.Path,
    ahora: int | None = None,
    traer: Any = None,
    unreadable: list[tuple[str, str, str]] | None = None,
) -> list[tuple[str, int, int, str]]:
    """(qué, año que citamos, año que aparece en la fuente, dirección), solo cuando el segundo es
    mayor. Nunca lanza: esto corre dentro del informe semanal."""
    import yaml

    año_actual = ahora or dt.date.today().year
    if traer is None:

        def traer(url: str) -> str:
            import httpx

            r = httpx.get(url, follow_redirects=True, timeout=TIMEOUT, headers={"User-Agent": UA})
            return r.text if r.status_code < 400 else ""

    vac = yaml.safe_load((root / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    fuera: list[tuple[str, int, int, str]] = []
    ilegibles = [] if unreadable is None else unreadable
    for code, c in sorted(vac["countries"].items()):
        url, nuestra = str(c.get("source_url") or ""), _edicion_citada(str(c.get("source", "")))
        if not url or nuestra is None:
            continue
        try:
            texto = traer(url)
        except Exception:  # noqa: BLE001
            ilegibles.append((f"calendario {code}", "no responde", url))
            continue
        if len(texto) < MINIMO_LEGIBLE:
            # No es «no hay nada nuevo»: es «no se ha podido mirar». Callarlo convertiría una
            # fuente ilegible en una fuente sana, que es el peor error para algo que avisa.
            ilegibles.append((f"calendario {code}", f"{len(texto)} bytes", url))
            continue
        visible = _texto_visible(texto)
        candidatos = {
            a for a in _años_de_edicion(visible) if nuestra < a <= año_actual + MARGEN_FUTURO
        }
        if candidatos:
            fuera.append((f"calendario {code}", nuestra, max(candidatos), url))
    return fuera
