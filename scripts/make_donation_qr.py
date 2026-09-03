"""Generate one QR per donation wallet (1-sep-2026, three wallets since 3-sep-2026).

    uv run python scripts/make_donation_qr.py

It reads the wallets from web/site/src/donation.ts so there is a single source of truth — a QR
that says something different from the address printed next to it is the worst possible bug on
this page.

Each QR encodes a URI rather than the bare address, because several wallets read a bare string as
"some text": `ethereum:0x…@8453` opens straight on the transfer screen with the right network
already chosen, and `solana:…` does the equivalent on Solana wallets.

Output: web/site/public/donation-qr-<key>.svg — our own files, no third-party QR service, which
would otherwise see every visitor of the support page.
"""

from __future__ import annotations

import pathlib
import re
import sys

import segno

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "web" / "site" / "src" / "donation.ts"
PUBLIC = ROOT / "web" / "site" / "public"
INK = "#2B3A35"  # same ink as the site; the light module stays transparent

EVM = re.compile(r"^0x[0-9a-fA-F]{40}$")
BASE58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def wallets() -> list[dict[str, str]]:
    """Every wallet in donation.ts: key, kind, address and the chain its QR aims at."""
    text = CONFIG.read_text(encoding="utf-8")
    out: list[dict[str, str]] = []
    for block in re.split(r"\n  \{", text.split("DONATION_WALLETS")[1])[1:]:
        key = re.search(r"key:\s*'([^']+)'", block)
        kind = re.search(r"kind:\s*'([^']+)'", block)
        addr = re.search(r"address:\s*'([^']*)'", block)
        chain = re.search(r"defaultChainId:\s*(\d+)", block)
        first_chain = re.search(r"\{\s*id:\s*(\d+)", block)
        if not (key and kind and addr) or not addr.group(1).strip():
            continue
        out.append(
            {
                "key": key.group(1),
                "kind": kind.group(1),
                "address": addr.group(1).strip(),
                "chain": (chain or first_chain).group(1) if (chain or first_chain) else "0",
            }
        )
    return out


def uri(w: dict[str, str]) -> str:
    """The same URI the page links to. A mismatch here sends money to the wrong place."""
    if w["kind"] == "evm":
        if not EVM.fullmatch(w["address"]):
            raise SystemExit(f"not an EVM address: {w['address']!r}")
        return f"ethereum:{w['address']}@{w['chain']}"
    if not BASE58.fullmatch(w["address"]):
        raise SystemExit(f"not a base58 address: {w['address']!r}")
    return f"solana:{w['address']}"


def main() -> int:
    found = wallets()
    if not found:
        print("no donation wallet set: nothing to draw")
        return 0
    # a QR left over from a wallet that no longer exists would still be reachable by URL
    for stale in PUBLIC.glob("donation-qr*.svg"):
        stale.unlink()
    for w in found:
        out = PUBLIC / f"donation-qr-{w['key']}.svg"
        segno.make(uri(w), error="m").save(out, scale=6, border=2, dark=INK, light=None)
        print(f"{uri(w)} → {out.relative_to(ROOT)}  ({out.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
