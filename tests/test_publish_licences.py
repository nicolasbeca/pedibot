"""Licence lock for published content (26-ago-2026).

`usage: citar_solo` means: index it, cite it by name, but never reproduce it in a public article.
`gather_hits` filtered the *extra* passages by usage but not the anchors named in TOPIC_PLAN, and
one topic (choking) anchored on a book with an ISBN. Nothing had been published from it yet.
"""

from __future__ import annotations

import pathlib

import yaml

from pedibot.index.store import Index, build_index
from pedibot.ingest.schema import Chunk
from pedibot.publish.articles import TOPIC_PLAN, gather_hits

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _usage_by_doc() -> dict[str, str]:
    usage: dict[str, str] = {}
    for name in ("fuentes.yaml", "fuentes_web.yaml"):
        f = ROOT / "config" / name
        if f.exists():
            for d in yaml.safe_load(f.read_text(encoding="utf-8"))["sources"]:
                usage[d["doc_id"]] = d["usage"]
    return usage


def test_every_article_anchor_is_publicly_reproducible():
    usage = _usage_by_doc()
    offenders = [
        (topic, doc, usage.get(doc, "UNKNOWN"))
        for topic, plan in TOPIC_PLAN.items()
        for doc in plan["docs"]
        if usage.get(doc) != "publico"
    ]
    assert offenders == [], f"articles would reproduce restricted sources: {offenders}"


def _c(cid: str, usage: str) -> Chunk:
    return Chunk(
        chunk_id=cid,
        doc_id=cid.split("#")[0],
        org="ORG",
        doc_title="Doc",
        year=2024,
        lang="es",
        section="S",
        pages=[1],
        text="atragantamiento maniobra golpes interescapulares cuerpo extraño en la via aerea",
        topic="accidentes",
        doc_type="hoja_padres",  # type: ignore[arg-type]
        evidence="sociedad_cientifica",
        usage=usage,  # type: ignore[arg-type]
        source_hash="h",
        n_words=12,
    )


def test_gather_hits_drops_restricted_sources(tmp_path: pathlib.Path, monkeypatch):
    db = tmp_path / "i.db"
    build_index([_c("libro#1", "citar_solo"), _c("hoja#1", "publico")], db)
    monkeypatch.setitem(
        TOPIC_PLAN,
        "_test",
        {"query": "atragantamiento", "docs": ["libro", "hoja"], "slug": {}, "title": {}},
    )
    got = {h.chunk.doc_id for h in gather_hits(Index(db), "_test")}
    assert got == {"hoja"}
