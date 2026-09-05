"""End-to-end ingestion: catalog + PDFs → JSONL per document + summary report."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from pedibot.ingest.catalog import catalog_by_file, load_catalog, nfc
from pedibot.ingest.chunk import chunk_section, merge_small
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.clean import clean
from pedibot.ingest.extract import extract_pdf, file_sha256
from pedibot.ingest.extract_html import extract_html
from pedibot.ingest.schema import Chunk, SourceDoc
from pedibot.ingest.sections import split_sections

_SLUG = re.compile(r"[^a-z0-9]+")


# Latin letters with accents are folded to their base letter; whole scripts are transliterated.
# Without this a Cyrillic or Arabic title collapses to the "s" fallback and two guides in the
# same language end up sharing one filename, the second overwriting the first.
_FOLD = str.maketrans({
    "á": "a", "à": "a", "â": "a", "ä": "a", "ã": "a", "å": "a",
    "é": "e", "è": "e", "ê": "e", "ë": "e",
    "í": "i", "ì": "i", "î": "i", "ï": "i",
    "ó": "o", "ò": "o", "ô": "o", "ö": "o", "õ": "o",
    "ú": "u", "ù": "u", "û": "u", "ü": "u",
    "ñ": "n", "ç": "c", "ß": "ss", "ø": "o", "æ": "ae", "œ": "oe",
})

_CYRILLIC = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", "і": "i", "ї": "yi", "є": "ye", "ґ": "g",
}

_ARABIC = {
    "ا": "a", "أ": "a", "إ": "i", "آ": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j",
    "ح": "h", "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s", "ش": "sh",
    "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "a", "غ": "gh", "ف": "f", "ق": "q",
    "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h", "و": "w", "ي": "y", "ى": "a",
    "ة": "a", "ء": "", "ؤ": "u", "ئ": "i",
}


# Devanagari needs a scanner, not a table: a consonant carries an inherent "a" that a vowel sign
# or a virama takes away, so what a letter sounds like depends on the character after it.
# बुखार is "bukhaar" — b-u-kh-aa-r — and not "ba-u-kha-a-ra".
_DEV_CONS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "ळ": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
}
# the same letters with a nukta under them, which Hindi uses for sounds Sanskrit did not have
_DEV_NUKTA = {"क": "q", "ख": "kh", "ग": "gh", "ज": "z", "ड": "r", "ढ": "rh", "फ": "f"}
_DEV_VOWELS = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऍ": "e", "ऑ": "o",
}
_DEV_MATRA = {
    "ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॅ": "e", "ॉ": "o",
}
_DEV_SIGNS = {"ं": "n", "ँ": "n", "ः": "h", "ऽ": "", "़": ""}
_DEV_DIGITS = {"०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
               "५": "5", "६": "6", "७": "7", "८": "8", "९": "9"}
_VIRAMA = "\u094d"
_NUKTA = "\u093c"


def devanagari(text: str) -> str:
    """Romanise Devanagari. Readability for a URL, not a scholarly scheme."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in _DEV_CONS:
            base = _DEV_CONS[c]
            i += 1
            if i < n and text[i] == _NUKTA:
                base = _DEV_NUKTA.get(c, base)
                i += 1
            out.append(base)
            if i < n and text[i] in _DEV_MATRA:
                out.append(_DEV_MATRA[text[i]])
                i += 1
            elif i < n and text[i] == _VIRAMA:
                i += 1  # the inherent vowel is exactly what a virama removes
            elif i < n and "ऀ" <= text[i] <= "ॿ":
                out.append("a")  # inside a word the inherent vowel is heard
            # at the end of a word Hindi drops it: बुखार is "bukhaar", not "bukhaara"
            continue
        for table in (_DEV_VOWELS, _DEV_MATRA, _DEV_SIGNS, _DEV_DIGITS):
            if c in table:
                out.append(table[c])
                break
        else:
            out.append(c)
        i += 1
    return "".join(out)


_TRANSLIT = {**_CYRILLIC, **_ARABIC}


def slug(text: str, max_len: int = 40) -> str:
    t = text.lower().translate(_FOLD)
    if any("\u0900" <= c <= "\u097f" for c in t):
        t = devanagari(t)
    t = "".join(_TRANSLIT.get(c, c) for c in t)
    t = _SLUG.sub("_", t).strip("_")
    return t[:max_len].strip("_") or "s"


