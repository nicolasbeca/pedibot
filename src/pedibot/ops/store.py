"""SQLite ops store. No personal data: the session id is a random token, IPs are hashed with a
per-deployment salt and only used for rate limiting (CLAUDE.md clinical rule 8)."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    session TEXT NOT NULL,
    lang TEXT NOT NULL,
    country TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    level TEXT NOT NULL,
    verification TEXT NOT NULL,
    chunk_ids TEXT NOT NULL,
    prompt_version TEXT,
    model TEXT,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    feedback INTEGER
);
CREATE INDEX IF NOT EXISTS answers_ts ON answers(ts);
CREATE TABLE IF NOT EXISTS ratelimit (
    ip_hash TEXT NOT NULL,
    ts TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ratelimit_ip ON ratelimit(ip_hash, ts);
"""


@dataclass
class AnswerRecord:
    session: str
    lang: str
    country: str | None
    question: str
    answer: str
    level: str
    verification: str
    chunk_ids: list[str]
    prompt_version: str | None
    model: str | None
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


class OpsStore:
    def __init__(self, path: Path, salt: str = "pedibot"):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(path, check_same_thread=False)
        self.con.executescript(_SCHEMA)
        self.salt = salt

    # ---- answers ----
    def log_answer(self, r: AnswerRecord) -> int:
        cur = self.con.execute(
            "INSERT INTO answers (ts, session, lang, country, question, answer, level, verification,"
            " chunk_ids, prompt_version, model, tokens_in, tokens_out, cost_usd, latency_ms)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                _now(),
                r.session,
                r.lang,
                r.country,
                r.question,
                r.answer,
                r.level,
                r.verification,
                json.dumps(r.chunk_ids),
                r.prompt_version,
                r.model,
                r.tokens_in,
                r.tokens_out,
                r.cost_usd,
                r.latency_ms,
            ),
        )
        self.con.commit()
        return int(cur.lastrowid or 0)

    def set_feedback(self, answer_id: int, session: str, value: int) -> bool:
        """value: +1 / -1. Only the owning session may rate."""
        cur = self.con.execute(
            "UPDATE answers SET feedback=? WHERE id=? AND session=?", (value, answer_id, session)
        )
        self.con.commit()
        return cur.rowcount == 1

    def cost_today_usd(self) -> float:
        day = _now()[:10]
        row = self.con.execute(
            "SELECT COALESCE(SUM(cost_usd),0) FROM answers WHERE ts >= ?", (day,)
        ).fetchone()
        return float(row[0])

    def stats(self, days: int = 7) -> dict[str, object]:
        since = (dt.datetime.now(dt.UTC) - dt.timedelta(days=days)).isoformat(timespec="seconds")
        q = self.con.execute
        n = q("SELECT COUNT(*) FROM answers WHERE ts>=?", (since,)).fetchone()[0]
        cost = q("SELECT COALESCE(SUM(cost_usd),0) FROM answers WHERE ts>=?", (since,)).fetchone()[
            0
        ]
        by_ver = dict(
            q(
                "SELECT verification, COUNT(*) FROM answers WHERE ts>=? GROUP BY 1", (since,)
            ).fetchall()
        )
        by_level = dict(
            q("SELECT level, COUNT(*) FROM answers WHERE ts>=? GROUP BY 1", (since,)).fetchall()
        )
        up = q("SELECT COUNT(*) FROM answers WHERE ts>=? AND feedback=1", (since,)).fetchone()[0]
        down = q("SELECT COUNT(*) FROM answers WHERE ts>=? AND feedback=-1", (since,)).fetchone()[0]
        return {
            "days": days,
            "answers": n,
            "cost_usd": round(float(cost), 4),
            "by_verification": by_ver,
            "by_level": by_level,
            "thumbs_up": up,
            "thumbs_down": down,
        }

    # ---- rate limiting ----
    def ip_hash(self, ip: str) -> str:
        return hashlib.sha256(f"{self.salt}:{ip}".encode()).hexdigest()[:24]

    def hit_and_count(self, ip: str, window_minutes: int) -> int:
        """Record a hit for this IP and return the number of hits in the window (incl. this one)."""
        h = self.ip_hash(ip)
        now = dt.datetime.now(dt.UTC)
        self.con.execute(
            "INSERT INTO ratelimit VALUES (?,?)", (h, now.isoformat(timespec="seconds"))
        )
        cutoff = (now - dt.timedelta(minutes=window_minutes)).isoformat(timespec="seconds")
        self.con.execute(
            "DELETE FROM ratelimit WHERE ts < ?", ((now - dt.timedelta(days=1)).isoformat(),)
        )
        self.con.commit()
        return int(
            self.con.execute(
                "SELECT COUNT(*) FROM ratelimit WHERE ip_hash=? AND ts>=?", (h, cutoff)
            ).fetchone()[0]
        )

    def count_day(self, ip: str) -> int:
        h = self.ip_hash(ip)
        cutoff = (dt.datetime.now(dt.UTC) - dt.timedelta(days=1)).isoformat(timespec="seconds")
        return int(
            self.con.execute(
                "SELECT COUNT(*) FROM ratelimit WHERE ip_hash=? AND ts>=?", (h, cutoff)
            ).fetchone()[0]
        )
