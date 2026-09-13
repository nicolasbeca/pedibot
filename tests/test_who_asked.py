"""Whose questions the panel counts (6-sep-2026).

The operator opened /admin and found 106 questions. Three of them came from outside; the other
103 were test strings sent from the build machine while the eight languages were being made. The
database had no way to tell them apart, so the panel — and the daily review, and the public
/api/stats — reported our own work back as readers.

What these lock down is the direction of the error. A question is counted as a reader's only when
the client that sent it said which client it is; anything that did not say is left out. That will
occasionally hide someone real (a browser holding an old copy of the page), and it is still the
right way round: a number the operator uses to decide whether the site is working must never be
larger than the truth.
"""

from __future__ import annotations

import sqlite3

import pytest

from pedibot.ops.store import NOT_REAL, REAL_ONLY, AnswerRecord, OpsStore


def _rec(**kw: object) -> AnswerRecord:
    base: dict[str, object] = {
        "session": "s1",
        "lang": "es",
        "country": None,
        "question": "mi hijo tiene fiebre",
        "answer": "texto",
        "level": "routine",
        "verification": "ok",
        "chunk_ids": [],
        "prompt_version": None,
        "model": None,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.01,
        "latency_ms": 10,
        "source": "web",
    }
    base.update(kw)
    return AnswerRecord(**base)  # type: ignore[arg-type]


def test_the_record_has_no_default_source() -> None:
    """A new way of asking must say what it is. With a default, the next endpoint someone adds
    would quietly log itself as a reader — which is how the first 106 rows happened."""
    with pytest.raises(TypeError):
        AnswerRecord(  # type: ignore[call-arg]
            session="s",
            lang="es",
            country=None,
            question="q",
            answer="a",
            level="routine",
            verification="ok",
            chunk_ids=[],
            prompt_version=None,
            model=None,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            latency_ms=0,
        )


def test_the_two_filters_are_complements() -> None:
    """Every row is either counted as a reader or counted as ours. A source that fell through
    both would be invisible in every view at once.

    Checked on rows, not on the text of the two clauses: since 13-sep-2026 they also carry the
    ids declared in config/team.yaml, and a textual `IN` → `NOT IN` no longer describes them."""
    import sqlite3

    from pedibot.ops.store import _OURS

    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE answers (id INTEGER, source TEXT)")
    ids = [1, 2, *sorted(_OURS)]
    fuentes = ["web", "telegram", "agent", "test", "unknown"]
    con.executemany("INSERT INTO answers VALUES (?,?)", [(i, s) for i in ids for s in fuentes])
    total = con.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
    lectores = con.execute("SELECT COUNT(*) FROM answers WHERE 1=1" + REAL_ONLY).fetchone()[0]
    nuestras = con.execute("SELECT COUNT(*) FROM answers WHERE 1=1" + NOT_REAL).fetchone()[0]
    ambas = con.execute("SELECT COUNT(*) FROM answers WHERE 1=1" + REAL_ONLY + NOT_REAL).fetchone()[
        0
    ]
    assert lectores + nuestras == total and ambas == 0


@pytest.mark.parametrize(
    ("source", "counts"),
    [("web", True), ("telegram", True), ("agent", True), ("test", False), ("unknown", False)],
)
def test_only_a_named_client_counts_as_a_reader(tmp_path, source: str, counts: bool) -> None:
    ops = OpsStore(tmp_path / "ops.db")
    ops.log_answer(_rec(source=source))
    assert bool(ops.stats()["answers"]) is counts


def test_money_counts_every_question(tmp_path) -> None:
    """The one number that must never be filtered: a test question is charged like a real one,
    and a spend figure that hides half of what was spent is worse than no figure."""
    from pedibot.ops import report

    ops = OpsStore(tmp_path / "ops.db")
    ops.log_answer(_rec(source="test", cost_usd=0.02))
    assert float(ops.stats()["cost_usd"]) == pytest.approx(0.02)  # type: ignore[arg-type]
    assert report.questions(ops.con, days=7)["cost"] == pytest.approx(0.02)
    assert ops.cost_today_usd() == pytest.approx(0.02)


