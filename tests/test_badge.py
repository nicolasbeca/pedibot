"""The LaunchLeague badge was retired on 2-sep-2026 after measuring it.

Seven days on the leaderboard brought 20 distinct visitors and not one question to the bot: they
opened the home page, a few looked at /dose and /guides, and left. The listing is free and stays;
the badge does not, because it put a startup-competition mark on a paediatric health page and
sent an outbound link from both home pages.

What is locked here is the rule that outlives the decision: if the badge ever goes back, it is
served from our own domain. /legal promises no third-party requests, and handing every visitor's
IP to another company for a decorative image is not a trade worth making.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SECTIONS = ROOT / "web" / "site" / "src" / "components" / "Sections.astro"


def test_the_badge_is_not_on_the_site_any_more():
    html = SECTIONS.read_text(encoding="utf-8")
    assert "launchleague.xyz/?product=" not in html
    assert "launchleague-badge" not in html


def test_if_it_ever_comes_back_it_is_self_hosted():
    """The two SVGs stay in public/ precisely so that putting it back never means reaching for
    their CDN."""
    html = SECTIONS.read_text(encoding="utf-8")
    assert "cdn.launchleague.xyz" not in html, "serve the badge from our own domain"
    for name in ("launchleague-badge-light.svg", "launchleague-badge-dark.svg"):
        f = ROOT / "web" / "site" / "public" / name
        assert f.exists(), f"{name} is missing"
        assert f.read_text(encoding="utf-8").lstrip().startswith("<svg")
