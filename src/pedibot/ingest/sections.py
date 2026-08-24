"""Split cleaned lines into titled sections using font size, case and question patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pedibot.ingest.clean import join_hyphenated
from pedibot.ingest.extract import Extracted, Line

_QUESTION = re.compile(r"^¿.{3,120}\?$")
_ENUM = re.compile(r"^(\d{1,2}[\.\)]|[IVX]{1,4}\.)\s+\S")


@dataclass
class Section:
    title: str
    lines: list[Line] = field(default_factory=list)

    @property
    def pages(self) -> list[int]:
        return sorted({ln.page for ln in self.lines})

    @property
    def text(self) -> str:
        return join_hyphenated(" ".join(ln.text for ln in self.lines)).strip()


def _is_upper(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.9


def is_heading(ln: Line, body_size: float) -> bool:
    t = ln.text.strip()
    if len(t) < 3 or len(t) > 140:
        return False
    if t.endswith((".", ",", ";", ":")) and not t.endswith("?"):
        # sentences are not headings (colons appear in list intros)
        return False
    bigger = body_size > 0 and ln.size >= body_size * 1.15
    if _QUESTION.match(t):
        return True
    if _is_upper(t) and len(t.split()) <= 12:
        return True
    if bigger and len(t.split()) <= 14:
        return True
    if ln.bold and _ENUM.match(t) and len(t.split()) <= 12:
        return True
    return False


def split_sections(ex: Extracted, default_title: str = "Introducción") -> list[Section]:
    sections: list[Section] = [Section(title=default_title)]
    for p in ex.pages:
        for ln in p.lines:
            if is_heading(ln, ex.body_size):
                # merge consecutive heading lines (multi-line titles)
                if not sections[-1].lines and sections[-1].title != default_title:
                    sections[-1].title = f"{sections[-1].title} {ln.text}".strip()
                else:
                    sections.append(Section(title=ln.text.strip()))
            else:
                sections[-1].lines.append(ln)
    return [s for s in sections if s.lines]
