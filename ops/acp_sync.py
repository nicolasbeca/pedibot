"""Make PediBot's ACP listing match ops/acp_catalogue.json (13-sep-2026).

    uv run python ops/acp_sync.py            # prints what it would do
    uv run python ops/acp_sync.py --apply    # does it

Runs on the server, as the service user (the signer lives in its keystore):

    sudo -u pedibot HOME=/opt/pedibot bash -lc 'cd /opt/pedibot && ~/.local/bin/uv run --no-dev python ops/acp_sync.py --apply'

Offerings are matched BY NAME: one that exists is updated (description, price, SLA, both schemas,
visible), one that does not is created, and every offering gets the subscription packages
attached. Resources can only be CREATED from the CLI — `acp resource update` and `delete` take no
options in the versions tried (1.0.34) — so a resource that is no longer in the catalogue is only
REPORTED, with its name, for the operator to hide from the Virtuals panel.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "ops" / "acp_catalogue.json"


@dataclass
class Plan:
    update: list[tuple[str, dict[str, Any]]] = field(default_factory=list)  # (id, offering)
    create: list[dict[str, Any]] = field(default_factory=list)
    create_resources: list[dict[str, Any]] = field(default_factory=list)
    stale_resources: list[str] = field(default_factory=list)


def plan(
    catalogue: dict[str, Any], offerings: list[dict[str, Any]], resources: list[dict[str, Any]]
) -> Plan:
    """What has to change, without touching anything."""
    p = Plan()
    live = {str(o.get("name")): str(o.get("id")) for o in offerings}
    for o in catalogue["offerings"]:
        if o["name"] in live:
            p.update.append((live[o["name"]], o))
        else:
            p.create.append(o)
    have = {str(r.get("name")) for r in resources}
    want = {r["name"] for r in catalogue["resources"]}
    p.create_resources = [r for r in catalogue["resources"] if r["name"] not in have]
    p.stale_resources = sorted(have - want)
    return p


def offering_args(o: dict[str, Any]) -> list[str]:
    return [
        "--name",
        o["name"],
        "--description",
        o["description"],
        "--price-type",
        "fixed",
        "--price-value",
        f"{o['price']:g}",
        "--sla-minutes",
        str(o["sla_minutes"]),
        "--requirements",
        json.dumps(o["requirements"], ensure_ascii=False),
        "--deliverable",
        json.dumps(o["deliverable"], ensure_ascii=False),
        "--no-required-funds",
        "--no-hidden",
    ]


def acp(*args: str) -> Any:
    out = subprocess.run(["acp", *args, "--json"], capture_output=True, text=True, timeout=120)
    for line in reversed(out.stdout.splitlines()):
        if line.strip()[:1] in "[{":
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    raise RuntimeError(f"acp {' '.join(args[:2])} failed: {out.stderr[-400:] or out.stdout[-400:]}")


def _list(kind: str) -> list[dict[str, Any]]:
    got = acp(kind, "list")
    if isinstance(got, dict):
        got = got.get("data") or []
    return got if isinstance(got, list) else []


def main() -> int:
    apply = "--apply" in sys.argv
    catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    p = plan(catalogue, _list("offering"), _list("resource"))
    print(f"offerings: update {len(p.update)}, create {len(p.create)}")
    print(
        f"resources: create {len(p.create_resources)}; not in the catalogue (hide in the panel): {p.stale_resources}"
    )
    if not apply:
        for oid, o in p.update:
            print(f"  would update {o['name']} ({oid})")
        for o in p.create:
            print(f"  would create {o['name']}")
        for r in p.create_resources:
            print(f"  would create resource {r['name']} → {r['url']}")
        return 0
    for oid, o in p.update:
        acp("offering", "update", "--offering-id", oid, *offering_args(o))
        print(f"  updated {o['name']}")
    for o in p.create:
        acp("offering", "create", *offering_args(o))
        print(f"  created {o['name']}")
    for r in p.create_resources:
        acp(
            "resource",
            "create",
            "--name",
            r["name"],
            "--description",
            r["description"],
            "--url",
            r["url"],
            "--params",
            json.dumps(r["params"], ensure_ascii=False),
            "--no-hidden",
        )
        print(f"  created resource {r['name']}")
    subs = ",".join(str(s["id"]) for s in _list("subscription"))
    if subs:
        for o in _list("offering"):
            acp("offering", "update", "--offering-id", str(o["id"]), "--subscription-ids", subs)
        print(f"  subscriptions attached to every offering: {subs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
