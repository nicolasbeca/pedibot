"""Load and validate the source catalog (`config/fuentes.yaml`)."""

from __future__ import annotations

import unicodedata
from pathlib import Path

import yaml

from pedibot.ingest.schema import SourceDoc


def load_catalog(path: Path) -> list[SourceDoc]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    docs = [SourceDoc(**d) for d in raw["sources"]]
    ids = [d.doc_id for d in docs]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate doc_id in catalog: {sorted(dupes)}")
    return docs


def catalog_by_file(docs: list[SourceDoc]) -> dict[str, SourceDoc]:
    """Map basename of the PDF → SourceDoc (files live in FUENTES/ and FUENTES/Subidos/)."""
    return {nfc(Path(d.file).name): d for d in docs}


def nfc(name: str) -> str:
    return unicodedata.normalize("NFC", name)
