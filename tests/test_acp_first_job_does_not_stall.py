"""The first paid ACP job must go all the way through (13-sep-2026).

PediBot has been listed since August and has never served a job, so nothing had ever exercised
the worker against the shapes ACP v2 really uses. Reading the CLI (1.0.34) and its SDK
(acp-node-v2) turned up three places where the first real job would have stalled silently:

1. `acp job list` gives the state as `jobStatus`, with v2 values (`open`, `budget_set`,
   `funded`, `submitted`, `completed`). The worker looked for `phase`/`status`/`state` and for
   v1 words (REQUEST, TRANSACTION): it would have read no state at all and done nothing.
2. `acp job history` REQUIRES `--chain-id`. The worker never passed it.
3. In v2 the buyer's form is a MESSAGE, `{"kind": "message", "contentType": "requirement",
   "content": "<json>"}`, sent right after the job is created. The worker searched for a key
   called `requirement` and would have found none, so every job would have been left as "the
   form does not match any offering".

The shapes below are copied from what the CLI prints (`outputResult` in dist/bin/acp.js and
`OffChainJob` in acp-node-v2/dist/events/types.d.ts), not guessed.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location("acp_worker", ROOT / "ops" / "acp_worker.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    sys.modules["acp_worker"] = m
    spec.loader.exec_module(m)
    return m


PRICES = {"child_medicine_dose": "0.02", "paediatric_question_with_sources": "0.01"}


def _job(status: str, job_id: str = "812", offering: str = "child_medicine_dose") -> dict[str, Any]:
    """One entry of `acp job list --json` → {"jobs": [...]}, v2."""
    return {
        "chainId": 8453,
        "onChainJobId": job_id,
        "jobStatus": status,
        "clientAddress": "0xbuyer",
        "providerAddress": "0xpedibot",
        "evaluatorAddress": "0x0000000000000000000000000000000000000000",
        "description": offering,
        "budget": None,
        "expiredAt": "2026-09-13T20:00:00.000Z",
        "hookAddress": None,
        "deliverable": None,
        "hookConfigs": None,
        "clientSubscription": None,
        "legacy": False,
    }


def _history(job_id: str, form: dict[str, Any], status: str = "funded") -> dict[str, Any]:
    """`acp job history --job-id X --chain-id Y --json`, v2."""
    return {
        "jobId": job_id,
        "chainId": 8453,
        "protocol": "v2",
        "status": status,
        "entryCount": 3,
        "entries": [
            {"kind": "system", "event": {"type": "job.created", "provider": "0xpedibot"}},
            {
                "kind": "message",
                "from": "0xbuyer",
                "contentType": "requirement",
                "content": json.dumps(form),
            },
            {"kind": "system", "event": {"type": "job.funded"}},
        ],
    }


class FakeAcp:
    def __init__(self, history: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.history = history

    def __call__(self, *args: str) -> Any:
        self.calls.append(args)
        if args[:2] == ("job", "history"):
            if "--chain-id" not in args:  # the real CLI: requiredOption
                return None
            return self.history
        if args[:2] == ("provider", "set-budget"):
            return {"success": True}
        if args[:2] == ("provider", "submit"):
            return {"success": True}
        return None

    def named(self, *head: str) -> list[tuple[str, ...]]:
        return [c for c in self.calls if c[: len(head)] == head]


def _opt(call: tuple[str, ...], name: str) -> str:
    return call[call.index(name) + 1]


def test_an_open_v2_job_gets_the_price_of_its_own_offering(monkeypatch):
    m = _mod()
    fake = FakeAcp()
    monkeypatch.setattr(m, "acp", fake)
    state: dict[str, Any] = {}
    m.handle(_job("open"), state, PRICES)
    budgets = fake.named("provider", "set-budget")
    assert len(budgets) == 1, fake.calls
    assert _opt(budgets[0], "--job-id") == "812"
    assert _opt(budgets[0], "--chain-id") == "8453"
    # the job's description is the offering name: 0.02, not the cheapest 0.01
    assert _opt(budgets[0], "--amount") == "0.02"


def test_a_funded_v2_job_reads_the_form_from_the_requirement_message(monkeypatch):
    m = _mod()
    fake = FakeAcp(_history("812", {"drug": "ibuprofen", "weight_kg": 12, "lang": "es"}))
    monkeypatch.setattr(m, "acp", fake)
    served: list[Any] = []
    monkeypatch.setattr(m, "serve", lambda r: served.append(r) or {"dose": "6 ml"})
    state: dict[str, Any] = {"812": {"budget_set": 1.0, "raw_logged": True}}
    m.handle(_job("funded"), state, PRICES)

    hist = fake.named("job", "history")
    assert hist and _opt(hist[0], "--chain-id") == "8453"
    assert served and served[0].path == "/api/dose", served
    subs = fake.named("provider", "submit")
    assert len(subs) == 1, fake.calls
    assert _opt(subs[0], "--chain-id") == "8453"
    assert json.loads(_opt(subs[0], "--deliverable"))["dose"] == "6 ml"


def test_a_funded_job_is_delivered_even_if_this_worker_did_not_set_its_budget(monkeypatch):
    """The state file can be lost with a redeploy, and a subscription job arrives already paid.
    What the market says the job IS decides; our notes only prevent doing it twice."""
    m = _mod()
    fake = FakeAcp(_history("900", {"question": "fiebre de 39 en un niño de 2 años"}))
    monkeypatch.setattr(m, "acp", fake)
    monkeypatch.setattr(m, "serve", lambda r: {"answer": "ok"})
    m.handle(_job("funded", "900", "paediatric_question_with_sources"), {}, PRICES)
    assert len(fake.named("provider", "submit")) == 1, fake.calls


def test_nothing_is_done_twice(monkeypatch):
    m = _mod()
    fake = FakeAcp(_history("812", {"drug": "paracetamol", "weight_kg": 10}))
    monkeypatch.setattr(m, "acp", fake)
    monkeypatch.setattr(m, "serve", lambda r: {"dose": "x"})
    state: dict[str, Any] = {}
    for _ in range(3):
        m.handle(_job("open"), state, PRICES)
    for _ in range(3):
        m.handle(_job("funded"), state, PRICES)
    assert len(fake.named("provider", "set-budget")) == 1
    assert len(fake.named("provider", "submit")) == 1


def test_waiting_states_are_left_alone(monkeypatch):
    m = _mod()
    for status in ("budget_set", "submitted", "completed", "rejected", "expired"):
        fake = FakeAcp(_history("812", {"drug": "ibuprofen", "weight_kg": 12}))
        monkeypatch.setattr(m, "acp", fake)
        monkeypatch.setattr(m, "serve", lambda r: {"dose": "x"})
        m.handle(_job(status), {"812": {"budget_set": 1.0}}, PRICES)
        acted = fake.named("provider")
        assert not acted, (status, acted)


def test_a_failed_budget_call_is_retried_on_the_next_poll(monkeypatch):
    """A CLI timeout returns nothing. Marking the budget as set anyway would leave the job
    waiting for a price that was never proposed until it expires."""
    m = _mod()
    calls: list[tuple[str, ...]] = []

    def flaky(*args: str) -> Any:
        calls.append(args)
        return None if len(calls) == 1 else {"success": True}

    monkeypatch.setattr(m, "acp", flaky)
    state: dict[str, Any] = {}
    m.handle(_job("open"), state, PRICES)
    m.handle(_job("open"), state, PRICES)
    assert [c[:2] for c in calls] == [("provider", "set-budget")] * 2
    m.handle(_job("open"), state, PRICES)
    assert len(calls) == 2  # succeeded on the second: not proposed a third time


def test_the_v1_words_still_work(monkeypatch):
    """Legacy jobs are mapped to v2 words by the CLI, but a raw v1 phase must not break."""
    m = _mod()
    assert m.status_of({"phase": "REQUEST"}) == "open"
    assert m.status_of({"phase": "TRANSACTION"}) == "funded"
    assert m.status_of({"jobStatus": "budget_set"}) == "budget_set"
    assert m.status_of({}) == ""


def test_a_cli_error_is_not_a_result(monkeypatch):
    """With --json the CLI prints its errors on STDOUT as {"error": ...} and exits with 1
    (outputError in dist/bin/acp.js). Parsing the last JSON line took that for an answer, so a
    failed `provider submit` would have been recorded as delivered: the buyer pays and gets
    nothing, and we believe we served them. Regime's worker learnt this on 11-sep."""
    import subprocess as sp

    m = _mod()

    class Failed:
        returncode = 1
        stdout = '{"error": "No session found for job 812.", "code": "SESSION_NOT_FOUND"}\n'
        stderr = ""

    monkeypatch.setattr(sp, "run", lambda *a, **k: Failed())
    assert m.acp("provider", "submit", "--job-id", "812") is None

    class Ok:
        returncode = 0
        stdout = '{"success": true, "action": "submit"}\n'
        stderr = ""

    monkeypatch.setattr(sp, "run", lambda *a, **k: Ok())
    assert m.acp("provider", "submit", "--job-id", "812") == {"success": True, "action": "submit"}