def test_the_panel_hides_ours_but_says_how_many(tmp_path) -> None:
    from pedibot.ops import report

    ops = OpsStore(tmp_path / "ops.db")
    ops.log_answer(_rec(source="web", question="una madre pregunta"))
    for _ in range(4):
        ops.log_answer(_rec(source="test", question="cadena de prueba"))

    q = report.questions(ops.con, days=7)
    assert q["total"] == 1 and q["test"] == 4
    rows = report.recent_answers(ops.con, 50)
    assert [r["question"] for r in rows] == ["una madre pregunta"]

    both = report.questions(ops.con, days=7, include_test=True)
    assert both["total"] == 5
    shown = report.recent_answers(ops.con, 50, include_test=True)
    assert len(shown) == 5
    # and when they are shown, the card says which is which
    assert {r["channel"] for r in shown} == {"web", "prueba nuestra"}


def test_the_daily_review_skips_our_own(tmp_path) -> None:
    """It exists to be read at breakfast. A morning spent reading yesterday's test strings is
    the review teaching the operator to ignore it."""
    from pedibot.ops.daily import daily_text

    c = sqlite3.connect(":memory:")
    c.execute(
        "CREATE TABLE answers (id INTEGER PRIMARY KEY, ts TEXT, lang TEXT, level TEXT,"
        " verification TEXT, feedback INTEGER, question TEXT, session TEXT,"
        " source TEXT NOT NULL DEFAULT 'web')"
    )
    for source, question in (("test", "cadena de prueba"), ("web", "una madre pregunta")):
        c.execute(
            "INSERT INTO answers (ts, lang, level, verification, feedback, question, session,"
            " source) VALUES ('2026-09-04T10:00:00+00:00','es','routine','ok',NULL,?,'s',?)",
            (question, source),
        )
    text = daily_text(c, day="2026-09-04")
    assert text is not None
    assert "una madre pregunta" in text
    assert "cadena de prueba" not in text

    # and a day that was only us is a day with nothing to say
    c.execute("DELETE FROM answers WHERE source='web'")
    assert daily_text(c, day="2026-09-04") is None


def _caddy(
    ip: str, uri: str, ua: str = "Mozilla/5.0 (Windows NT 10.0) Chrome/120", status: int = 200
) -> str:
    import json as _json

    return _json.dumps(
        {
            "msg": "handled request",
            "ts": 1788700000.0,
            "status": status,
            "request": {
                "uri": uri,
                "method": "GET",
                "remote_ip": ip,
                "headers": {"User-Agent": [ua]},
            },
        }
    )


def test_the_operator_is_not_one_of_his_own_visitors(monkeypatch) -> None:
    """He opens the site to look at it, from the browser he opens the panel with. At this traffic
    one person checking twice a day is most of the number the panel then shows him.

    Found with no configuration and no address written down: /admin is password-protected, so a
    browser that asked for it is his.
    """
    import subprocess

    from pedibot.ops import report

    log = "\n".join(
        [
            _caddy("10.0.0.1", "/admin?days=7"),  # the operator, identifying himself
            _caddy("10.0.0.1", "/"),
            _caddy("10.0.0.1", "/_astro/app.js"),  # con navegador de verdad, y aun así fuera
            _caddy("10.0.0.1", "/es/guias/fiebre"),
            _caddy("203.0.113.9", "/"),  # somebody else
            _caddy("203.0.113.9", "/_astro/app.js"),
            _caddy("203.0.113.9", "/es/guias/fiebre"),
            _caddy("198.51.100.4", "/", ua="curl/8.5.0"),  # our scripts, already excluded
            # a scanner hunting for an admin panel: Caddy answers 401, so it is NOT the operator
            _caddy("192.0.2.7", "/admin", status=401),
            _caddy("192.0.2.7", "/"),
            _caddy("192.0.2.7", "/favicon.ico"),
        ]
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: type("R", (), {"stdout": log})())
    w = report.web_visits(7)
    # the reader, and the scanner that failed the password: two, not one. Guessing the scanner
    # away would shrink the number in the flattering direction, which is the failure this whole
    # change exists to stop.
    # los tres cargaron la página entera, así que el 2 sólo sale si el operador queda fuera
    assert w["visitors"] == 2
    assert w["views"] == 3
    assert w["returning"] == 1, "solo uno de los dos abrió una segunda página"


