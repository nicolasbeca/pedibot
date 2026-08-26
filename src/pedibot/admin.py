"""Operator panel at /admin (protected by Caddy basic auth in production; never linked publicly).

Server-rendered HTML, no framework: metrics of the last 7/30 days, PDBT series, recent
conversations with verification/feedback, and a "flag" button that appends the case to
eval/flagged.jsonl so it can join the golden set later."""

from __future__ import annotations

import datetime as dt
import html
import json
import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from pedibot.ops import report
from pedibot.settings import ROOT

FLAGGED = ROOT / "eval" / "flagged.jsonl"

_CSS = """
body{margin:0;background:#FFFDF9;color:#2B3A35;font-family:"Atkinson Hyperlegible",system-ui,sans-serif;font-size:15px}
main{max-width:1100px;margin:0 auto;padding:24px 18px}h1,h2{font-family:Nunito,sans-serif;margin:0 0 8px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:14px 0 24px}
.k{background:#fff;border:1px solid #EAE4DA;border-radius:14px;padding:12px 14px}.k b{display:block;font-family:"JetBrains Mono",monospace;font-size:1.4rem;color:#1F4F40}
.k span{color:#8A9992;font-size:.85rem}table{width:100%;border-collapse:collapse;font-size:.9rem}td,th{padding:6px 8px;border-bottom:1px solid #EAE4DA;vertical-align:top;text-align:left}
.lvl-urgent,.lvl-emergency{color:#C0392B;font-weight:700}.lvl-mental_health{color:#B7791F;font-weight:700}.ok{color:#2F6B57}.bad{color:#C0392B}
details summary{cursor:pointer;color:#2F6B57}pre{white-space:pre-wrap;background:#FFF6EA;padding:10px;border-radius:10px;font-size:.85rem}
button{border:1px solid #EAE4DA;background:#fff;border-radius:999px;padding:3px 10px;cursor:pointer}.bar{display:inline-block;height:8px;background:#C8E9E0;border-radius:4px}
.mono{font-family:"JetBrains Mono",monospace}a{color:#2F6B57}
"""


def _kpi(label: str, value: object) -> str:
    return f'<div class="k"><b>{html.escape(str(value))}</b><span>{html.escape(label)}</span></div>'


def _series(d: dict[str, int]) -> str:
    if not d:
        return "<p>—</p>"
    mx = max(d.values()) or 1
    return "".join(
        f'<div><span class="mono" style="display:inline-block;width:90px">{k}</span><span class="bar" style="width:{int(200 * v / mx)}px"></span> {v}</div>'
        for k, v in d.items()
    )


def render(con: sqlite3.Connection, days: int) -> str:
    w = report.web_visits(days)
    q = report.questions(con, days)
    tk = report.token(con, days)
    g = report.guides(days)
    bal = report.balance()
    rows = report.recent_answers(con, 60)
    flagged = set()
    if FLAGGED.exists():
        for line in FLAGGED.read_text(encoding="utf-8").splitlines():
            try:
                flagged.add(json.loads(line).get("id"))
            except json.JSONDecodeError:
                pass
    h = [
        f"<!doctype html><html><head><meta charset=utf-8><meta name=robots content=noindex><title>PediBot admin</title><style>{_CSS}</style></head><body><main>"
    ]
    h.append(
        f'<h1>PediBot · admin</h1><p>Últimos <a href="/admin?days=7">7</a> · <a href="/admin?days=30">30</a> · <a href="/admin?days=90">90</a> días — generado {dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M")} UTC</p>'
    )
    h.append(
        '<div class="grid">'
        + _kpi("páginas vistas", w["views"])
        + _kpi("visitantes únicos", w["visitors"])
        + _kpi("vistas del chat", w["chat_pageviews"])
        + _kpi("consultas", q["total"])
        + _kpi("web / telegram", f"{q['web']} / {q['telegram']}")
        + _kpi("con alarma", q["alarms"])
        + _kpi("sin fuente", q["no_source"])
        + _kpi("👍 / 👎", f"{q['up']} / {q['down']}")
        + _kpi("coste IA (USD)", f"{q['cost']:.3f}")
        + _kpi("saldo DeepSeek", f"{bal:.2f}" if bal is not None else "?")
        + _kpi("guías publicadas", g)
        + "</div>"
    )
    if tk:
        h.append(
            '<h2>PDBT</h2><div class="grid">'
            + _kpi("compras", tk["buys"])
            + _kpi("ventas", tk["sells"])
            + _kpi("volumen USD", f"{tk['volume']:.0f}")
            + _kpi("precio USD", f"{tk['price']:.7f}")
            + _kpi("variación", f"{tk['price_change_pct']:+.1f} %")
            + _kpi("FDV USD", f"{tk['fdv']:.0f}")
            + _kpi("liquidez USD", f"{tk['liquidity']:.0f}")
            + "</div>"
        )
        h.append(
            "<table><tr><th>día</th><th>precio</th><th>compras</th><th>ventas</th></tr>"
            + "".join(
                f"<tr><td class=mono>{d}</td><td class=mono>{p:.7f}</td><td>{b}</td><td>{s}</td></tr>"
                for d, p, b, s in tk["series"]
            )
            + "</table>"
        )
    h.append(
        "<h2>Visitas por día</h2>"
        + _series(w["per_day"])
        + "<h2>Consultas por día</h2>"
        + _series(q["per_day"])
    )
    h.append(
        "<h2>Páginas más vistas</h2><table>"
        + "".join(f"<tr><td class=mono>{html.escape(u)}</td><td>{n}</td></tr>" for u, n in w["top"])
        + "</table>"
    )
    h.append(
        f"<p>Idiomas: {html.escape(json.dumps(q['langs']))} · niveles: {html.escape(json.dumps(q['levels']))}</p>"
    )
    h.append(
        "<h2>Últimas conversaciones</h2><table><tr><th>#</th><th>cuándo</th><th>canal</th><th>nivel</th><th>verif.</th><th>fb</th><th>coste</th><th>pregunta / respuesta</th><th></th></tr>"
    )
    for r in rows:
        fb = "👍" if r["feedback"] == 1 else ("👎" if r["feedback"] == -1 else "")
        ver = r["verification"]
        vcls = "ok" if ver in ("ok", "regenerated", "dose_calculator") else "bad"
        flag = (
            "🚩"
            if r["id"] in flagged
            else f'<form method=post action="/admin/flag" style="display:inline"><input type=hidden name=id value="{r["id"]}"><button title="marcar como mala para el golden set">flag</button></form>'
        )
        h.append(
            f'<tr><td class=mono>{r["id"]}</td><td class=mono>{str(r["ts"])[5:16]}</td><td>{r["channel"]}</td><td class="lvl-{r["level"]}">{r["level"]}</td><td class="{vcls}">{ver}</td><td>{fb}</td><td class=mono>{r["cost_usd"]:.4f}</td>'
            f"<td><details><summary>{html.escape(str(r['question'])[:110])}</summary><pre>{html.escape(str(r['answer']))}</pre></details></td><td>{flag}</td></tr>"
        )
    h.append("</table></main></body></html>")
    return "".join(h)


def make_router(con_factory) -> APIRouter:  # type: ignore[no-untyped-def]
    router = APIRouter()

    @router.get("/admin", response_class=HTMLResponse)
    def admin(days: int = 7) -> str:
        return render(con_factory(), max(1, min(days, 365)))

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
