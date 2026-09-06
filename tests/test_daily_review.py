"""The daily review, and the days it says nothing (5-sep-2026).

Asked for weeks ago: a way to know what was asked and what was answered without having to
remember to look. The panel shows it and never says there is something to see.

The rule that matters most here is the silence. At this traffic most days have no questions at
all, and a message every morning saying so is a message that stops being read — which is exactly
how the panel ended up abandoned before it was rewritten. So a day with nothing produces nothing.
"""

from __future__ import annotations

import sqlite3

import pytest

from pedibot.ops.daily import daily_text


@pytest.fixture
def con() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.execute(
        "CREATE TABLE answers (id INTEGER PRIMARY KEY, ts TEXT, lang TEXT, level TEXT,"
        " verification TEXT, feedback INTEGER, question TEXT, session TEXT,"
        " source TEXT NOT NULL DEFAULT 'web')"
    )
    return c


def add(c: sqlite3.Connection, **kw: object) -> None:
    row = {
        "ts": "2026-09-04T10:00:00+00:00",
        "lang": "es",
        "level": "routine",
        "verification": "ok",
        "feedback": None,
        "question": "mi hijo tiene fiebre",
        "session": "web-1",
    }
    row.update(kw)
    c.execute(
        "INSERT INTO answers (ts, lang, level, verification, feedback, question, session)"
        " VALUES (:ts, :lang, :level, :verification, :feedback, :question, :session)",
        row,
    )


def test_a_quiet_day_says_nothing(con: sqlite3.Connection) -> None:
    """The whole point. A daily 'nothing happened' is how a report stops being read."""
    assert daily_text(con, "2026-09-04") is None


def test_it_lists_what_was_asked(con: sqlite3.Connection) -> None:
    add(con, question="mi hijo de 4 años tiene fiebre")
    add(con, question="tose por la noche", lang="fr")
    text = daily_text(con, "2026-09-04")
    assert text and "2 consultas" in text
    assert "mi hijo de 4 años tiene fiebre" in text and "tose por la noche" in text
    assert "español" in text and "francés" in text


def test_the_ones_that_need_eyes_come_first(con: sqlite3.Connection) -> None:
    add(con, question="una normal")
    add(con, question="esta no sirvió", feedback=-1)
    add(con, question="sin fuente", verification="no_source")
    add(con, question="una alarma", level="urgent")
    text = daily_text(con, "2026-09-04")
    assert text
    order = [text.index(q) for q in ("esta no sirvió", "sin fuente", "una alarma", "una normal")]
    assert order == sorted(order), "lo que hay que mirar primero no va primero"
    assert "👎" in text and "❓" in text and "🚨" in text


def test_an_answer_is_only_listed_once(con: sqlite3.Connection) -> None:
    """A thumbs-down on an emergency with no source is one answer, not three lines."""
    add(con, question="la misma", feedback=-1, verification="no_source", level="urgent")
    text = daily_text(con, "2026-09-04")
    assert text and text.count("la misma") == 1


def test_what_the_operator_marked_is_called_out(con: sqlite3.Connection) -> None:
    add(con, question="marcada por mí")
    text = daily_text(con, "2026-09-04", flagged={1})
    assert text and "🚩" in text


def test_it_defaults_to_yesterday(con: sqlite3.Connection) -> None:
    """Run at 08:30, "today" is a few hours old and mostly empty; the day to review is the one
    that finished."""
    import datetime as dt

    add(con, ts=(dt.date.today() - dt.timedelta(days=1)).isoformat() + "T09:00:00+00:00")
    assert daily_text(con) is not None
