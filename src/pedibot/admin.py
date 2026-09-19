"""Operator panel at /admin (protected by Caddy basic auth in production; never linked publicly).

Rewritten to be read at a glance (4-sep-2026). It used to be a wall of numbers — twelve tiles, a
PDBT price table, and two lists of `label ▁▁▁ 7` — and the operator had stopped opening it, which
makes it worth nothing however correct it is. Now it opens with one chart of the last N days,
puts the pages and the languages side by side as bars, and gives most of the room to the thing
that actually needs reading: what people asked and what PediBot answered.

The token block is gone. It has its own alert on Telegram the moment anything trades, and it was
the only part of this page nobody needed to check.

Server-rendered HTML with inline SVG and no library, matching the site: a dashboard that needs a
CDN is a dashboard that breaks the day the CDN does.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import pathlib
import sqlite3
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from pedibot.ops import report, search


def flagged_path() -> pathlib.Path:
    """Read from settings each time: the panel test points it at a temporary directory, and with a
    module constant every run of the suite wrote into the working copy of this file."""
    from pedibot.settings import get_settings

    return get_settings().flagged_path


def load_flagged() -> dict[int, dict[str, object]]:
    """The marked answers, by id. One entry each — it used to append a line per press, and the
    file ended up holding 189 copies of the same test answer."""
    path = flagged_path()
    if not path.exists():
        return {}
    out: dict[int, dict[str, object]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec.get("id"), int):
            out[rec["id"]] = rec  # a later line replaces an earlier one
    return out


def save_flagged(items: dict[int, dict[str, object]]) -> None:
    path = flagged_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(items[k], ensure_ascii=False) + "\n" for k in sorted(items))
    path.write_text(body, encoding="utf-8", newline="\n")


_CSS = """
:root{--ink:#2B3A35;--ink2:#5B6D66;--ink3:#8A9992;--line:#EAE4DA;--paper:#fff;--ground:#FFFDF9;
--sage:#2F6B57;--sage2:#C8E9E0;--coral:#C0392B;--amber:#B7791F;--mint:#EAF7F2}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:"Atkinson Hyperlegible",system-ui,sans-serif;font-size:15px}
main{max-width:1180px;margin:0 auto;padding:22px 18px 60px}
h1{font-family:Nunito,sans-serif;margin:0;font-size:1.5rem}
h2{font-family:Nunito,sans-serif;margin:0 0 12px;font-size:1.05rem;color:var(--ink2)}
.top{display:flex;align-items:baseline;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:18px}
.range a{display:inline-block;padding:4px 12px;border:1px solid var(--line);border-radius:999px;
text-decoration:none;color:var(--ink2);margin-left:6px;background:var(--paper)}
.range a.on{background:var(--sage);color:#fff;border-color:var(--sage)}
.period{margin:0 0 12px;color:var(--ink3);font-size:.86rem}
.period b{color:var(--ink2)}
.period .warn,.period .warn b{color:var(--coral)}
table.t{width:100%;border-collapse:collapse;margin-top:10px;font-size:.88rem}
table.t th{text-align:left;color:var(--ink3);font-weight:600;padding:4px 8px 4px 0;
border-bottom:1px solid var(--line)}
table.t td{padding:4px 8px 4px 0;border-bottom:1px solid var(--line);vertical-align:top}
table.t .mono{font-family:ui-monospace,monospace;color:var(--ink2);white-space:nowrap}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px}
.k{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.k b{display:block;font-family:"JetBrains Mono",monospace;font-size:1.7rem;line-height:1.1;color:var(--sage)}
.k span{color:var(--ink3);font-size:.82rem}
.k.warn b{color:var(--coral)}
.card{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin-bottom:16px}
.two{display:grid;grid-template-columns:1.15fr 1fr;gap:16px}
@media(max-width:880px){.two{grid-template-columns:1fr}}
.bars{display:grid;gap:7px}
.brow{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;font-size:.9rem}
.btrack{position:relative;background:var(--mint);border-radius:6px;height:22px;overflow:hidden}
.bfill{position:absolute;inset:0 auto 0 0;background:var(--sage2);border-radius:6px}
.blabel{position:relative;padding:2px 8px;line-height:18px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bnum{font-family:"JetBrains Mono",monospace;color:var(--ink2);font-size:.85rem}
.legend{display:flex;gap:16px;font-size:.82rem;color:var(--ink3);margin-bottom:6px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.qa{border-top:1px solid var(--line);padding:14px 0}
.qa:first-of-type{border-top:0}
.meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:.78rem;color:var(--ink3);margin-bottom:6px}
.tag{border:1px solid var(--line);border-radius:999px;padding:1px 9px;background:var(--ground)}
.tag.lvl-emergency,.tag.lvl-urgent{border-color:var(--coral);color:var(--coral);font-weight:700}
.tag.lvl-mental_health{border-color:var(--amber);color:var(--amber);font-weight:700}
.tag.bad{border-color:var(--coral);color:var(--coral)}
.q{font-size:1.02rem;margin:0 0 6px}
details summary{cursor:pointer;color:var(--sage);font-size:.88rem}
/* the sources are a second fold on purpose: which documents it used is a fair question,
   and on a five-sentence answer they are longer than the answer itself */
details.howto{margin:-4px 0 14px}details.howto p{margin:6px 0 0;color:var(--ink3);font-size:.86rem;line-height:1.5}
details.src{margin-top:8px}
details.src summary{color:var(--ink3);font-size:.8rem}
details.src pre{font-size:.78rem;color:var(--ink3)}
pre{white-space:pre-wrap;background:var(--ground);border:1px solid var(--line);padding:12px;
border-radius:10px;font-size:.86rem;margin:8px 0 0;font-family:inherit;line-height:1.5}
button{border:1px solid var(--line);background:var(--paper);border-radius:999px;padding:2px 11px;
cursor:pointer;font-size:.78rem;color:var(--ink2)}
button:hover{border-color:var(--coral);color:var(--coral)}
.mono{font-family:"JetBrains Mono",monospace}
a{color:var(--sage)}
.empty{color:var(--ink3);font-style:italic}
"""


def _day(iso: str | None) -> str:
    """2026-09-05 → 5 sep. The panel is read by one person who knows what year it is."""
    if not iso:
        return "—"
    months = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
    try:
        d = dt.date.fromisoformat(iso[:10])
    except ValueError:
        return iso
    return f"{d.day} {months[d.month - 1]}"


def _kpi(label: str, value: object, warn: bool = False) -> str:
    return (
        f'<div class="k{" warn" if warn else ""}"><b>{html.escape(str(value))}</b>'
        f"<span>{html.escape(label)}</span></div>"
    )


def _chart(visits: dict[str, int], questions: dict[str, int], days: int) -> str:
    """One picture of the period: visits as an area, questions as bars on the same days.

    Drawn as inline SVG because the two series only make sense together — a day with visitors and
    no questions means something different from a quiet day, and two separate lists never showed
    that.
    """
    end = dt.date.today()
    if days > 0:
        span = [(end - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    else:
        # "everything": from the first day either series saw, so the curve starts where the site
        # did instead of at an arbitrary window edge
        seen = sorted(set(visits) | set(questions))
        if not seen:
            return '<p class="empty">Todavía no hay nada que dibujar.</p>'
        start = dt.date.fromisoformat(seen[0])
        span = [(start + dt.timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    v = [visits.get(d, 0) for d in span]
    q = [questions.get(d, 0) for d in span]
    if not any(v) and not any(q):
        return '<p class="empty">Todavía no hay nada que dibujar en este periodo.</p>'

    W, H, PAD = 1100, 190, 26
    top = max(max(v), 1)
    inner_w, inner_h = W - PAD * 2, H - PAD * 2
    step = inner_w / max(len(span) - 1, 1)

    def y(value: int) -> float:
        return PAD + inner_h - (value / top) * inner_h

    pts = " ".join(f"{PAD + i * step:.1f},{y(n):.1f}" for i, n in enumerate(v))
    area = f"{PAD},{PAD + inner_h} {pts} {PAD + inner_w},{PAD + inner_h}"

    qtop = max(max(q), 1)
    bar_w = max(2.0, step * 0.34)
    bars = "".join(
        f'<rect x="{PAD + i * step - bar_w / 2:.1f}" y="{PAD + inner_h - (n / qtop) * inner_h * 0.55:.1f}"'
        f' width="{bar_w:.1f}" height="{(n / qtop) * inner_h * 0.55:.1f}" rx="2" fill="#2F6B57" opacity=".75"/>'
        for i, n in enumerate(q)
        if n
    )
    # a label every few days, so the axis stays legible at 7, 30 and 90
    every = max(1, len(span) // 9)
    ticks = "".join(
        f'<text x="{PAD + i * step:.1f}" y="{H - 6}" text-anchor="middle" font-size="10" fill="#8A9992">'
        f"{span[i][8:10]}/{span[i][5:7]}</text>"
        for i in range(0, len(span), every)
    )
    return (
        '<div class="legend"><span><i style="background:#C8E9E0"></i>visitas</span>'
        '<span><i style="background:#2F6B57"></i>consultas</span></div>'
        f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" role="img" aria-label="visitas y consultas por día">'
        f'<polyline points="{area}" fill="#EAF7F2" stroke="none"/>'
        f'<polyline points="{pts}" fill="none" stroke="#C8E9E0" stroke-width="2.5"/>'
        f"{bars}{ticks}"
        f'<text x="{PAD}" y="{PAD - 8}" font-size="11" fill="#8A9992">máx {top} visitas/día</text>'
        "</svg>"
    )


def _bars(items: list[tuple[str, int]], limit: int = 10) -> str:
    items = items[:limit]
    if not items:
        return '<p class="empty">Nada todavía.</p>'
    top = max(n for _, n in items) or 1
    rows = "".join(
        f'<div class="brow"><div class="btrack">'
        f'<div class="bfill" style="width:{100 * n / top:.0f}%"></div>'
        f'<div class="blabel">{html.escape(str(label))}</div></div>'
        f'<span class="bnum">{n}</span></div>'
        for label, n in items
    )
    return f'<div class="bars">{rows}</div>'


#: Each language named in itself, as the site names it. Hand-written and therefore checked
#: against SUPPORTED_LANGS by a test: Hindi shipped as a bare "hi" here because this list was
#: seven long and nothing said so.
_LANG_NAME = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "ru": "Русский",
    "ar": "العربية",
    "pt": "Português",
    "hi": "हिन्दी",
}

#: The triage levels are internal words and they decide whether a red banner sits above a
#: parent's answer. On a panel written in Spanish they should be readable.
_LEVEL_NAME = {
    "routine": "rutina",
    "mental_health": "salud mental",
    "urgent": "urgente (hoy)",
    "emergency": "emergencia (ahora)",
}


def _dwell_label(w: dict[str, Any]) -> str:
    """The middle visit, of those whose length can be known — or a dash, which is the honest
    answer when it cannot. Never a zero: zero is a measurement and this is the absence of one."""
    secs = w.get("median_seconds")
    if not w.get("timed") or secs is None:
        return "—"
    secs = int(secs)
    return f"{secs} s" if secs < 90 else f"{secs // 60} min"


def _dwell_sentence(w: dict[str, Any]) -> str:
    timed, visits = int(w.get("timed", 0)), int(w.get("visits", 0))
    if not visits:
        return ""
    return (
        f"<br>El tiempo solo se puede medir cuando alguien pide una segunda página — sin ella "
        f"nada marca el final de la visita. Aquí sale de <b>{timed}</b> visitas de {visits}; "
        f"de esas, {w.get('over_a_minute', 0)} pasaron del minuto. "
        f"No hay ningún rastreador en la web y no va a haberlo, así que esto es todo lo que se "
        f"puede saber."
    )


def _google_card(g: dict[str, Any] | None) -> str:
    """Lo que Google enseña de nosotros. Del fichero que deja el timer, nunca de la red: una
    llamada a Google dentro de un render convierte una página de 200 ms en una que a veces tarda
    diez segundos, y una página que a veces tarda diez segundos deja de abrirse."""
    if not g:
        return (
            '<div class="card"><h2>Google</h2><p class="empty">Todavía no hay datos. '
            "Los deja <code>ops/gsc_refresh.py</code> cada mañana; si lleva días vacío, la clave "
            "de <code>gsc_key.json</code> ha dejado de valer.</p></div>"
        )
    out = [
        '<div class="card"><h2>Google '
        f'<span class="bnum">({html.escape(str(g["from"]))} → {html.escape(str(g["to"]))})</span>'
        "</h2>",
        '<p class="period">Google publica con dos o tres días de retraso, así que esto nunca '
        "llega hasta hoy. <b>Impresiones</b> son las veces que nos ha mostrado; los clics, las "
        "que además nos pincharon.</p>",
        '<div class="kpis">'
        + _kpi("impresiones", g["impressions"])
        + _kpi("clics", g["clicks"])
        + _kpi("CTR", f"{g['ctr']}%")
        + _kpi("posición media", g["position"], warn=float(g["position"]) > 20)
        + "</div>",
    ]

    if g.get("close"):
        out.append(
            '<h2 style="margin-top:20px">Lo que se puede empujar</h2>'
            '<p class="period">Consultas donde ya salimos entre el puesto 4 y el 30. Por debajo '
            'del 30 no mueve una página lo que se le haga a la página.</p><table class="t">'
            "<tr><th>puesto</th><th>impr.</th><th>búsqueda</th><th>página</th></tr>"
        )
        for r in g["close"][:12]:
            out.append(
                f'<tr><td class="mono">{r["position"]}</td>'
                f'<td class="mono">{r["impressions"]}</td>'
                f"<td>{html.escape(str(r['query'])[:52])}</td>"
                f'<td class="mono">{html.escape(str(r["page"])[:44])}</td></tr>'
            )
        out.append("</table>")

    if g.get("queries"):
        out.append('<h2 style="margin-top:20px">Con qué nos buscan</h2><table class="t">')
        out.append("<tr><th>impr.</th><th>clics</th><th>puesto</th><th>búsqueda</th></tr>")
        for r in g["queries"][:15]:
            out.append(
                f'<tr><td class="mono">{r["impressions"]}</td>'
                f'<td class="mono">{r["clicks"]}</td>'
                f'<td class="mono">{r["position"]}</td>'
                f"<td>{html.escape(str(r['key'])[:60])}</td></tr>"
            )
        out.append("</table>")
    out.append("</div>")
    return "".join(out)


def _tests_line(q: dict[str, Any], days: int, include_test: bool) -> str:
    """Says out loud which questions are on screen, and links to the other set.

    Never hidden silently: if one morning the panel says nothing was asked, the operator has to
    be able to tell "nobody came" from "the header stopped being sent", and the only way is to
    look at what was left out."""
    n, other = int(q.get("test", 0)), ("" if include_test else "&tests=1")
    href = f"/admin?days={days}{other}"
    if include_test:
        return (
            f"<br><b>Se están contando también nuestras pruebas</b> ({n} en este período). "
            f'<a href="{href}">Ver solo a los lectores</a>.'
        )
    if not n:
        return ""
    return (
        f"<br>Fuera de la cuenta quedan <b>{n}</b> consultas nuestras de prueba: no son nadie "
        f'preguntando por su hijo. <a href="{href}">Verlas igualmente</a>.'
    )


def _sin_modelo_line(q: dict[str, Any]) -> str:
    """Callado cuando todo va bien; a gritos cuando el modelo ha fallado.

    Una avería del proveedor no se puede quedar en una fila de la lista de abajo, que hay que
    bajar a leer. Y se dicen por separado sus dos causas: el tope de gasto lo ponemos nosotros y
    es una decisión; que DeepSeek no conteste es otra cosa y quizá haya que mirarla.
    """
    averias, tope = int(q.get("no_model", 0)), int(q.get("degraded", 0))
    if not averias and not tope:
        return ""
    partes = []
    if averias:
        partes.append(f"<b>{averias}</b> porque el modelo no contestó (caído, lento o sin saldo)")
    if tope:
        partes.append(f"<b>{tope}</b> porque se había alcanzado el tope de gasto del día")
    return (
        '<br><span class="warn">Respuestas dadas sin modelo: '
        + " y ".join(partes)
        + ".</span> Llevan las guías y el aviso de urgencia igual que las demás; lo que les falta "
        "es la redacción."
    )


def _unanswered_card(items: list[dict[str, Any]]) -> str:
    """Un número no se puede arreglar; una pregunta sí.

    Cada fila es un hueco del corpus o un fallo del buscador, y hasta hoy había que sacarlas con
    SQL para saber de cuál se trataba (11-sep-2026: de seis, tres eran arreglables).
    """
    if not items:
        return (
            '<div class="card"><h2>Preguntas sin respuesta</h2>'
            '<p class="empty">Ninguna: a todas se les encontró fuente.</p></div>'
        )
    filas = "".join(
        '<tr><td class="dim">{fecha}</td><td class="dim">{lang}</td>'
        "<td>{pregunta}</td></tr>".format(
            fecha=html.escape(_day(str(it.get("ts") or ""))),
            lang=html.escape(str(it.get("lang") or "?")),
            pregunta=html.escape(str(it.get("question") or ""))[:160],
        )
        for it in items
    )
    return (
        f'<div class="card"><h2>Preguntas sin respuesta ({len(items)})</h2>'
        '<p class="dim">Cada una es un hueco del corpus o un fallo del buscador. '
        "Las dos se arreglan; el número solo no dice cuál.</p>"
        f'<table class="t">{filas}</table></div>'
    )


def family_counts(path: pathlib.Path | None = None) -> dict[str, int]:
    """Cuántas cuentas, hijos y medidas hay (19-sep-2026).

    Vive aquí y no en `report.py` porque lee **otra base de datos**: las cuentas están en
    `pedibot_familias.db` y no en la de operación, y esa separación es la que permite que
    aquélla siga prometiendo que no guarda datos personales.

    El primer día no hay ni fichero, y eso son ceros y no un error: el panel se abre igual.

    Sólo `COUNT(*)`. Lo que hay en esas tablas es el nombre de un niño y su fecha de nacimiento,
    y el panel se mira en sitios donde alguien puede estar mirando por encima del hombro.
    """
    if path is None:
        from pedibot.settings import get_settings

        path = pathlib.Path(get_settings().family_db_path)
    vacio = {"accounts": 0, "children": 0, "measurements": 0, "newsletter": 0}
    if not pathlib.Path(path).exists():
        return vacio
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return vacio
    try:
        fuera = dict(vacio)
        fuera["accounts"] = int(con.execute("SELECT count(*) FROM users").fetchone()[0])
        fuera["children"] = int(con.execute("SELECT count(*) FROM children").fetchone()[0])
        fuera["measurements"] = int(con.execute("SELECT count(*) FROM measurements").fetchone()[0])
        fuera["newsletter"] = int(
            con.execute("SELECT count(*) FROM users WHERE newsletter = 1").fetchone()[0]
        )
        return fuera
    except sqlite3.Error:
        # una base a medio crear no puede tumbar el panel entero
        return vacio
    finally:
        con.close()


def family_kpis(c: dict[str, int]) -> str:
    """Las tres casillas de la fila de indicadores. Números, nunca personas."""
    return (
        _kpi("cuentas", c["accounts"])
        + _kpi("hijos apuntados", c["children"])
        + _kpi("medidas", c["measurements"])
    )


def render(con: sqlite3.Connection, days: int, include_test: bool = False) -> str:
    """`include_test` shows our own traffic too, and says on every card which is which.

    By default it does not. The operator opened this page on the 6th of September and found 106
    questions, 103 of them test strings sent from the build machine — a panel that reports our
    own work back to us as readers is a panel that lies about the only thing it exists to say.
    """
    w = report.web_visits(days)
    q = report.questions(con, days, include_test=include_test)
    g = report.guides(days)
    rows = report.recent_answers(con, 80, include_test=include_test)
    flagged = set(load_flagged())
    sin_respuesta = report.unanswered(con, days, include_test=include_test)

    tail = "&tests=1" if include_test else ""

    def link(n: int, label: str | None = None) -> str:
        on = "on" if n == days else ""
        return f'<a href="/admin?days={n}{tail}" class="{on}">{label or f"{n} días"}</a>'

    # what each block of numbers is counting, said out loud. The two are not the same period:
    # questions are every one ever asked; visits are what the journal still had.
    if days > 0:
        period = f"últimos {days} días"
        covered = period
    else:
        period = (
            f"desde el principio ({_day(q['first_day'])})" if q["first_day"] else "todavía nada"
        )
        covers = w.get("covers") or ()
        covered = f"desde el {_day(covers[0])}" if covers else "sin registro"

    h: list[str] = [
        "<!doctype html><html lang=es><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        "<meta name=robots content=noindex><title>PediBot · panel</title>"
        # Este navegador es del equipo: desde ahora el chat pregunta como `test` y cada página
        # del sitio lo avisa a /api/team, así que nada de lo que haga sale aquí como un lector.
        "<script>try{localStorage.setItem('pedibot_team','1')}catch(e){}</script>"
        f"<style>{_CSS}</style></head><body><main>",
        '<div class="top"><h1>PediBot · panel</h1>'
        f'<div class="range">{link(0, "total")}{link(7)}{link(30)}{link(90)}</div></div>',
    ]

    down = q["down"]
    # 16-sep-2026, el operador: «está bien pero demasiado texto explicativo al principio». Cómo
    # se cuenta una visita y qué se descarta es la mitad del valor de este panel —sin eso las
    # cifras no se pueden auditar— pero no es a lo que se entra. Arriba, las cifras y lo que
    # exige una decisión (una avería del modelo, que las pruebas estén contando); el resto,
    # debajo y plegado.
    h.append(
        f'<p class="period">Consultas y guías: <b>{html.escape(period)}</b> · '
        f"Visitas: <b>{html.escape(covered)}</b>."
        + _sin_modelo_line(q)
        + _tests_line(q, days, include_test)
        + "</p>"
        '<details class="howto"><summary>Cómo se cuentan estas cifras</summary><p>'
        "Las visitas salen del registro del servidor, que no guarda desde siempre. "
        "<b>Una visita es alguien que cargó la página entera</b>: además del texto pidió su "
        "hoja de estilo, su JavaScript o un tipo de letra, que es lo que hace un navegador solo "
        "y lo que un rastreador no hace nunca. Se descartan además las direcciones de rastreo "
        "que Google publica como suyas. "
        f"Hubo <b>{w.get('page_requests', 0)}</b> peticiones de página que no se identificaron "
        "como robot pero tampoco probaron ser un navegador, y no se cuentan aquí: "
        "el panel decía 3.227 visitantes donde había 201." + _dwell_sentence(w) + "</p></details>"
        '<div class="kpis">'
        + _kpi("visitas con navegador", w["visitors"])
        + _kpi("vieron 2+ páginas", w.get("returning", 0))
        + _kpi("páginas vistas", w["views"])
        + _kpi("peticiones sin probar navegador", w.get("page_requests", 0))
        + _kpi("cuánto se quedan", _dwell_label(w))
        + _kpi("consultas", q["total"])
        + _kpi("por Telegram", q["telegram"])
        + _kpi("con signo de alarma", q["alarms"], warn=q["alarms"] > 0)
        + _kpi("sin fuente", q["no_source"], warn=q["no_source"] > 0)
        + _kpi("pulgar arriba", q["up"])
        + _kpi("pulgar abajo", down, warn=down > 0)
        + _kpi("guías publicadas", g)
        # 19-sep-2026: las cuentas de familia, que viven en otra base. Van al final de la
        # fila porque son lo más nuevo, y son sólo cifras: el panel no enseña a nadie.
        + family_kpis(family_counts())
        + "</div>"
    )

    h.append(
        '<div class="card"><h2>'
        + ("Visitas y consultas por día" if days > 0 else "Por día, desde el principio")
        + "</h2>"
        + _chart(w["per_day"], q["per_day"], days)
        + "</div>"
    )

    langs = sorted(q["langs"].items(), key=lambda kv: -kv[1])
    levels = sorted(q["levels"].items(), key=lambda kv: -kv[1])
    h.append(
        '<div class="two">'
        '<div class="card"><h2>Páginas más vistas</h2>' + _bars(list(w["top"])) + "</div>"
        '<div class="card"><h2>Consultas por idioma</h2>'
        + _bars([(_LANG_NAME.get(k, k), n) for k, n in langs])
        + '<h2 style="margin-top:18px">Por nivel</h2>'
        + _bars([(_LEVEL_NAME.get(k, k), n) for k, n in levels])
        + "</div></div>"
    )
    # Una tarjeta entera para ella: cada fila es un hueco del corpus o un fallo del buscador,
    # y el contador de arriba («sin fuente: N») nunca dijo cuál de las dos.
    h.append(_unanswered_card(sin_respuesta))

    h.append(_google_card(search.load()))

    h.append(
        f'<div class="card"><h2>Qué se preguntó y qué se respondió '
        f'<span class="bnum">({len(rows)} últimas)</span></h2>'
    )
    if not rows:
        h.append('<p class="empty">Ninguna consulta todavía.</p>')
    for r in rows:
        fb = "👍" if r["feedback"] == 1 else ("👎" if r["feedback"] == -1 else "")
        ver = str(r["verification"])
        good = ver in (
            "ok",
            "regenerated",
            "dose_calculator",
            "vaccine_schedule",
            "growth_chart",
        )
        flag = (
            '<form method=post action="/admin/flag" style="display:inline">'
            f'<input type=hidden name=id value="{r["id"]}">'
            + (
                '<button class="unflag" title="quitar la marca">🚩 marcada — quitar</button>'
                if r["id"] in flagged
                else '<button title="apartarla para revisarla: pedibot flagged las lista">'
                "marcar como mala</button>"
            )
            + "</form>"
        )
        h.append(
            '<div class="qa"><div class="meta">'
            f'<span class="mono">{str(r["ts"])[5:16].replace("T", " ")}</span>'
            f'<span class="tag">{html.escape(_LANG_NAME.get(str(r["lang"]), str(r["lang"])))}</span>'
            f'<span class="tag">{html.escape(str(r["channel"]))}</span>'
            f'<span class="tag lvl-{html.escape(str(r["level"]))}">'
            f"{html.escape(_LEVEL_NAME.get(str(r['level']), str(r['level'])))}</span>"
            + (f'<span class="tag bad">{html.escape(ver)}</span>' if not good else "")
            + (f"<span>{fb}</span>" if fb else "")
            + f'<span style="margin-left:auto">{flag}</span></div>'
            f'<p class="q"><b>{html.escape(str(r["question"]))}</b></p>'
            f"<details><summary>ver la respuesta</summary>"
            f"<pre>{html.escape(_split_answer(str(r['answer']))[0])}</pre>"
            + (
                f'<details class="src"><summary>{len(_split_answer(str(r["answer"]))[1])}'
                " fuentes</summary><pre>"
                + html.escape("\n".join(_split_answer(str(r["answer"]))[1]))
                + "</pre></details>"
                if _split_answer(str(r["answer"]))[1]
                else ""
            )
            + "</details></div>"
        )
    h.append("</div></main></body></html>")
    return "".join(h)


#: The record is stored as `Answer.render_debug()`: answer, then "Fuentes:"/"Sources:" with one
#: numbered line per document, then the legal line. Here the answer is the point — the sources are
#: usually longer than it, and the legal line is identical on every card.
_SOURCE_HEADS = ("Fuentes:", "Sources:", "Quellen:", "Fontes:", "Источники:", "المصادر:", "स्रोत:")


def _split_answer(raw: str) -> tuple[str, list[str]]:
    """(what PediBot said, one line per source)."""
    body, sources = raw, []
    for head in _SOURCE_HEADS:
        marker = "\n\n" + head + "\n"
        if marker in body:
            body, rest = body.split(marker, 1)
            sources = [ln for ln in rest.splitlines() if ln.startswith("[")]
            break
    # the legal line rides at the end of every record and says the same thing every time
    body = body.split("\n\nℹ️ ")[0]
    return body.strip(), sources


def make_router(con_factory: Any) -> APIRouter:
    router = APIRouter()

    @router.get("/admin", response_class=HTMLResponse)
    def admin(days: int = 0, tests: int = 0) -> str:
        """`days=0` is the landing view: the totals. The windows are for the shape of a period.
        `tests=1` adds our own traffic, which is off by default."""
        return render(con_factory(), max(0, min(days, 365)), include_test=bool(tests))

    @router.post("/admin/flag")
    async def flag(request: Request) -> RedirectResponse:
        form = await request.form()
        aid = int(str(form.get("id", "0")))
        con = con_factory()
        row = con.execute(
            "SELECT question, answer, level, verification, lang FROM answers WHERE id=?", (aid,)
        ).fetchone()
        items = load_flagged()
        if aid in items:
            del items[aid]  # a misclick used to be permanent
        elif row:
            items[aid] = {
                "id": aid,
                "ts": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                "lang": row[4],
                "question": row[0],
                "answer": row[1],
                "level": row[2],
                "verification": row[3],
            }
        save_flagged(items)
        return RedirectResponse("/admin", status_code=303)

    return router
