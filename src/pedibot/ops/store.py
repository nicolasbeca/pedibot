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
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session TEXT NOT NULL,
    ts TEXT NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS turns_session ON turns(session, id);
CREATE TABLE IF NOT EXISTS tg_users (
    chat_id INTEGER PRIMARY KEY,
    lang TEXT,
    country TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    opted_out INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    text TEXT NOT NULL,
    sent INTEGER NOT NULL,
    failed INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS shares (
    token TEXT PRIMARY KEY,
    answer_id INTEGER NOT NULL,
    ts TEXT NOT NULL
);
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

    def answers_today(self, session: str) -> int:
        """How many questions this browser has asked since midnight UTC.

        By session, not by address: the token lives in the reader's own localStorage and never
        leaves their browser except attached to their own questions. /legal promises the answers
        are stored "with a random session identifier, no IP address", and this keeps that.
        """
        day = _now()[:10]
        return int(
            self.con.execute(
                "SELECT COUNT(*) FROM answers WHERE session=? AND substr(ts,1,10)=?",
                (session, day),
            ).fetchone()[0]
        )

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

    # ---- conversation turns (short window, expire with the session) ----
    def add_turn(self, session: str, role: str, text: str) -> None:
        self.con.execute(
            "INSERT INTO turns (session, ts, role, text) VALUES (?,?,?,?)",
            (session, _now(), role, text),
        )
        self.con.commit()

    def history(
        self, session: str, max_turns: int = 6, max_age_hours: int = 24
    ) -> list[dict[str, str]]:
        cutoff = (dt.datetime.now(dt.UTC) - dt.timedelta(hours=max_age_hours)).isoformat(
            timespec="seconds"
        )
        rows = self.con.execute(
            "SELECT role, text FROM turns WHERE session=? AND ts>=? ORDER BY id DESC LIMIT ?",
            (session, cutoff, max_turns),
        ).fetchall()
        return [{"role": r, "text": t} for r, t in reversed(rows)]

    # ---- public shares (I-28): the answer text only, never the session ----
    def create_share(self, answer_id: int, session: str) -> str | None:
        import secrets

        row = self.con.execute(
            "SELECT 1 FROM answers WHERE id=? AND session=?", (answer_id, session)
        ).fetchone()
        if not row:
            return None
        token = secrets.token_urlsafe(9)
        self.con.execute("INSERT INTO shares VALUES (?,?,?)", (token, answer_id, _now()))
        self.con.commit()
        return token

    def get_share(self, token: str) -> dict[str, object] | None:
        row = self.con.execute(
            "SELECT a.question, a.answer, a.level, a.lang, a.ts FROM shares s"
            " JOIN answers a ON a.id = s.answer_id WHERE s.token=?",
            (token,),
        ).fetchone()
        if not row:
            return None
        return {"question": row[0], "answer": row[1], "level": row[2], "lang": row[3], "ts": row[4]}

    # ---- Telegram audience (chat ids, so the bot can reply and send rare notices) ----
    def touch_tg_user(self, chat_id: int, lang: str | None, country: str | None) -> None:
        now = _now()
        self.con.execute(
            "INSERT INTO tg_users (chat_id, lang, country, first_seen, last_seen) VALUES (?,?,?,?,?)"
            " ON CONFLICT(chat_id) DO UPDATE SET last_seen=excluded.last_seen,"
            " lang=COALESCE(excluded.lang, tg_users.lang), country=COALESCE(excluded.country, tg_users.country)",
            (chat_id, lang, country, now, now),
        )
        self.con.commit()

    def set_tg_opt_out(self, chat_id: int, opted_out: bool) -> None:
        self.con.execute(
            "UPDATE tg_users SET opted_out=? WHERE chat_id=?", (int(opted_out), chat_id)
        )
        self.con.commit()

    def tg_audience(self, lang: str | None = None) -> list[tuple[int, str | None]]:
        sql = "SELECT chat_id, lang FROM tg_users WHERE opted_out=0"
        params: list[object] = []
        if lang:
            sql += " AND COALESCE(lang,'en')=?"
            params.append(lang)
        return [(int(r[0]), r[1]) for r in self.con.execute(sql, params).fetchall()]

    def last_announcement(self) -> tuple[str, str] | None:
        row = self.con.execute(
            "SELECT ts, text FROM announcements ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return (str(row[0]), str(row[1])) if row else None

    def log_announcement(self, text: str, sent: int, failed: int) -> None:
        self.con.execute(
            "INSERT INTO announcements (ts, text, sent, failed) VALUES (?,?,?,?)",
            (_now(), text, sent, failed),
        )
        self.con.commit()

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
