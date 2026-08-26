"""Rare, operator-triggered notices to people who have used the Telegram bot.

No channel, no scheduled broadcasts: only `pedibot announce "..."`, with a 14-day guard, an opt-out
line appended, and 1 message/second so Telegram never rate-limits us.
"""

from __future__ import annotations

import datetime as dt
import time

import httpx
from loguru import logger

from pedibot.ops.store import OpsStore

OPT_OUT = {
    "en": "\n\n— Occasional notice from PediBot. /stop to receive none.",
    "es": "\n\n— Aviso puntual de PediBot. /stop para no recibir ninguno.",
}
MIN_DAYS_BETWEEN = 14


def too_soon(ops: OpsStore, days: int = MIN_DAYS_BETWEEN) -> tuple[bool, str | None]:
    last = ops.last_announcement()
    if not last:
        return False, None
    ts = dt.datetime.fromisoformat(last[0])
    delta = (dt.datetime.now(dt.UTC) - ts).days
    return (delta < days), last[0]


def send_announcement(
    ops: OpsStore, token: str, text: str, lang: str | None = None, dry_run: bool = False
) -> dict[str, int]:
    audience = ops.tg_audience(lang)
    sent = failed = 0
    for chat_id, chat_lang in audience:
        body = text + OPT_OUT.get(chat_lang or "en", OPT_OUT["en"])
        if dry_run:
            sent += 1
            continue
        try:
            r = httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": body, "disable_web_page_preview": False},
                timeout=20,
            )
            if r.status_code == 200:
                sent += 1
            else:
                failed += 1
                if r.status_code == 403:  # blocked the bot
                    ops.set_tg_opt_out(chat_id, True)
        except Exception as e:  # noqa: BLE001
            failed += 1
            logger.warning("announce to {} failed: {}", chat_id, e)
        time.sleep(1.0)
    if not dry_run:
        ops.log_announcement(text, sent, failed)
    return {"audience": len(audience), "sent": sent, "failed": failed}
