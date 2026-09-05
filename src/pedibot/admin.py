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
import sqlite3
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from pedibot.ops import report
from pedibot.settings import ROOT

FLAGGED = ROOT / "eval" / "flagged.jsonl"

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
        span = [
            (start + dt.timedelta(days=i)).isoformat() for i in range((end - start).days + 1)
        ]
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
    "en": "English", "es": "Español", "fr": "Français", "de": "Deutsch",
    "ru": "Русский", "ar": "العربية", "pt": "Português", "hi": "हिन्दी",
}

#: The triage levels are internal words and they decide whether a red banner sits above a
#: parent's answer. On a panel written in Spanish they should be readable.
_LEVEL_NAME = {
    "routine": "rutina",
    "mental_health": "salud mental",
    "urgent": "urgente (hoy)",
    "emergency": "emergencia (ahora)",
}


def render(con: sqlite3.Connection, days: int) -> str:
    w = report.web_visits(days)
    q = report.questions(con, days)
    g = report.guides(days)
    rows = report.recent_answers(con, 80)
    flagged: set[int] = set()
    if FLAGGED.exists():
        for line in FLAGGED.read_text(encoding="utf-8").splitlines():
            try:
                flagged.add(json.loads(line).get("id"))
            except json.JSONDecodeError:
                pass

    def link(n: int, label: str | None = None) -> str:
        on = "on" if n == days else ""
        return f'<a href="/admin?days={n}" class="{on}">{label or f"{n} días"}</a>'

    # what each block of numbers is counting, said out loud. The two are not the same period:
    # questions are every one ever asked; visits are what the journal still had.
    if days > 0:
        period = f"últimos {days} días"
        covered = period
    else:
        period = f"desde el principio ({_day(q['first_day'])})" if q["first_day"] else "todavía nada"
        covers = w.get("covers") or ()
        covered = f"desde el {_day(covers[0])}" if covers else "sin registro"

    h: list[str] = [
        "<!doctype html><html lang=es><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        "<meta name=robots content=noindex><title>PediBot · panel</title>"
        f"<style>{_CSS}</style></head><body><main>",
        '<div class="top"><h1>PediBot · panel</h1>'
        f'<div class="range">{link(0, "total")}{link(7)}{link(30)}{link(90)}</div></div>',
    ]

    down = q["down"]
    h.append(
        f'<p class="period">Consultas y guías: <b>{html.escape(period)}</b>. '
        f'Visitas: <b>{html.escape(covered)}</b> — salen del registro del servidor, que no '
        "guarda desde siempre.</p>"
        '<div class="kpis">'
        + _kpi("visitantes", w["visitors"])
        + _kpi("páginas vistas", w["views"])
        + _kpi("consultas", q["total"])
        + _kpi("por Telegram", q["telegram"])
        + _kpi("con signo de alarma", q["alarms"], warn=q["alarms"] > 0)
        + _kpi("sin fuente", q["no_source"], warn=q["no_source"] > 0)
        + _kpi("pulgar arriba", q["up"])
        + _kpi("pulgar abajo", down, warn=down > 0)
        + _kpi("guías publicadas", g)
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
        '<div class="card"><h2>Páginas más vistas</h2>'
        + _bars(list(w["top"]))
        + "</div>"
        '<div class="card"><h2>Consultas por idioma</h2>'
        + _bars([(_LANG_NAME.get(k, k), n) for k, n in langs])
        + '<h2 style="margin-top:18px">Por nivel</h2>'
        + _bars([(_LEVEL_NAME.get(k, k), n) for k, n in levels])
        + "</div></div>"
    )

    h.append(
        f'<div class="card"><h2>Qué se preguntó y qué se respondió '
        f'<span class="bnum">({len(rows)} últimas)</span></h2>'
    )
    if not rows:
        h.append('<p class="empty">Ninguna consulta todavía.</p>')
    for r in rows:
        fb = "👍" if r["feedback"] == 1 else ("👎" if r["feedback"] == -1 else "")
        ver = str(r["verification"])
        good = ver in ("ok", "regenerated", "dose_calculator")
        flag = (
            '<span class="tag bad">marcada 🚩</span>'
            if r["id"] in flagged
            else (
                '<form method=post action="/admin/flag" style="display:inline">'
                f'<input type=hidden name=id value="{r["id"]}">'
                '<button title="guardar en el golden set como respuesta mala">marcar como mala</button>'
                "</form>"
            )
        )
        h.append(
            '<div class="qa"><div class="meta">'
            f'<span class="mono">{str(r["ts"])[5:16].replace("T", " ")}</span>'
            f'<span class="tag">{html.escape(_LANG_NAME.get(str(r["lang"]), str(r["lang"])))}</span>'
            f'<span class="tag">{html.escape(str(r["channel"]))}</span>'
            f'<span class="tag lvl-{html.escape(str(r["level"]))}">'
            f'{html.escape(_LEVEL_NAME.get(str(r["level"]), str(r["level"])))}</span>'
            + (f'<span class="tag bad">{html.escape(ver)}</span>' if not good else "")
            + (f"<span>{fb}</span>" if fb else "")
            + f"<span style=\"margin-left:auto\">{flag}</span></div>"
            f'<p class="q"><b>{html.escape(str(r["question"]))}</b></p>'
            f"<details><summary>ver la respuesta</summary>"
            f"<pre>{html.escape(_split_answer(str(r['answer']))[0])}</pre>"
            + (
                f"<details class=\"src\"><summary>{len(_split_answer(str(r['answer']))[1])}"
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
    def admin(days: int = 0) -> str:
        """`days=0` is the landing view: the totals. The windows are for the shape of a period."""
        return render(con_factory(), max(0, min(days, 365)))

    @router.post("/admin/flag")
    async def flag(request: Request) -> RedirectResponse:
        form = await request.form()
        aid = int(str(form.get("id", "0")))
        con = con_factory()
        row = con.execute(
            "SELECT question, answer, level, verification FROM answers WHERE id=?", (aid,)
        ).fetchone()
        if row:
            FLAGGED.parent.mkdir(parents=True, exist_ok=True)
            with FLAGGED.open("a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "id": aid,
                            "ts": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                            "question": row[0],
                            "answer": row[1],
                            "level": row[2],
                            "verification": row[3],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        return RedirectResponse("/admin", status_code=303)

    return router
