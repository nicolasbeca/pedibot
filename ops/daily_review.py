"""Yesterday's questions → operator's Telegram. Silent on a day with none.

Logic lives in pedibot.ops.daily; this is the wire, matching ops/weekly_report.py.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import httpx

from pedibot.ops.daily import daily_text
from pedibot.settings import get_settings


def send(text: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print(text)
        return False
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": text},
        timeout=20,
    )
    return r.status_code == 200


def main() -> int:
    from pedibot.admin import load_flagged

    day = sys.argv[1] if len(sys.argv) > 1 else None
    con = sqlite3.connect(get_settings().ops_db_path)
    text = daily_text(con, day, flagged=set(load_flagged()))
    if text is None:
        # No questions is not news. A message every morning saying nothing happened is a message
        # that stops being read, and this one exists to be read.
        print("sin consultas: no se envía nada")
        return 0
    print(text)
    send(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
