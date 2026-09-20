"""Label the questions logged before anything recorded who asked (6-sep-2026).

Run once, on the server, after deploying the `source` column:

    python3 ops/label_old_rows.py --before 2026-09-06T12:00:00+00:00           # dry run
    python3 ops/label_old_rows.py --before 2026-09-06T12:00:00+00:00 --write

The operator opened /admin and asked whether the questions he was seeing were mine. They were:
of the 106 rows in the database on the 6th of September, 103 are test strings sent from the build
machine while the eight languages were being made. There is no way to see that from the row — the
column that would have said so did not exist — so this labels them from what IS knowable:

  · session prefixed `tg_`      → telegram. The channel is certain; who was on the other end is
                                  not, and two rows do not change any number that matters.
  · session prefixed `agent_`   → agent. The ACP endpoint is the only thing that writes them.
  · id 14                       → unknown. "Hello PediBot, without reviews, anxious parents might
                                  hesitate to trust…" is not one of my test strings and not
                                  anything I sent. Somebody else wrote it. It is left unattributed
                                  rather than guessed at, which means it is not counted either.
  · everything else before the  → test. Mine. I recognise them one by one: they are the golden-set
    cutoff                        questions and the eight-language sweeps, several of them sent
                                  four times in a row a minute apart.

Only rows still marked `unknown` are touched, so a reader who arrives between the deploy and this
script — their row already says `web` — is never relabelled. Nothing is deleted: the rows stay,
the panel simply stops calling them readers.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DB = Path("/opt/pedibot/data/pedibot_ops.db")

#: rows before the cutoff that are NOT mine, with the reason. See the module docstring.
NOT_MINE = {14: "unknown"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DB)
    ap.add_argument("--before", required=True, help="ISO timestamp: the moment source went live")
    ap.add_argument("--write", action="store_true", help="without it, only says what it would do")
    a = ap.parse_args()

    con = sqlite3.connect(a.db)
    rows = con.execute(
        "SELECT id, session FROM answers WHERE ts < ? AND source='unknown' ORDER BY id",
        (a.before,),
    ).fetchall()
    if not rows:
        print("nada que etiquetar")
        return

    plan: dict[str, list[int]] = {}
    for rid, session in rows:
        if rid in NOT_MINE:
            label = NOT_MINE[rid]
        elif str(session).startswith("tg_"):
            label = "telegram"
        elif str(session).startswith("agent_"):
            label = "agent"
        else:
            label = "test"
        plan.setdefault(label, []).append(rid)

    for label, ids in sorted(plan.items()):
        print(f"{label:9} {len(ids):4}  ids {ids[0]}–{ids[-1]}")
    if not a.write:
        print("\n(prueba: nada escrito — repite con --write)")
        return

    for label, ids in plan.items():
        con.executemany("UPDATE answers SET source=? WHERE id=?", [(label, i) for i in ids])
    con.commit()
    left = con.execute("SELECT COUNT(*) FROM answers WHERE source='unknown'").fetchone()[0]
    print(f"\nescrito. quedan {left} sin identificar")


if __name__ == "__main__":
    main()
