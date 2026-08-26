"""Weekly report → operator's Telegram (Sunday 08:00 Madrid). Logic lives in pedibot.ops.report."""

from __future__ import annotations

import os
import sqlite3

import httpx

from pedibot.ops.report import weekly_text
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
    con = sqlite3.connect(get_settings().ops_db_path)
    text = weekly_text(con)
    print(text)
    send(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
