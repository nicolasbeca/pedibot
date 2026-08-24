"""Section → chunks of ~TARGET words with overlap. Dose tables are never split."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pedibot.ingest.sections import Section

TARGET_WORDS = 320
MAX_WORDS = 480
OVERLAP_WORDS = 40
MIN_WORDS = 40  # chunks smaller than this are merged into a neighbour (table layouts, side boxes)

_DOSE = re.compile(r"\bmg\s*/\s*kg\b|\bmg/kg/d[ií]a\b|\bml/kg\b", re.I)
_RED_FLAG_TITLE = re.compile(
    r"urgencias|112|alarma|cu[aá]ndo (debo|hay que|tengo que) (consultar|acudir|ir)|"
    r"cu[aá]ndo consultar|cu[aá]ndo acudir|signos de gravedad|when to (seek|go|call)|"
    r"emergency|warning signs",
    re.I,
)
_RED_FLAG_TEXT = re.compile(
    r"(acud[ae]|acudir|llam[ae]|llamar)\s+(a|al)\s+(urgencias|112)|llame al 112|"
    r"de forma inmediata|urgentemente",
    re.I,
)
_SENT = re.compile(r"(?<=[\.\?\!])\s+(?=[A-ZÁÉÍÓÚÑ¿¡•\-])")


@dataclass
class RawChunk:
    section: str
    pages: list[int]
    text: str
    is_red_flag: bool
    is_dose_table: bool


def merge_small(
    chunks: list[RawChunk], min_words: int = MIN_WORDS, max_words: int = MAX_WORDS
) -> list[RawChunk]:
    """Merge chunks with < min_words into the previous chunk (or the next one if first).

    Section titles are kept inside the merged text ("TITLE: text") so a drug name that was
    detected as a heading stays searchable. Flags are OR-ed and pages are unioned.
    """
    out: list[RawChunk] = []
    pending: RawChunk | None = None
    for c in chunks:
        if pending is not None:
            c = _merge(pending, c)
            pending = None
        small = len(c.text.split()) < min_words
        if small and out and len(out[-1].text.split()) + len(c.text.split()) <= max_words:
            out[-1] = _merge(out[-1], c)
        elif small and not out:
            pending = c
        else:
            out.append(c)
    if pending is not None:
        out.append(pending)
    return out


def _merge(a: RawChunk, b: RawChunk) -> RawChunk:
    text = a.text if b.section == a.section else f"{a.text} {b.section}: {b.text}"
    if b.section == a.section:
        text = f"{a.text} {b.text}"
    return RawChunk(
        section=a.section,
        pages=sorted(set(a.pages) | set(b.pages)),
        text=text,
        is_red_flag=a.is_red_flag or b.is_red_flag,
        is_dose_table=a.is_dose_table or b.is_dose_table,
    )


def _sentences(text: str) -> list[str]:
    parts = _SENT.split(text)
    return [p.strip() for p in parts if p.strip()]


def chunk_section(sec: Section) -> list[RawChunk]:
    text = sec.text
    words = text.split()
    dose = bool(_DOSE.search(text))
    red = bool(_RED_FLAG_TITLE.search(sec.title)) or bool(_RED_FLAG_TEXT.search(text))
    if len(words) <= MAX_WORDS or dose:
        return [RawChunk(sec.title, sec.pages, text, red, dose)]

    out: list[RawChunk] = []
    buf: list[str] = []
    buf_words = 0
    for sent in _sentences(text):
        n = len(sent.split())
        if buf_words + n > TARGET_WORDS and buf:
            out.append(RawChunk(sec.title, sec.pages, " ".join(buf), red, dose))
            # overlap: keep the tail of the previous chunk
            tail: list[str] = []
            tw = 0
            for s in reversed(buf):
                tw += len(s.split())
                tail.insert(0, s)
                if tw >= OVERLAP_WORDS:
                    break
            buf, buf_words = tail, tw
        buf.append(sent)
        buf_words += n
    if buf:
        out.append(RawChunk(sec.title, sec.pages, " ".join(buf), red, dose))
    return out
