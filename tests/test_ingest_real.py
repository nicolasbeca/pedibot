"""Integration on the real PDFs (skipped if FUENTES/ is absent, e.g. on CI)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.index.store import Index, build_index
from pedibot.ingest.catalog import catalog_by_file, load_catalog
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.pipeline import build_chunks


@pytest.fixture(scope="module")
def fiebre_chunks(fuentes_dir: Path, config_dir: Path):
    docs = catalog_by_file(load_catalog(config_dir / "fuentes.yaml"))
    pdf = next(fuentes_dir.rglob("15_Fiebre.pdf"))
    chunks, rep = build_chunks(docs["15_Fiebre.pdf"], pdf, Taxonomy(config_dir / "taxonomia.yaml"))
    return chunks, rep


def test_fiebre_leaflet_is_sectioned(fiebre_chunks):
    chunks, rep = fiebre_chunks
    assert rep.status == "ok" and rep.n_chunks >= 4
    titles = [c.section.lower() for c in chunks]
    assert any("qué es" in t or "que es" in t for t in titles)
    assert all(c.pages for c in chunks)
    assert any(c.is_red_flag for c in chunks), "fever leaflet must have a warning-signs chunk"
    assert all(c.topic == "fiebre" for c in chunks)


def test_search_on_real_leaflet(fiebre_chunks, tmp_path: Path):
    chunks, _ = fiebre_chunks
    db = tmp_path / "f.db"
    build_index(chunks, db)
    hits = Index(db).search("cuándo tengo que ir a urgencias por fiebre", red_flag_boost=True)
    assert hits and hits[0].chunk.is_red_flag
