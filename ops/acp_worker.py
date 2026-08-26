"""ACP provider worker: answers paid jobs from other agents with the PediBot engine.

Design notes (26-ago-2026):
- The signer key lives in the `acp` CLI keystore on this server (P256, added with
  `acp agent add-signer --policy restricted`), so we drive ACP through the **CLI**, not the
  Python SDK (the SDK expects a raw EVM private key, which we deliberately do not have).
- Polling instead of `acp events listen`: one process, no socket to babysit, and `acp job list`
  is REST. Every POLL_SECONDS we list active jobs and act on the ones that need us.
- NEVER pass `--all` (or `--legacy`) to `acp job list`: legacy jobs are read on-chain, the
  `restricted` signer policy denies that RPC call, and the CLI then blocks waiting for a manual
  approval that never comes (verified 26-ago: 3 s with plain `job list`, full timeout with
  `--all`). Our offering is v2, so plain `job list` is the complete picture.
- The answer itself comes from the local API (`/api/agent/ask`), so ACP jobs go through exactly
  the same triage, sources and verifier as the web and Telegram, and are logged the same way.
- Field names in ACP payloads are not stable across versions, so we search the JSON recursively
  for what we need and log the raw shape the first time we see a job.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "data" / "acp_state.json"
POLL_SECONDS = int(os.environ.get("ACP_POLL_SECONDS", "30"))
PRICE_USDC = os.environ.get("ACP_PRICE_USDC", "0.05")
API = os.environ.get("PEDIBOT_API", "http://127.0.0.1:8601")
API_KEY = (os.environ.get("AGENT_API_KEYS", "").split(",") or [""])[0].strip()
DRY_RUN = os.environ.get("ACP_DRY_RUN", "").lower() == "true"
CLI_TIMEOUT = int(os.environ.get("ACP_CLI_TIMEOUT", "60"))


def acp(*args: str) -> dict[str, Any] | list[Any] | None:
    """Run the acp CLI with --json and parse the last JSON line (it also prints human text)."""
    cmd = ["acp", *args, "--json"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT).stdout
    except subprocess.TimeoutExpired:
        logger.warning("acp {} timed out", " ".join(args))
        return None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    if "Manual approval required" in out:
        logger.warning(
            "acp {} needs manual approval (policy). Output: {}", " ".join(args), out[:300]
        )
    return None


def find_first(obj: Any, keys: tuple[str, ...]) -> Any:
    """Depth-first search for the first value under any of `keys`."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in keys and v not in (None, "", [], {}):
                return v
        for v in obj.values():
            got = find_first(v, keys)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = find_first(v, keys)
            if got is not None:
                return got
    return None


def load_state() -> dict[str, dict[str, Any]]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict[str, dict[str, Any]]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=1), encoding="utf-8")


def job_requirement(job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """The buyer's requirement: {question, lang, country}. Looks in the job and, if needed, history."""
    req = find_first(job, ("requirement", "requirements", "servicerequirement"))
    if req is None:
        hist = acp("job", "history", "--job-id", job_id)
        req = (
            find_first(hist, ("requirement", "requirements", "servicerequirement"))
            if hist
            else None
        )
    if isinstance(req, str):
        try:
            req = json.loads(req)
        except json.JSONDecodeError:
            req = {"question": req}
    if not isinstance(req, dict):
        return {}
    return {
        "question": str(req.get("question") or req.get("query") or req.get("prompt") or "").strip(),
        "lang": "es" if str(req.get("lang", "en")).lower().startswith("es") else "en",
        "country": (str(req.get("country") or "GB")[:2] or "GB").upper(),
    }


def answer(req: dict[str, Any]) -> dict[str, Any] | None:
    if not API_KEY:
        logger.error("AGENT_API_KEYS empty: cannot answer ACP jobs")
        return None
    try:
        r = httpx.post(
            f"{API}/api/agent/ask",
            headers={"x-api-key": API_KEY, "content-type": "application/json"},
            json={"question": req["question"], "lang": req["lang"], "country": req["country"]},
            timeout=90,
        )
        r.raise_for_status()
        return dict(r.json())
    except Exception as e:  # noqa: BLE001
        logger.error("engine call failed: {}", e)
        return None


def phase_of(job: dict[str, Any]) -> str:
    return str(find_first(job, ("phase", "status", "state")) or "").upper()


def handle(job: dict[str, Any], state: dict[str, dict[str, Any]]) -> None:
    job_id = str(find_first(job, ("onchainjobid", "jobid", "id")) or "")
    if not job_id:
        return
    st = state.setdefault(job_id, {})
    if "raw_logged" not in st:
        logger.info("ACP job {} seen. Raw: {}", job_id, json.dumps(job)[:800])
        st["raw_logged"] = True
    phase = phase_of(job)

    # 1. new request → propose our fixed price
    if not st.get("budget_set") and any(
        k in phase for k in ("REQUEST", "NEGOTIAT", "PENDING", "CREATED")
    ):
        logger.info("job {} phase={} → set-budget {} USDC", job_id, phase, PRICE_USDC)
        if not DRY_RUN:
            res = acp("provider", "set-budget", "--job-id", job_id, "--amount", PRICE_USDC)
            logger.info("set-budget result: {}", json.dumps(res)[:300] if res else "none")
        st["budget_set"] = time.time()
        return

    # 2. funded / in transaction → answer and deliver
    if (
        st.get("budget_set")
        and not st.get("submitted")
        and any(k in phase for k in ("TRANSACTION", "FUNDED", "PAID", "IN_PROGRESS", "ACCEPTED"))
    ):
        req = job_requirement(job, job_id)
        if not req.get("question"):
            logger.warning("job {}: no question found in requirement; skipping this round", job_id)
            return
        a = answer(req)
        if a is None:
            return
        deliverable = json.dumps(
            {
                "level": a.get("level"),
                "banner": a.get("banner"),
                "answer": a.get("answer"),
                "sources": a.get("sources", []),
                "verification": a.get("verification"),
                "disclaimer": a.get("disclaimer"),
            },
            ensure_ascii=False,
        )
        logger.info("job {} phase={} → submit ({} chars)", job_id, phase, len(deliverable))
        if not DRY_RUN:
            res = acp("provider", "submit", "--job-id", job_id, "--deliverable", deliverable)
            logger.info("submit result: {}", json.dumps(res)[:300] if res else "none")
        st["submitted"] = time.time()
        st["question"] = req["question"][:120]


def main() -> int:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} {level} {message}")
    logger.info(
        "acp worker up (poll={}s, price={} USDC, dry_run={})", POLL_SECONDS, PRICE_USDC, DRY_RUN
    )
    state = load_state()
    while True:
        listed = acp("job", "list")
        jobs = listed.get("jobs", []) if isinstance(listed, dict) else (listed or [])
        if jobs:
            logger.info("{} active job(s)", len(jobs))
        for job in jobs:
            if isinstance(job, dict):
                try:
                    handle(job, state)
                except Exception as e:  # noqa: BLE001
                    logger.exception("job handling failed: {}", e)
        save_state(state)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
