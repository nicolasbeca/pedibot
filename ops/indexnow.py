"""Tell the search engines the pages exist, without an account (3-sep-2026).

Google Search Console needs the owner's Google session, so submitting the sitemap there is a
manual step nobody can automate from here. IndexNow is the part that can be: Bing, Yandex,
Seznam and Naver accept a plain POST with a list of URLs, authenticated only by a key file the
site itself hosts. One submission covers all of them.

    uv run python ops/indexnow.py            # everything in the sitemap
    uv run python ops/indexnow.py --new 30   # only what changed in the last 30 days
    uv run python ops/indexnow.py --dry-run

The key lives in web/site/public/<key>.txt, so it ships with the site and is served at
https://pedibot.xyz/<key>.txt — which is exactly how the engines check that whoever submitted
the URLs controls the domain.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "web" / "site" / "public"
DIST = ROOT / "web" / "site" / "dist"
HOST = "pedibot.xyz"
ENDPOINT = "https://api.indexnow.org/indexnow"
BATCH = 10_000  # the documented ceiling per request


def key() -> str:
    """The key file already in public/, or a new one written there on first run."""
    existing = sorted(PUBLIC.glob("*.txt"))
    for f in existing:
        if re.fullmatch(r"[0-9a-f]{32}", f.stem) and f.read_text(encoding="utf-8").strip() == f.stem:
            return f.stem
    import secrets

    k = secrets.token_hex(16)
    (PUBLIC / f"{k}.txt").write_text(k, encoding="utf-8")
    print(f"clave IndexNow nueva: {k} (súbela con el próximo despliegue antes de enviar nada)")
    return k


def urls(newer_than_days: int | None = None) -> list[tuple[str, str]]:
    """(URL, lastmod) for every page in the built sitemaps, optionally only recent ones."""
    out: list[tuple[str, str]] = []
    cutoff = None
    if newer_than_days is not None:
        cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=newer_than_days)
    for f in sorted(DIST.glob("sitemap-*.xml")):
        text = f.read_text(encoding="utf-8")
        for m in re.finditer(r"<url>(.*?)</url>", text, re.S):
            loc = re.search(r"<loc>(.*?)</loc>", m.group(1))
            if not loc:
                continue
            mod = re.search(r"<lastmod>(.*?)</lastmod>", m.group(1))
            stamp = mod.group(1) if mod else ""
            if cutoff is not None and stamp:
                when = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                if when < cutoff:
                    continue
            out.append((loc.group(1), stamp))
    return out


def state_path() -> pathlib.Path:
    """What we last told the engines, so we do not tell them again for nothing."""
    return ROOT / "data" / "indexnow_sent.json"


def already_sent() -> dict[str, str]:
    p = state_path()
    if not p.exists():
        return {}
    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        # a corrupt file means we resubmit once, which is harmless; failing here is not
        return {}


def remember(sent: dict[str, str]) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sent, indent=1, sort_keys=True), encoding="utf-8", newline="\n")


def submit(url_list: list[str], k: str) -> tuple[int, str]:
    body = json.dumps(
        {"host": HOST, "key": k, "keyLocation": f"https://{HOST}/{k}.txt", "urlList": url_list}
    ).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            # a named agent, so a rejection can be told apart from a blocked default one
            "User-Agent": f"PediBot/1.0 (+https://{HOST})",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 — fixed endpoint
            return r.status, r.read().decode("utf-8", "replace")[:200]
    except urllib.error.HTTPError as e:
        # 403 SiteVerificationNotCompleted right after publishing the key is normal: the engine
        # has not fetched /<key>.txt yet. Re-run in a few hours; nothing else needs doing.
        return e.code, e.read().decode("utf-8", "replace")[:200]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", type=int, metavar="DAYS", help="sólo lo cambiado en N días")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--all",
        action="store_true",
        help="reenvía aunque ya se enviara con ese mismo lastmod",
    )
    args = ap.parse_args()

    if not DIST.exists():
        print("no hay build en web/site/dist — ejecuta `npx astro build` primero")
        return 2

    k = key()
    found = urls(args.new)
    sent = {} if args.all else already_sent()
    # a page whose lastmod has not moved since we told them is not news
    todo = [(u, m) for u, m in found if args.all or sent.get(u) != m]
    if not todo:
        print(f"nada nuevo que enviar ({len(found)} URLs, todas ya avisadas)")
        return 0
    print(f"{len(todo)} URLs nuevas o cambiadas de {len(found)} · clave {k}")
    if args.dry_run:
        for u, _ in todo[:5]:
            print("   ", u)
        print("    …") if len(todo) > 5 else None
        return 0

    for i in range(0, len(todo), BATCH):
        batch = todo[i : i + BATCH]
        status, body = submit([u for u, _ in batch], k)
        print(f"lote {i // BATCH + 1}: HTTP {status} {body}".rstrip())
        if status not in (200, 202):
            # remember what did get through, so a later failure does not resend everything
            remember(sent)
            return 1
        sent.update(dict(batch))
    remember(sent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
