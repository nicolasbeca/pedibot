"""One quiet line about who pays for this, and the answers it must never appear on (5-sep-2026).

The operator asked whether we could watch IP addresses to spot heavy users and invite them to the
support page. The second half needs no IPs: the session token lives in the reader's own
localStorage and survives across days, so counting a session's questions is a query we already
can run — and /legal promises, in eight languages, that answers are stored "with a random session
identifier, no IP address".

The rule that is not about tact:

    NEVER over an answer with a warning sign.

A parent whose child has just had a seizure, swallowed a battery or stopped breathing is not
asked for money. Everything else here — once a day, on the fifth, a line and not a box — is about
not being tiresome. That one is about not being contemptible.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.api import INVITE_AFTER, _should_invite


class FakeOps:
    def __init__(self, n: int) -> None:
        self.n = n

    def answers_today(self, session: str) -> int:
        return self.n


class FakeAnswer:
    def __init__(self, level: str = "routine", verification: str = "ok") -> None:
        self.level = level
        self.verification = verification


@pytest.mark.parametrize("level", ["urgent", "emergency", "mental_health"])
def test_never_over_an_alarm(level: str) -> None:
    """The one rule here that is not about tact."""
    assert not _should_invite(FakeAnswer(level=level), FakeOps(INVITE_AFTER), "s")


def test_shown_once_on_the_fifth_calm_question() -> None:
    for n in range(1, INVITE_AFTER):
        assert not _should_invite(FakeAnswer(), FakeOps(n), "s"), f"aparece a la {n}"
    assert _should_invite(FakeAnswer(), FakeOps(INVITE_AFTER), "s")


def test_not_again_afterwards() -> None:
    """No counter to store and no way for it to become a nag: it is the fifth or nothing."""
    for n in (INVITE_AFTER + 1, INVITE_AFTER + 7, 40):
        assert not _should_invite(FakeAnswer(), FakeOps(n), "s"), f"vuelve a salir en la {n}"


@pytest.mark.parametrize("verification", ["asked_age", "clarify", "no_source", "fallback"])
def test_not_when_the_answer_did_not_answer(verification: str) -> None:
    """Asking for support under "I don't have reliable information on this" is asking to be paid
    for the thing that just failed."""
    assert not _should_invite(FakeAnswer(verification=verification), FakeOps(INVITE_AFTER), "s")


@pytest.mark.parametrize(
    "verification", ["ok", "regenerated", "dose_calculator", "vaccine_schedule"]
)
def test_shown_after_an_answer_that_worked(verification: str) -> None:
    assert _should_invite(FakeAnswer(verification=verification), FakeOps(INVITE_AFTER), "s")


def test_a_broken_counter_never_breaks_an_answer() -> None:
    class Exploding:
        def answers_today(self, session: str) -> int:
            raise RuntimeError("db locked")

    assert not _should_invite(FakeAnswer(), Exploding(), "s")


def test_the_promise_it_keeps() -> None:
    """/legal says answers are stored with a random session identifier and no IP address, in
    eight languages. This feature counts by session, and this test is here so that a future
    version reaching for the IP has to change the promise on purpose."""
    root = pathlib.Path(__file__).resolve().parents[1]
    api = (root / "src" / "pedibot" / "api.py").read_text(encoding="utf-8")
    invite = api[api.index("def _should_invite") : api.index("class ToolOut")]
    assert "ip" not in invite.lower().replace("script", ""), (
        "la invitación ha empezado a mirar la IP: eso hay que cambiarlo primero en /legal, "
        "en los ocho idiomas"
    )
