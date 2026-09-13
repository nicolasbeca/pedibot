"""ACP provider worker: answers paid jobs from other agents with the PediBot engine.

Design notes (26-ago-2026):
- The signer key lives in the `acp` CLI keystore on this server (P256, added with
  `acp agent add-signer --policy restricted`), so we drive ACP through the **CLI**, not the
  Python SDK (the SDK expects a raw EVM private key, which we deliberately do not have).
- Polling `acp job list` (REST) is how we learn about jobs: every POLL_SECONDS we list active
  jobs and act on the ones that need us. BUT since 13-sep-2026 `acp events listen` also runs, as
  a child process, only to keep the agent online: without that socket and its heartbeat the
  marketplace never listed PediBot and it got zero jobs in eighteen days (see "presence").
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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

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
    # ACP v2: the job's `description` IS the offering name (createJobFromOffering)
    if str(job.get("description") or "") in table:
        return table[str(job["description"])]
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

    sex = str(req.get("sex") or "").strip().lower()[:1]
    height = _num(req.get("height_cm") or req.get("height") or req.get("length_cm"))
    symptoms = str(req.get("symptoms") or req.get("text") or req.get("description") or "").strip()
    topic = str(req.get("topic") or req.get("subject") or "").strip()
    mode = "child" if str(req.get("mode") or "").lower() == "child" else "parent"

    if question:
        return Route(
            "/api/agent/ask",
            "POST",
            {"question": question, "lang": lang, "country": country[:2] or "GB", "mode": mode},
        )
    # la comprobación de signos de alarma: reglas fijas, sin modelo (13-sep-2026)
    if symptoms:
        q = urlencode(
            {"text": symptoms[:1500], "lang": lang, **({"country": country[:2]} if country else {})}
        )
        return Route(f"/api/triage?{q}", "GET", {})
    # la curva de crecimiento: con sexo y edad, y peso o talla. Sin sexo, un peso solo sigue
    # siendo el suero oral de siempre (13-sep-2026)
    if sex in ("m", "f") and age is not None and (weight is not None or height is not None):
        params: dict[str, Any] = {"sex": sex, "age_months": age, "lang": lang}
        if weight is not None:
            params["weight_kg"] = weight
        if height is not None:
            params["height_cm"] = height
        if country:
            params["country"] = country[:2]
        return Route(f"/api/growth?{urlencode(params)}", "GET", {})
    if topic:
        return Route(f"/api/guides?{urlencode({'q': topic[:200], 'lang': lang})}", "GET", {})
    if drug and weight is not None:
        payload: dict[str, Any] = {"drug": drug, "weight_kg": weight, "lang": lang}
        if age is not None:
            payload["age_months"] = age
        return Route("/api/dose", "POST", payload)
    if country:
        # con edad, las vacunas que tocan a esa edad; sin ella, el calendario entero
        tail = f"&age_months={age:g}" if age is not None else ""
        return Route(f"/api/vaccines?country={country[:2]}{tail}&lang={lang}", "GET", {})
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


def requirement_message(hist: Any) -> Any:
    """ACP v2: the form is the LAST message whose contentType is "requirement", its JSON as text
    in `content` (acp-node-v2 createJobFromOffering). The last one, because a buyer may resend."""
    entries = hist.get("entries") if isinstance(hist, dict) else None
    for e in reversed(entries or []):
        if isinstance(e, dict) and str(e.get("contentType") or "").lower() == "requirement":
            return e.get("content")
    return None


def job_requirement(job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """The buyer's form, as it comes. Looks in the job and, if needed, in its history.

    It is NOT normalised here: each offering has its own form (a question, a weight and a
    medicine, a country) and `route` is what decides which endpoint serves it."""
    req = find_first(job, ("requirement", "requirements", "servicerequirement"))
    if req is None:
        # --chain-id is a required option of `job history`: without it the CLI prints an error
        hist = acp("job", "history", "--job-id", job_id, "--chain-id", chain_of(job))
        req = requirement_message(hist)
        if req is None and hist:
            req = find_first(hist, ("requirement", "requirements", "servicerequirement"))
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


# ── the job's life ───────────────────────────────────────────────────────────
# 13-sep-2026, read from acp-cli 1.0.34 before the first real job: `acp job list` gives the state
# as `jobStatus` with the v2 words below (acp-node-v2 jobSession.js EVENT_TO_STATUS). The first
# version of this worker looked for `phase`/`status` and for v1 words, and against a real v2 job
# it would have done nothing at all. v1 phases are still mapped, the way the CLI maps legacy jobs.

_V1_TO_V2 = {
    "REQUEST": "open",
    "NEGOTIATION": "budget_set",
    "TRANSACTION": "funded",
    "EVALUATION": "submitted",
    "COMPLETED": "completed",
    "REJECTED": "rejected",
    "EXPIRED": "expired",
}


def status_of(job: dict[str, Any]) -> str:
    """The job's state in v2 words: open, budget_set, funded, submitted, completed, rejected…"""
    raw = find_first(job, ("jobstatus", "status", "phase", "state"))
    if raw is None:
        return ""
    text = str(raw).strip()
    return _V1_TO_V2.get(text.upper(), text.lower())


