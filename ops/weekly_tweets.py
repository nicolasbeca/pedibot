"""Seven drafts to the operator's Telegram, one message each, ready to copy (6-sep-2026).

Logic lives in pedibot.ops.tweets; this is the wire, matching ops/daily_review.py.

One message per draft, and NOTHING else in it — no heading, no numbering, no "here are this
week's". He asked for that explicitly: a message he has to edit before pasting is a message he
will not paste. Anything that needs saying (how many were thrown away and why) goes to the
journal, where it belongs, not on top of the text he is about to post.

Usage:
    python3 ops/weekly_tweets.py            # write and send (seven)
    python3 ops/weekly_tweets.py --n 10     # a bigger batch, when he asks for one
    python3 ops/weekly_tweets.py --dry-run  # write and print, send nothing
"""

from __future__ import annotations

import os
import sys
import time

import httpx

from pedibot.ops.tweets import facts, load_history, remember, write_batch
from pedibot.settings import ROOT, get_settings

HOW_MANY = 7


def how_many(argv: list[str]) -> int:
    """`--n 10` cuando el operador pide una tanda mayor; siete es lo semanal (16-sep-2026)."""
    if "--n" in argv:
        i = argv.index("--n")
        if i + 1 < len(argv) and argv[i + 1].isdigit():
            return max(1, min(20, int(argv[i + 1])))
    return HOW_MANY


def send(text: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print(text)
        return False
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        # no parse_mode: the text goes out exactly as written. Markdown would eat an underscore
        # or an asterisk and hand him a post with a word missing.
        # no preview either — there are no links in these, and it keeps the message clean.
        json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    if r.status_code != 200:
        print(f"telegram {r.status_code}: {r.text[:200]}", file=sys.stderr)
    return r.status_code == 200


def main() -> int:
    dry = "--dry-run" in sys.argv
    s = get_settings()
    f = facts(ROOT, s.index_db_path)
    print(
        f"datos medidos: {f['guides']} guías · {f['languages']} idiomas · "
        f"{f['documents']} documentos · {f['organisations']} organismos"
    )

    from pedibot.bot.llm import provider_from_settings

    drafts, rejected = write_batch(
        provider_from_settings(), f, how_many(sys.argv[1:]), tuple(load_history(ROOT))
    )
    for why in rejected:
        print(f"  descartado — {why}", file=sys.stderr)
    if not drafts:
        # Silence beats a message saying it failed: the watchdog already reports a unit that
        # exits non-zero, and this one is read for its content or not at all.
        print("ningún borrador pasó la verificación: no se envía nada", file=sys.stderr)
        return 1

    sent = 0
    for t in drafts:
        if dry:
            print(f"\n--- {len(t)} car.\n{t}")
            continue
        if send(t):
            sent += 1
        # Telegram allows one message per second per chat and these go out as a burst
        time.sleep(1.2)
    if not dry:
        remember(ROOT, drafts[:sent])
        print(f"enviados {sent} de {len(drafts)} ({len(rejected)} descartados por el verificador)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
