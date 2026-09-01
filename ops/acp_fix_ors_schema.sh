#!/usr/bin/env bash
# The published deliverable for `oral_rehydration_plan` did not match what /api/ors actually
# returns (it returns age_band + plain sentences + warnings + sources, not numeric fields).
# A schema that does not match the delivery is a reason for a buyer to reject the job.
set -euo pipefail
cd /opt/pedibot

ORS_DEL='{"type":"object","properties":{"age_band":{"type":"string","description":"infant or child: the volumes differ under and over one year"},"lines":{"type":"array","items":{"type":"string"},"description":"How much solution per intake and how often, in plain sentences"},"warnings":{"type":"array","items":{"type":"string"},"description":"When to stop and see a doctor or go to the emergency department"},"sources":{"type":"array","items":{"type":"string"}},"disclaimer":{"type":"string"}}}'

ID=$(acp offering list --json | python3 -c "
import json, sys
for o in json.load(sys.stdin):
    if o['name'] == 'oral_rehydration_plan':
        print(o['id'])
        break
")
[ -n "$ID" ] || { echo "offering not found"; exit 1; }
acp offering update --offering-id "$ID" --deliverable "$ORS_DEL" --json >/dev/null
echo "deliverable fixed for $ID"
