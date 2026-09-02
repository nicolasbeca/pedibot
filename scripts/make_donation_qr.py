"""Generate the QR for the donation address (1-sep-2026).

    uv run python scripts/make_donation_qr.py

It reads the address from web/site/src/donation.ts so there is a single source of truth — a QR
that says something different from the text next to it is the worst possible bug on this page.
The QR encodes the EIP-681 URI (`ethereum:0x...@8453`), which opens the wallet straight on the
transfer screen with the Base network already chosen, instead of the bare address, which several
wallets read as "some text".

Output: web/site/public/donation-qr.svg — our own file, no third-party QR service, which would
otherwise see every visitor of the support page.
"""

from __future__ import annotations

import pathlib
import re
import sys

import segno

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "web" / "site" / "src" / "donation.ts"
OUT = ROOT / "web" / "site" / "public" / "donation-qr.svg"
INK = "#2B3A35"  # same ink as the site; the light module stays transparent


def address() -> str:
    m = re.search(r"DONATION_ADDRESS\s*=\s*'([^']*)'", CONFIG.read_text(encoding="utf-8"))
    if not m or not m.group(1).strip():
        return ""
    value = m.group(1).strip()
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
        raise SystemExit(f"not an EVM address: {value!r}")
    return value


def chain_id() -> int:
    m = re.search(r"DONATION_CHAIN_ID\s*=\s*(\d+)", CONFIG.read_text(encoding="utf-8"))
    return int(m.group(1)) if m else 8453


def main() -> int:
    addr = address()
    if not addr:
        print("no donation address set: nothing to draw")
        return 0
    uri = f"ethereum:{addr}@{chain_id()}"
    segno.make(uri, error="m").save(OUT, scale=6, border=2, dark=INK, light=None)
    print(f"{uri} → {OUT.relative_to(ROOT)}  ({OUT.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