def chain_of(job: dict[str, Any]) -> str:
    return str(find_first(job, ("chainid",)) or "8453")  # Base, the CLI's own default


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
    status = status_of(job)
    chain = chain_of(job)

    # 1. new job → propose the price its own offering advertises. Marked only when the CLI
    # answered: a timeout marked as done would leave the buyer waiting for a price until expiry.
    if status == "open" and not st.get("budget_set"):
        price = price_for(job, prices or {}, fallback=PRICE_USDC)
        logger.info("job {} status={} → set-budget {} USDC", job_id, status, price)
        if DRY_RUN:
            st["budget_set"] = time.time()
            return
        res = acp(
            "provider", "set-budget", "--job-id", job_id, "--amount", price, "--chain-id", chain
        )
        logger.info("set-budget result: {}", json.dumps(res)[:300] if res else "none")
        if res is not None:
            st["budget_set"] = time.time()
        return

    # 2. paid → answer and deliver. What the market says the job is decides, not our notes: the
    # state file can be lost with a redeploy, and a subscription job can arrive already paid.
    if status == "funded" and not st.get("submitted"):
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
        logger.info("job {} status={} → submit ({} chars)", job_id, status, len(deliverable))
        if not DRY_RUN:
            res = acp(
                "provider",
                "submit",
                "--job-id",
                job_id,
                "--deliverable",
                deliverable,
                "--chain-id",
                chain,
            )
            logger.info("submit result: {}", json.dumps(res)[:300] if res else "none")
            if res is None:
                return
        st["submitted"] = time.time()
        st["served"] = r.path


# ── presence ─────────────────────────────────────────────────────────────────
# 13-sep-2026: from the 26th of August to this day the worker saw ZERO jobs, and the marketplace
# search did not list PediBot for "pediatric", "health" or even "PediBot". An agent's presence is
# a socket with a heartbeat (acp-node-v2 socketTransport); polling `acp job list` over REST never
# opens it, so the agent stayed at `lastActiveAt: None` and browse left it out. With
# `acp events listen` connected it went to 2999-12-31, the "online" marker. The listener runs
# beside the poll loop (which stays: REST is still the complete picture of our jobs).

EVENTS_FILE = ROOT / "data" / "acp_events.jsonl"


def listener_command() -> list[str]:
    # never --all / --legacy: legacy events are read on-chain and the restricted policy hangs
    return ["acp", "events", "listen", "--output", str(EVENTS_FILE)]


def start_listener() -> subprocess.Popen[bytes]:
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.info("starting presence listener: {}", " ".join(listener_command()))
    return subprocess.Popen(
        listener_command(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def ensure_listener(proc: Any, start: Callable[[], Any]) -> Any:
    """The listener, alive: started if there is none, restarted if it died."""
    if proc is not None and proc.poll() is None:
        return proc
    if proc is not None:
        logger.warning("presence listener exited ({}); restarting", proc.poll())
    return start()


def main() -> int:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} {level} {message}")
    box: dict[str, Any] = {"listener": None}
    try:
        return _run(box)
    except KeyboardInterrupt:
        # systemd stops the unit with SIGINT (KillSignal=SIGINT): a normal stop, not a failure
        logger.info("acp worker stopping")
        return 0
    finally:
        proc = box["listener"]
        if proc is not None and proc.poll() is None:
            proc.terminate()


def _run(box: dict[str, Any]) -> int:
    box["listener"] = ensure_listener(box["listener"], start_listener)
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
        box["listener"] = ensure_listener(box["listener"], start_listener)
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
