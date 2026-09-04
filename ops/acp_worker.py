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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "data" / "acp_state.json"
POLL_SECONDS = int(os.environ.get("ACP_POLL_SECONDS", "30"))
PRICE_USDC = os.environ.get("ACP_PRICE_USDC", "0.01")  # only if the market does not answer
API = os.environ.get("PEDIBOT_API", "http://127.0.0.1:8601")
API_KEY = (os.environ.get("AGENT_API_KEYS", "").split(",") or [""])[0].strip()
DRY_RUN = os.environ.get("ACP_DRY_RUN", "").lower() == "true"
PRICE_REFRESH_EVERY = 60  # polls between price re-reads (30 s x 60 = 30 min)
DISCLAIMER = (
    "Information from published paediatric guidelines. Not medical advice, not a diagnosis."
)
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


# ── prices ───────────────────────────────────────────────────────────────────
# The budget we propose must be exactly the price shown on the listing. Keeping it in a
# constant meant that lowering the price in the marketplace left the worker proposing the old
# one. Read it from the market at start-up; when a job does not say which offering it came
# from, charge the CHEAPEST: better to undercharge than to charge above the listing.

OFFER_KEYS = ("offeringid", "offering_id", "serviceid", "service_id", "offering", "service")
NAME_KEYS = ("offeringname", "servicename", "offering_name", "service_name", "name")


def prices_from(offerings: list[dict[str, Any]]) -> dict[str, str]:
    table: dict[str, str] = {}
    for o in offerings or []:
        price = o.get("priceValue")
        if price is None:
            continue
        text = f"{float(price):g}"
        for key in (o.get("id"), o.get("name")):
            if key:
                table[str(key)] = text
    return table


def price_for(job: dict[str, Any], table: dict[str, str], *, fallback: str) -> str:
    if not table:
        return fallback
    for keys in (OFFER_KEYS, NAME_KEYS):
        value = find_first(job, keys)
        if isinstance(value, dict):
            value = value.get("id") or value.get("name")
        if value is not None and str(value) in table:
            return table[str(value)]
    return min(table.values(), key=float)


def fetch_prices() -> dict[str, str]:
    listed = acp("offering", "list")
    if isinstance(listed, dict):
        listed = listed.get("data") or []
    return prices_from(listed if isinstance(listed, list) else [])


# ── routing ──────────────────────────────────────────────────────────────────
# Each offering has its own form. Doses and vaccination schedules are answered from fixed
# tables through the same endpoints the website uses — the model is not involved in a number.


@dataclass(frozen=True)
class Route:
    path: str
    method: str
    payload: dict[str, Any]


