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


def slug(text: str, max_len: int = 40) -> str:
    t = text.lower()
    t = (
        t.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
        .replace("ü", "u")
    )
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