def test_a_one_page_visit_has_no_duration() -> None:
    """The only clock a site without a tracker has is the gap between two requests. One page
    leaves nothing to measure against — not zero seconds: no measurement. Thirty days of this
    site is 1.942 such visits out of 2.222, and reporting an average over them would be making
    it up."""
    from pedibot.ops.report import _dwell

    d = _dwell({"solo": [100.0], "otro": [500.0]})
    assert d["visits"] == 2 and d["timed"] == 0
    assert d["median_seconds"] is None


def test_a_visit_ends_after_half_an_hour_and_the_middle_one_is_reported() -> None:
    """The median, not the average: one machine coming back after ten hours pulls the average of
    the real numbers to nineteen minutes while the middle visit is nineteen seconds."""
    from pedibot.ops.report import _dwell

    d = _dwell(
        {
            "a": [0.0, 10.0],  # 10 s
            "b": [0.0, 30.0],  # 30 s
            "c": [0.0, 36000.0],  # ten hours apart: two visits of one page, not one of ten hours
            "d": [0.0, 20.0, 100.0],  # 100 s
        }
    )
    assert d["visits"] == 5, "la vuelta de 'c' diez horas despues es otra visita"
    assert d["timed"] == 3 and d["median_seconds"] == 30
    assert d["over_a_minute"] == 1


def test_the_ip_salt_is_not_a_constant_in_the_repository(tmp_path) -> None:
    """/legal promete «tu IP solo se usa como hash con sal». Había sal —la constante «pedibot»,
    escrita en un repositorio público— porque el parámetro no se pasaba desde ninguno de los tres
    sitios que construyen el almacén. Con una sal conocida, revertir una IPv4 desde su hash son
    cuatro mil millones de sha256, o sea nada.

    Se genera por despliegue y se guarda junto a la base, fuera de git."""
    from pedibot.ops.store import OpsStore, deployment_salt

    a = OpsStore(tmp_path / "a" / "ops.db")
    assert a.salt != "pedibot", "la sal sigue siendo la constante del repositorio"
    assert len(a.salt) >= 16, f"la sal es demasiado corta: {len(a.salt)}"

    # estable dentro de un mismo despliegue: si cambiara en cada arranque, el límite de peticiones
    # se reiniciaría con cada reinicio del servicio
    assert deployment_salt(tmp_path / "a" / "ops.db") == a.salt

    # y distinta en otro
    b = OpsStore(tmp_path / "b" / "ops.db")
    assert b.salt != a.salt, "dos despliegues comparten sal"


def test_the_conversation_really_is_gone_after_24_hours(tmp_path) -> None:
    """/legal dice «la memoria de conversación dura 24 horas». history() solo LEÍA las últimas 24,
    pero las filas se quedaban para siempre. Quien lee esa frase entiende que ya no están."""
    import datetime as dt

    ops = OpsStore(tmp_path / "ops.db")
    viejo = (dt.datetime.now(dt.UTC) - dt.timedelta(hours=30)).isoformat(timespec="seconds")
    ops.con.execute(
        "INSERT INTO turns (session, ts, role, text) VALUES (?,?,?,?)",
        ("s1", viejo, "user", "una pregunta de hace treinta horas"),
    )
    ops.con.commit()
    assert ops.con.execute("SELECT COUNT(*) FROM turns").fetchone()[0] == 1

    ops.add_turn("s2", "user", "una de ahora")  # cualquier turno nuevo limpia lo vencido
    quedan = [r[0] for r in ops.con.execute("SELECT text FROM turns")]
    assert quedan == ["una de ahora"], f"la conversación vieja sigue guardada: {quedan}"
