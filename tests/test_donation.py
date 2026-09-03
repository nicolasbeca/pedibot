"""The donation addresses are the one place on the site where a typo costs money (1-sep-2026).

Three failure modes worth a lock: publishing a placeholder that swallows donations, pasting an
address that is already ours for something else, and — since 3-sep-2026, when Solana and HyperEVM
joined — putting an address on the wrong network's card, which loses the money just as surely.

The PDBT contract would burn anything sent to it; the PediBot agent wallet on Virtuals is under
Privy custody with a signer policy and is tied to the operator's account, which defeats the point
of a separate donation wallet.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "web" / "site" / "src" / "donation.ts"

# addresses that must never be used to receive donations
PDBT_CONTRACT = "0x196a67ba334dbed501e19baec47d217bb2fc15e1"
AGENT_WALLET = "0x30d331ee2dc619ad4c353969b18586e5c0ce3ebb"

EVM = re.compile(r"^0x[0-9a-fA-F]{40}$")
BASE58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def _wallets() -> list[dict[str, str]]:
    text = CONFIG.read_text(encoding="utf-8")
    assert "DONATION_WALLETS" in text, "DONATION_WALLETS not found in web/site/src/donation.ts"
    out = []
    for block in re.split(r"\n  \{", text.split("DONATION_WALLETS")[1])[1:]:
        key = re.search(r"key:\s*'([^']+)'", block)
        kind = re.search(r"kind:\s*'([^']+)'", block)
        addr = re.search(r"address:\s*'([^']*)'", block)
        if key and kind and addr:
            out.append(
                {"key": key.group(1), "kind": kind.group(1), "address": addr.group(1).strip()}
            )
    assert out, "no wallet parsed"
    return out


def test_every_address_is_either_empty_or_a_real_one():
    """Empty is fine — that card simply does not render. Half an address is not."""
    for w in _wallets():
        if not w["address"]:
            continue
        pattern = EVM if w["kind"] == "evm" else BASE58
        assert pattern.fullmatch(w["address"]), f"{w['key']}: bad address {w['address']!r}"


def test_no_address_is_one_of_our_other_addresses():
    for w in _wallets():
        low = w["address"].lower()
        assert low != PDBT_CONTRACT, f"{w['key']}: that is the token contract, funds are burnt"
        assert low != AGENT_WALLET, f"{w['key']}: that is the ACP agent wallet"


def test_no_address_is_repeated_across_wallets():
    """Each network was given its own wallet on purpose; the same one twice means a paste slip."""
    addresses = [w["address"].lower() for w in _wallets() if w["address"]]
    assert len(addresses) == len(set(addresses)), addresses


def test_a_solana_address_is_never_offered_as_evm():
    """The failure this guards is silent and total: an EVM link built from a Solana key sends the
    donor to a chain where that address does not exist."""
    for w in _wallets():
        if w["kind"] == "evm":
            assert w["address"].startswith("0x"), f"{w['key']} is listed as EVM but is not 0x…"
        else:
            assert not w["address"].startswith("0x"), f"{w['key']} is not EVM but looks like it"


def test_every_live_wallet_has_its_own_qr():
    """A QR that says a different address from the text printed beside it is the worst bug here,
    so each one is drawn from this same file by scripts/make_donation_qr.py."""
    public = ROOT / "web" / "site" / "public"
    for w in _wallets():
        if not w["address"] or not any(public.glob("donation-qr-*.svg")):
            continue  # not generated in this checkout
        qr = public / f"donation-qr-{w['key']}.svg"
        assert qr.exists(), f"no QR for {w['key']} — run scripts/make_donation_qr.py"
        assert qr.stat().st_size > 200, f"{qr.name} looks empty"


def test_the_block_is_only_built_when_there_is_an_address():
    built = ROOT / "web" / "site" / "dist" / "support" / "index.html"
    if not built.exists():
        return  # the site has not been built in this checkout
    html = built.read_text(encoding="utf-8", errors="ignore")
    live = [w for w in _wallets() if w["address"]]
    if live:
        for w in live:
            assert w["address"] in html, f"{w['key']} is set but the support page does not show it"
    else:
        assert "Donate directly" not in html, "a donation block was published with no address"


def test_the_listed_networks_have_the_right_chain_ids():
    """A wrong id in the wallet link sends the donor to the wrong network. Checked against a
    public RPC on each: the six EVM ones on 1-sep, HyperEVM on 3-sep (eth_chainId → 0x3e7)."""
    text = CONFIG.read_text(encoding="utf-8")
    expected = {
        "Base": 8453,
        "Ethereum": 1,
        "Arbitrum": 42161,
        "Optimism": 10,
        "Polygon": 137,
        "BNB Chain": 56,
        "HyperEVM": 999,
        "Solana": 0,  # not an EVM chain id, and it never reaches a wallet link
    }
    found = dict(re.findall(r"\{\s*id:\s*(\d+),\s*name:\s*'([^']+)'", text))
    got = {name: int(cid) for cid, name in found.items()}
    assert got == expected, got


def test_only_one_network_is_recommended():
    text = CONFIG.read_text(encoding="utf-8")
    assert text.count("recommended: true") == 1


def test_the_page_no_longer_says_base_only():
    """It did while Base was the only network listed; saying it now would be false and would
    scare off a donor who only holds funds on Ethereum, BNB or Solana."""
    built = ROOT / "web" / "site" / "dist" / "support" / "index.html"
    if built.exists():
        html = built.read_text(encoding="utf-8", errors="ignore")
        assert "Base network only" not in html
        assert "Ethereum" in html and "BNB Chain" in html and "Solana" in html
