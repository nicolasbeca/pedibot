"""Build and query the SQLite/FTS5 index."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from pedibot.ingest.schema import Chunk

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    data TEXT NOT NULL,
    usage TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    topic TEXT NOT NULL,
    is_red_flag INTEGER NOT NULL,
    is_dose_table INTEGER NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED, text, section, doc_title,
    tokenize = 'unicode61 remove_diacritics 2'
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""

_TOKEN = re.compile(r"[\wáéíóúñü]+", re.I)
STOP = {
    "de",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "y",
    "o",
    "que",
    "en",
    "a",
    "con",
    "por",
    "para",
    "mi",
    "hijo",
    "hija",
    "tiene",
    "es",
    "se",
    "le",
    "al",
    "del",
    "the",
    "my",
    "is",
    "has",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "for",
    "on",
    "with",
    "child",
    "son",
    "daughter",
    "he",
    "she",
    "it",
    "his",
    "her",
    "i",
    "what",
    "should",
    "do",
    "can",
    "qué",
    "cómo",
    "como",
    "hago",
    "doy",
    "puedo",
    "años",
    "año",
    "meses",
    "mes",
    "old",
    "years",
    "year",
    "months",
    "month",
    "weeks",
    "week",
    "days",
    "day",
    "días",
    "dia",
    "día",
    "much",
    "puede",
    "pueden",
    "puedes",
    "comer",
    "hacer",
    "normal",
    "tener",
    "how",
    "many",
    "cuánto",
    "cuanto",
    "cuánta",
    "cuanta",
    "give",
    "dar",
    "darle",
}
_DOSE_QUERY = re.compile(
    r"\b(dosis|dose|dosage|mg|ml|kilos?|kg|paracetamol|ibuprofen\w*|acetaminophen|cu[aá]nt[oa]|how much)\b",
    re.I,
)


DOC_TYPE_WEIGHT = {
    "hoja_padres": 1.6,
    "calendario": 1.3,
    "guia_clinica": 1.15,
    "informe": 0.8,
    "manual": 0.75,
    "libro": 0.55,
}


@dataclass
class Hit:
    chunk: Chunk
    score: float  # higher is better (negated bm25)
    matched_terms: int


def build_index(
    chunks: list[Chunk], db_path: Path, include_usage: tuple[str, ...] = ("publico", "citar_solo")
) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(_SCHEMA)
    n = 0
    for c in chunks:
        if c.usage not in include_usage:
            continue
        con.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?)",
            (
                c.chunk_id,
                c.doc_id,
                c.model_dump_json(),
                c.usage,
                c.doc_type,
                c.topic,
                int(c.is_red_flag),
                int(c.is_dose_table),
            ),
        )
        con.execute(
            "INSERT INTO chunks_fts VALUES (?,?,?,?)",
            (c.chunk_id, c.text, c.section, c.doc_title),
        )
        n += 1
    con.execute("INSERT OR REPLACE INTO meta VALUES ('n_chunks', ?)", (str(n),))
    con.commit()
    con.close()
    return n


def query_terms(query: str, extra: list[str] | None = None) -> list[str]:
    terms = [t.lower() for t in _TOKEN.findall(query)]
    terms = [t for t in terms if len(t) >= 3 and t not in STOP]
    for e in extra or []:
        for t in _TOKEN.findall(e.lower()):
            if len(t) >= 3 and t not in terms:
                terms.append(t)
    return terms


def _fts_expr(terms: list[str]) -> str:
    # prefix match on each term, OR-ed; FTS5 needs quoting
    return " OR ".join(f'"{t}"*' for t in terms)


class Index:
    def __init__(self, db_path: Path):
        if not db_path.exists():
            raise FileNotFoundError(f"index not found: {db_path} (run `pedibot ingest` first)")
        self.con = sqlite3.connect(
            db_path, check_same_thread=False
        )  # read-only use from API threads

    def size(self) -> int:
        row = self.con.execute("SELECT v FROM meta WHERE k='n_chunks'").fetchone()
        return int(row[0]) if row else 0

    def get(self, chunk_id: str) -> Chunk | None:
        row = self.con.execute("SELECT data FROM chunks WHERE chunk_id=?", (chunk_id,)).fetchone()
        return Chunk.model_validate_json(row[0]) if row else None

    def red_flag_chunk(self, doc_id: str) -> Chunk | None:
        """The warning-signs chunk of a document (for triage rules to cite their own source)."""
        row = self.con.execute(
            "SELECT data FROM chunks WHERE doc_id=? AND is_red_flag=1 ORDER BY chunk_id LIMIT 1",
            (doc_id,),
        ).fetchone()
        if row is None:
            row = self.con.execute(
                "SELECT data FROM chunks WHERE doc_id=? ORDER BY chunk_id LIMIT 1", (doc_id,)
            ).fetchone()
        return Chunk.model_validate_json(row[0]) if row else None

    def search(
        self,
        query: str,
        top_k: int = 6,
        extra_terms: list[str] | None = None,
        prefer_parent_leaflets: bool = True,
        red_flag_boost: bool = False,
        topic: str | None = None,
        boost_topic: str | None = None,
    ) -> list[Hit]:
        terms = query_terms(query, extra_terms)
        if not terms:
            return []
        dose_query = bool(_DOSE_QUERY.search(query))
        sql = (
            "SELECT f.chunk_id, bm25(chunks_fts, 0, 1.0, 2.0, 3.0) AS r, c.data "
            "FROM chunks_fts f JOIN chunks c ON c.chunk_id = f.chunk_id "
            "WHERE chunks_fts MATCH ? "
        )
        params: list[object] = [_fts_expr(terms)]
        if topic:
            sql += "AND c.topic = ? "
            params.append(topic)
        sql += "ORDER BY r LIMIT ?"
        params.append(top_k * 5)
        rows = self.con.execute(sql, params).fetchall()
        hits: list[Hit] = []
        for _cid, r, data in rows:
            ch = Chunk.model_validate_json(data)
            score = -float(r)
            low = (ch.text + " " + ch.section).lower()
            matched = sum(1 for t in terms if t in low)
            if prefer_parent_leaflets:
                score *= DOC_TYPE_WEIGHT.get(ch.doc_type, 1.0)
            if boost_topic and ch.topic == boost_topic:
                score *= 1.5
            elif boost_topic and ch.topic not in (boost_topic, "general"):
                score *= (
                    0.7  # off-topic leaflets (heat stroke vs fever) must not outrank on-topic ones
                )
            if (
                red_flag_boost
                and ch.is_red_flag
                and (boost_topic is None or ch.topic == boost_topic)
            ):
                score *= 1.3
            if dose_query and ch.is_dose_table:
                score *= 1.6
            hits.append(Hit(ch, score, matched))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]


def dump_index_stats(db_path: Path) -> dict[str, int]:
    con = sqlite3.connect(db_path)
    stats = {
        "chunks": con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
        "docs": con.execute("SELECT COUNT(DISTINCT doc_id) FROM chunks").fetchone()[0],
        "red_flag": con.execute("SELECT COUNT(*) FROM chunks WHERE is_red_flag=1").fetchone()[0],
        "dose": con.execute("SELECT COUNT(*) FROM chunks WHERE is_dose_table=1").fetchone()[0],
    }
    con.close()
    return stats


def chunks_to_json(hits: list[Hit]) -> str:
    return json.dumps(
        [
            {"chunk_id": h.chunk.chunk_id, "score": round(h.score, 3), "section": h.chunk.section}
            for h in hits
        ],
        ensure_ascii=False,
        indent=2,
    )
