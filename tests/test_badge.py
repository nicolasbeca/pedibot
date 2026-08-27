"""The LaunchLeague badge is served from our own domain (27-ago-2026).

/legal promises no third-party trackers and that the visitor's IP is only ever a salted hash on
our side; embedding the badge from their CDN would hand every visitor's IP to a third party. The
SVG is theirs, self-contained (paths only, no fonts), so we host it.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SECTIONS = ROOT / "web" / "site" / "src" / "components" / "Sections.astro"


def test_both_badge_files_are_present():
    for name in ("launchleague-badge-light.svg", "launchleague-badge-dark.svg"):
        f = ROOT / "web" / "site" / "public" / name
        assert f.exists(), f"{name} is missing"
        assert f.read_text(encoding="utf-8").lstrip().startswith("<svg")


def test_the_badge_is_not_loaded_from_a_third_party():
    html = SECTIONS.read_text(encoding="utf-8")
    assert 'src="/launchleague-badge-light.svg"' in html
    assert "cdn.launchleague.xyz" not in html, "serve the badge from our own domain"
    assert 'href="https://launchleague.xyz/?product=pedibot-ai"' in html