@dataclass
class DocReport:
    doc_id: str
    file: str
    status: str  # ok | skipped_excluded | no_text | unchanged | error
    n_pages: int = 0
    n_words: int = 0
    n_sections: int = 0
    n_chunks: int = 0
    n_red_flag: int = 0
    n_dose: int = 0
    detail: str = ""


def build_chunks(doc: SourceDoc, pdf: Path, tax: Taxonomy) -> tuple[list[Chunk], DocReport]:
    ex = clean(extract_html(pdf) if pdf.suffix.lower() in (".html", ".htm") else extract_pdf(pdf))
    rep = DocReport(doc.doc_id, pdf.name, "ok", n_pages=len(ex.pages), n_words=ex.n_words)
    if ex.n_words < 50:
        rep.status = "no_text"
        rep.detail = "scanned or protected PDF — needs OCR"
        return [], rep
    sections = split_sections(ex)
    rep.n_sections = len(sections)
    chunks: list[Chunk] = []
    seen: dict[str, int] = {}
    raw = merge_small([rc for sec in sections for rc in chunk_section(sec)])
    for rc in raw:
        if True:
            base = f"{doc.doc_id}#{slug(rc.section)}"
            seen[base] = seen.get(base, 0) + 1
            cid = f"{base}#{seen[base]}"
            text = rc.text
            topic = doc.topic if doc.topic != "auto" else (tax.topic_for(text) or "general")
            ch = Chunk(
                chunk_id=cid,
                doc_id=doc.doc_id,
                org=doc.org,
                doc_title=doc.title,
                year=doc.year,
                lang=doc.lang,
                section=rc.section,
                pages=rc.pages,
                text=text,
                topic=topic,
                subtopics=tax.subtopics_for(text),
                age_groups=doc.age_groups if doc.age_groups != ["auto"] else tax.ages_for(text),
                doc_type=doc.doc_type,
                evidence=doc.evidence,
                usage=doc.usage,
                is_red_flag=rc.is_red_flag,
                is_dose_table=rc.is_dose_table,
                is_dose_source=doc.dose_source,
                source_url=doc.url,
                source_hash=ex.sha256,
                n_words=len(text.split()),
            )
            chunks.append(ch)
    rep.n_chunks = len(chunks)
    rep.n_red_flag = sum(c.is_red_flag for c in chunks)
    rep.n_dose = sum(c.is_dose_table for c in chunks)
    return chunks, rep


def _hash_of_existing(out_file: Path) -> str | None:
    if not out_file.exists():
        return None
    with out_file.open(encoding="utf-8") as f:
        first = f.readline()
    if not first:
        return None
    return json.loads(first).get("source_hash")


def run_ingest(
    sources_dir: Path, out_dir: Path, catalog_path: Path, taxonomy_path: Path, force: bool = False
) -> list[DocReport]:
    docs = load_catalog(catalog_path)
    by_file = catalog_by_file(docs)
    tax = Taxonomy(taxonomy_path)
    chunks_dir = out_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    reports: list[DocReport] = []
    pdfs = {
        nfc(p.name): p for p in list(sources_dir.rglob("*.pdf")) + list(sources_dir.rglob("*.html"))
    }

    for name, doc in by_file.items():
        pdf = pdfs.get(name)
        if pdf is None:
            reports.append(DocReport(doc.doc_id, name, "error", detail="file not found"))
            continue
        if doc.usage == "excluido":
            reports.append(DocReport(doc.doc_id, name, "skipped_excluded"))
            continue
        out_file = chunks_dir / f"{doc.doc_id}.jsonl"
        if not force and _hash_of_existing(out_file) == file_sha256(pdf):
            reports.append(DocReport(doc.doc_id, name, "unchanged"))
            continue
        try:
            chunks, rep = build_chunks(doc, pdf, tax)
        except Exception as e:  # noqa: BLE001
            reports.append(DocReport(doc.doc_id, name, "error", detail=str(e)))
            logger.exception("ingest failed for {}", name)
            continue
        if chunks:
            with out_file.open("w", encoding="utf-8") as f:
                for c in chunks:
                    f.write(c.model_dump_json() + "\n")
        reports.append(rep)
        logger.info("{} → {} chunks ({})", name, rep.n_chunks, rep.status)

    for name in sorted(set(pdfs) - set(by_file)):
        reports.append(DocReport("?", name, "error", detail="PDF not in catalog"))
    return reports


def load_all_chunks(out_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for f in sorted((out_dir / "chunks").glob("*.jsonl")):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    chunks.append(Chunk.model_validate_json(line))
    return chunks
