"""Text cleaning: hyphenation, whitespace, repeated headers/footers, noise lines."""

from __future__ import annotations

import re
from collections import Counter

from pedibot.ingest.extract import Extracted, Line

_WS = re.compile(r"[ \t ]+")
_HYPHEN_BREAK = re.compile(r"(\w)-\s+(\w)")
_LEAFLET_HEADER = re.compile(
    r"^informaci[oó]n para padres$|^informaci[oó]n para (madres|padres) y (padres|madres)$", re.I
)
_PAGE_NUM = re.compile(r"^\s*(página\s+)?\d{1,3}(\s*/\s*\d{1,3})?\s*$", re.I)


def normalize_line(text: str) -> str:
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = _WS.sub(" ", text).strip()
    return text


def join_hyphenated(text: str) -> str:
    """'infec- ción' → 'infección' (only when the break is inside a word)."""
    return _HYPHEN_BREAK.sub(r"\1\2", text)


def repeated_lines(ex: Extracted, min_pages: int = 3, ratio: float = 0.6) -> set[str]:
    """Lines that appear on ≥ ratio of pages (and ≥ min_pages) are headers/footers."""
    n_pages = len(ex.pages)
    if n_pages < min_pages:
        return set()
    c: Counter[str] = Counter()
    for p in ex.pages:
        seen = {normalize_line(ln.text).lower() for ln in p.lines}
        c.update(seen)
    return {t for t, n in c.items() if n >= max(min_pages, int(n_pages * ratio)) and len(t) > 3}


def clean(ex: Extracted) -> Extracted:
    noise = repeated_lines(ex)
    for p in ex.pages:
        kept: list[Line] = []
        for ln in p.lines:
            t = normalize_line(ln.text)
            if not t or _PAGE_NUM.match(t) or _LEAFLET_HEADER.match(t) or t.lower() in noise:
                continue
            kept.append(Line(text=t, size=ln.size, bold=ln.bold, page=ln.page))
        p.lines = kept
    return ex
