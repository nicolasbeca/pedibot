"""The donation address is the one place on the site where a typo costs money (1-sep-2026).

Two failure modes worth a lock: publishing a placeholder that swallows donations, and pasting an
address that is already ours for something else. The PDBT contract would burn anything sent to
it; the PediBot agent wallet on Virtuals is under Privy custody with a signer policy and is tied
to the operator's account, which defeats the point of a separate donation wallet.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "web" / "site" / "src" / "donation.ts"

# addresses that must never be used to receive donations
PDBT_CONTRACT = "0x196a67ba334dbed501e19baec47d217bb2fc15e1"
AGENT_WALLET = "0x30d331ee2dc619ad4c353969b18586e5c0ce3ebb"


def _address() -> str:
    m = re.search(r"DONATION_ADDRESS\s*=\s*'([^']*)'", CONFIG.read_text(encoding="utf-8"))
    assert m, "DONATION_ADDRESS not found in web/site/src/donation.ts"
    return m.group(1).strip()


def test_the_address_is_either_empty_or_a_real_one():
    """Empty is fine — the block simply does not render. Half an address is not."""
    address = _address()
    if address:
        assert re.fullmatch(r"0x[0-9a-fA-F]{40}", address), f"not an EVM address: {address!r}"


def test_it_is_not_one_of_our_other_addresses():
    address = _address().lower()
    assert address != PDBT_CONTRACT, "that is the token contract: anything sent there is lost"
    assert address != AGENT_WALLET, "that is the ACP agent wallet, tied to the Virtuals account"


def test_the_block_is_only_built_when_there_is_an_address():
    built = ROOT / "web" / "site" / "dist" / "support" / "index.html"
    if not built.exists():
        return  # the site has not been built in this checkout
    html = built.read_text(encoding="utf-8", errors="ignore")
    if _address():
        assert _address() in html, "there is an address but the support page does not show it"
    else:
        assert "Donate directly" not in html, "a donation block was published with no address"


def test_the_listed_networks_have_the_right_chain_ids():
    """A wrong id in the wallet link sends the donor to the wrong network. Checked on 1-sep
    against a public RPC on each one: the address is a plain account on all six."""
    text = CONFIG.read_text(encoding="utf-8")
    expected = {
        "Base": 8453,
        "Ethereum": 1,
        "Arbitrum": 42161,
        "Optimism": 10,
        "Polygon": 137,
        "BNB Chain": 56,
    }
    found = dict(re.findall(r"\{\s*id:\s*(\d+),\s*name:\s*'([^']+)'", text))
    got = {name: int(cid) for cid, name in found.items()}
    assert got == expected, got


def test_only_one_network_is_recommended():
    text = CONFIG.read_text(encoding="utf-8")
    assert text.count("recommended: true") == 1


def test_the_page_no_longer_says_base_only():
    """It did while Base was the only network listed; saying it now would be false and would
    scare off a donor who only holds funds on Ethereum or BNB."""
    built = ROOT / "web" / "site" / "dist" / "support" / "index.html"
    if built.exists():
        html = built.read_text(encoding="utf-8", errors="ignore")
        assert "Base network only" not in html
        assert "Ethereum" in html and "BNB Chain" in html
