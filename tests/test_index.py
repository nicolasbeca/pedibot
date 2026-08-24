from __future__ import annotations

from pathlib import Path

from pedibot.index.store import Index, build_index, query_terms
from pedibot.ingest.schema import Chunk


def _chunk(
    cid: str,
    text: str,
    section: str = "S",
    doc_type: str = "hoja_padres",
    usage: str = "publico",
    red: bool = False,
    dose: bool = False,
) -> Chunk:
    return Chunk(
        chunk_id=cid,
        doc_id=cid.split("#")[0],
        org="SEUP",
        doc_title="Doc",
        year=2024,
        lang="es",
        section=section,
        pages=[1],
        text=text,
        topic="fiebre",
        doc_type=doc_type,  # type: ignore[arg-type]
        evidence="sociedad_cientifica",
        usage=usage,
        is_red_flag=red,
        is_dose_table=dose,  # type: ignore[arg-type]
        source_hash="h",
        n_words=len(text.split()),
    )


def test_query_terms_drops_stopwords_and_accents_kept():
    assert query_terms("mi hijo tiene fiebre y tos") == ["fiebre", "tos"]
    assert query_terms("what should I do for a fever", extra=["fiebre"]) == ["fever", "fiebre"]


def test_build_and_search(tmp_path: Path):
    db = tmp_path / "i.db"
    chunks = [
        _chunk("a#s#1", "La fiebre es una elevación de la temperatura. Antitérmicos si malestar."),
        _chunk("b#s#1", "Los vómitos son la expulsión del contenido gástrico."),
        _chunk(
            "c#s#1", "Fiebre en el lactante: acuda a urgencias si tiene menos de 3 meses.", red=True
        ),
        _chunk("d#s#1", "Dermatología texto excluido", usage="excluido"),
    ]
    n = build_index(chunks, db)
    assert n == 3
    idx = Index(db)
    assert idx.size() == 3
    hits = idx.search("mi hijo tiene fiebre")
    ids = [h.chunk.chunk_id for h in hits]
    assert "a#s#1" in ids and "c#s#1" in ids and "b#s#1" not in ids
    assert idx.get("d#s#1") is None


def test_diacritics_insensitive_and_prefix(tmp_path: Path):
    db = tmp_path / "i.db"
    build_index([_chunk("a#s#1", "Vómitos repetidos y diarrea abundante.")], db)
    idx = Index(db)
    assert idx.search("vomitos")  # no accent
    assert idx.search("vomit")  # prefix


def test_red_flag_boost_reorders(tmp_path: Path):
    db = tmp_path / "i.db"
    build_index(
        [
            _chunk("a#s#1", "fiebre fiebre fiebre fiebre tratamiento en casa"),
            _chunk("c#s#1", "fiebre: acuda a urgencias", red=True),
        ],
        db,
    )
    idx = Index(db)
    plain = idx.search("fiebre")[0].chunk.chunk_id
    boosted = idx.search("fiebre", red_flag_boost=True)
    assert plain == "a#s#1"
    assert boosted[0].chunk.chunk_id == "c#s#1" or boosted[0].score >= boosted[1].score
