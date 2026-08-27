"""robots.txt is where a crawler looks for the sitemap (26-ago-2026: it was returning 404)."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROBOTS = ROOT / "web" / "site" / "public" / "robots.txt"


def test_robots_exists_and_points_at_the_sitemap():
    assert ROBOTS.exists(), "web/site/public/robots.txt is missing"
    text = ROBOTS.read_text(encoding="utf-8")
    assert "Sitemap: https://pedibot.xyz/sitemap-index.xml" in text


def test_robots_keeps_the_private_paths_out():
    text = ROBOTS.read_text(encoding="utf-8")
    for path in ("/api/", "/a/", "/admin"):
        assert f"Disallow: {path}" in text