def _num(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


# Kept in step with pedibot.bot.answer.SUPPORTED_LANGS by tests/test_acp_worker.py; the worker
# runs as a plain script on the server and does not import the package.
SUPPORTED_LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


def route(req: dict[str, Any]) -> Route | None:
    """Which endpoint answers this form. None if the form cannot be served."""
    req = {k.lower(): v for k, v in (req or {}).items()}
    question = str(req.get("question") or req.get("query") or req.get("prompt") or "").strip()
    country = str(req.get("country") or "").strip().upper()
    weight = _num(req.get("weight_kg") or req.get("weight"))
    drug = str(req.get("drug") or req.get("medicine") or req.get("brand") or "").strip()
    # every language the engine speaks, not "Spanish or English": a French buyer asking in
    # French used to be answered in English
    asked = str(req.get("lang") or "en").lower()[:2]
    lang = asked if asked in SUPPORTED_LANGS else "en"
    age = _num(req.get("age_months"))

    if question:
        return Route(
            "/api/agent/ask",
            "POST",
            {"question": question, "lang": lang, "country": country[:2] or "GB"},
        )
    if drug and weight is not None:
        payload: dict[str, Any] = {"drug": drug, "weight_kg": weight, "lang": lang}
        if age is not None:
            payload["age_months"] = age
        return Route("/api/dose", "POST", payload)
    if country:
        return Route(f"/api/vaccines?country={country[:2]}&lang={lang}", "GET", {})
    if weight is not None:
        tail = f"&age_months={int(age)}" if age is not None else ""
        return Route(f"/api/ors?weight_kg={weight}{tail}&lang={lang}", "GET", {})
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
    """The buyer's form, as it comes. Looks in the job and, if needed, in its history.

    It is NOT normalised here: each offering has its own form (a question, a weight and a
    medicine, a country) and `route` is what decides which endpoint serves it."""
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
    return req if isinstance(req, dict) else {}


def serve(r: Route) -> dict[str, Any] | None:
    """Call the endpoint that answers this job. The reply IS the deliverable."""
    if r.path == "/api/agent/ask" and not API_KEY:
        logger.error("AGENT_API_KEYS empty: cannot answer ACP jobs")
        return None
    headers = {"content-type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    try:
        if r.method == "GET":
            resp = httpx.get(f"{API}{r.path}", headers=headers, timeout=90)
        else:
            resp = httpx.post(f"{API}{r.path}", headers=headers, json=r.payload, timeout=90)
        resp.raise_for_status()
        return dict(resp.json())
    except Exception as e:  # noqa: BLE001
        logger.error("call to {} failed: {}", r.path, e)
        return None


def phase_of(job: dict[str, Any]) -> str:
    return str(find_first(job, ("phase", "status", "state")) or "").upper()


def handle(
    job: dict[str, Any], state: dict[str, dict[str, Any]], prices: dict[str, str] | None = None
) -> None:
    job_id = str(find_first(job, ("onchainjobid", "jobid", "id")) or "")
    if not job_id:
        return
    st = state.setdefault(job_id, {})
    if "raw_logged" not in st:
        logger.info("ACP job {} seen. Raw: {}", job_id, json.dumps(job)[:800])
        st["raw_logged"] = True
    phase = phase_of(job)

    # 1. new request → propose the price its own offering advertises
    if not st.get("budget_set") and any(
        k in phase for k in ("REQUEST", "NEGOTIAT", "PENDING", "CREATED")
    ):
        price = price_for(job, prices or {}, fallback=PRICE_USDC)
        logger.info("job {} phase={} → set-budget {} USDC", job_id, phase, price)
        if not DRY_RUN:
            res = acp("provider", "set-budget", "--job-id", job_id, "--amount", price)
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
        r = route(req)
        if r is None:
            logger.warning("job {}: the form does not match any offering; leaving it", job_id)
            return
        a = serve(r)
        if a is None:
            return
        a.setdefault("disclaimer", DISCLAIMER)
        deliverable = json.dumps(a, ensure_ascii=False)
        logger.info("job {} phase={} → submit ({} chars)", job_id, phase, len(deliverable))
        if not DRY_RUN:
            res = acp("provider", "submit", "--job-id", job_id, "--deliverable", deliverable)
            logger.info("submit result: {}", json.dumps(res)[:300] if res else "none")
        st["submitted"] = time.time()
        st["served"] = r.path


def main() -> int:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} {level} {message}")
    prices = fetch_prices()
    tariff = ", ".join(sorted(set(prices.values()), key=float)) or f"{PRICE_USDC} (fallback)"
    logger.info(
        "acp worker up (poll={}s, listed prices: {} USDC, dry_run={})",
        POLL_SECONDS,
        tariff,
        DRY_RUN,
    )
    state = load_state()
    rounds = 0
    while True:
        listed = acp("job", "list")
        jobs = listed.get("jobs", []) if isinstance(listed, dict) else (listed or [])
        if jobs:
            logger.info("{} active job(s)", len(jobs))
        for job in jobs:
            if isinstance(job, dict):
                try:
                    handle(job, state, prices)
                except Exception as e:  # noqa: BLE001
                    logger.exception("job handling failed: {}", e)
        save_state(state)
        rounds += 1
        if rounds % PRICE_REFRESH_EVERY == 0:  # a price can change without a restart
            fresh = fetch_prices()
            if fresh and fresh != prices:
                logger.info("prices updated: {}", sorted(set(fresh.values()), key=float))
                prices = fresh
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
