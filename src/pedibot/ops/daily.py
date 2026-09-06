"""The day's questions and what PediBot answered (5-sep-2026).

The operator asked for this weeks ago: "deberíamos diariamente revisar qué se ha preguntado y qué
se ha respondido para saber si se está haciendo bien". The panel shows it; nothing ever said
there was something to look at.

**It is silent on a day with no questions.** At today's traffic that is most days, and a message
that says "nothing happened" every morning is a message that stops being read — which is exactly
how the panel ended up abandoned before it was rewritten. The rule the project already follows on
Telegram is the same one: push when there is something.

What it says is chosen so it can be read on a phone without opening anything: how many, and then
the ones that need eyes first — a thumbs down, an answer with no source, an emergency, one the
operator already marked. Then the questions themselves, because reading what people actually type
is the point, and the numbers are only there to say how much of it there is.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Any

from pedibot.ops.store import REAL_ONLY

LEVEL_MARK = {"emergency": "🚨", "urgent": "🚨", "mental_health": "💛"}
LANG_NAME = {
    "en": "inglés", "es": "español", "fr": "francés", "de": "alemán",
    "ru": "ruso", "ar": "árabe", "pt": "portugués", "hi": "hindi",
}


def _rows(con: sqlite3.Connection, day: str) -> list[dict[str, Any]]:
    con.row_factory = sqlite3.Row
    return [
        dict(r)
        for r in con.execute(
            "SELECT id, ts, lang, level, verification, feedback, question, session "
            # readers only: the review exists to be read at breakfast, and a morning spent
            # reading yesterday's test strings is the review being trained to be ignored
            "FROM answers WHERE substr(ts,1,10)=?" + REAL_ONLY + " ORDER BY id",
            (day,),
        )
    ]


def daily_text(
    con: sqlite3.Connection, day: str | None = None, flagged: set[int] | None = None
) -> str | None:
    """The review for `day` (default: yesterday), or None when there is nothing to review."""
    day = day or (dt.date.today() - dt.timedelta(days=1)).isoformat()
    rows = _rows(con, day)
    if not rows:
        return None

    flagged = flagged or set()
    d = dt.date.fromisoformat(day)
    out = [f"📋 PediBot · qué se preguntó el {d.strftime('%d/%m')}", ""]

    langs = sorted({str(r["lang"]) for r in rows})
    tg = sum(1 for r in rows if str(r["session"]).startswith("tg_"))
    out.append(
        f"{len(rows)} consultas (web {len(rows) - tg}, Telegram {tg}) · "
        + ", ".join(LANG_NAME.get(x, x) for x in langs)
    )

    # what needs eyes, and why. Ordered by how much it needs them.
    needs: list[tuple[str, list[dict[str, Any]]]] = [
        ("👎 marcadas como no útiles", [r for r in rows if r["feedback"] == -1]),
        ("🚩 marcadas por ti", [r for r in rows if r["id"] in flagged]),
        (
            "❓ sin fuente que las respalde",
            [r for r in rows if r["verification"] in ("no_source", "fallback")],
        ),
        (
            "🚨 con signo de alarma",
            [r for r in rows if str(r["level"]) not in ("routine", "")],
        ),
    ]

    def line(r: dict[str, Any], mark: str = "") -> str:
        return f"  {mark}· {str(r['question'])[:90]}" if mark else f"  · {str(r['question'])[:90]}"

    shown: set[int] = set()
    for title, group in needs:
        group = [r for r in group if r["id"] not in shown]
        if not group:
            continue
        # every member of the group counts as shown, listed or not: an answer that appears under
        # "12 with a warning sign" and then again in "the rest" reads like two different answers
        shown.update(r["id"] for r in group)
        out.append("")
        out.append(f"{title} ({len(group)}):")
        out.extend(line(r) for r in group[:6])
        if len(group) > 6:
            out.append(f"  … y {len(group) - 6} más, en /admin")

    rest = [r for r in rows if r["id"] not in shown]
    if rest:
        out.append("")
        out.append("El resto:")
        out.extend(line(r, LEVEL_MARK.get(str(r["level"]), "")) for r in rest[:12])
        if len(rest) > 12:
            out.append(f"  … y {len(rest) - 12} más")

    out.append("")
    out.append("Las respuestas, en /admin. Lo que esté mal, márcalo ahí.")
    return "\n".join(out)
