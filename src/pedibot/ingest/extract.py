"""PDF → list of pages with lines annotated by font size (for heading detection)."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # pymupdf


@dataclass
class Line:
    text: str
    size: float
    bold: bool = False
    page: int = 0


@dataclass
class PageText:
    number: int  # 1-based
    lines: list[Line] = field(default_factory=list)


@dataclass
class Extracted:
    path: Path
    sha256: str
    pages: list[PageText]
    body_size: float

    @property
    def n_words(self) -> int:
        return sum(len(ln.text.split()) for p in self.pages for ln in p.lines)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def extract_pdf(path: Path) -> Extracted:
    doc = fitz.open(path)
    pages: list[PageText] = []
    size_counter: Counter[float] = Counter()
    for pno, page in enumerate(doc, start=1):
        pt = PageText(number=pno)
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                spans = [s for s in line["spans"] if s["text"].strip()]
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans).strip()
                size = max(s["size"] for s in spans)
                bold = any("Bold" in s["font"] or (s["flags"] & 16) for s in spans)
                size_counter[round(size, 1)] += len(text)
                pt.lines.append(Line(text=text, size=round(size, 1), bold=bold, page=pno))
        pages.append(pt)
    body_size = size_counter.most_common(1)[0][0] if size_counter else 0.0
    return Extracted(path=path, sha256=file_sha256(path), pages=pages, body_size=body_size)
