#!/usr/bin/env bash
# Complete JSON schemas for PediBot's ACP jobs (1-sep-2026).
#
# The marketplace flags a schema with a yellow warning when it is missing descriptions: both the
# top-level `description` of the object and one on every single property. A buyer agent reads
# exactly this to decide whether it can use the job, so an undescribed field is a field nobody
# will fill in. Safe to re-run: it only updates.
set -euo pipefail
cd /opt/pedibot

ASK_REQ='{"type":"object","required":["question"],"description":"One paediatric question from a parent, plus the language and country used to answer it.","properties":{"question":{"type":"string","description":"The question as a parent would ask it, e.g. my 3 year old has a barking cough"},"lang":{"type":"string","enum":["en","es"],"default":"en","description":"Language for the answer. The sources are quoted in either language regardless."},"country":{"type":"string","default":"GB","description":"ISO 3166-1 alpha-2, used to name the right emergency number in the banner"}}}'

ASK_DEL='{"type":"object","description":"The answer, its triage level, the sources behind it and the clause that travels with it.","properties":{"level":{"type":"string","enum":["routine","urgent","emergency","mental_health"],"description":"Triage outcome, decided by rules before the model is called"},"banner":{"type":["string","null"],"description":"Emergency instruction shown first when the triage flags a warning sign; null when nothing was flagged"},"answer":{"type":"string","description":"Short answer; every clinical sentence names the organisation it comes from"},"sources":{"type":"array","items":{"type":"string"},"description":"The passages used, each with organisation, document, section and year"},"verification":{"type":"string","description":"How the answer ended: ok, regenerated, no_source, asked_age, clarify, dose_calculator or vaccine_schedule"},"disclaimer":{"type":"string","description":"Information from published guidelines. Not medical advice, not a diagnosis."}}}'

DOSE_REQ='{"type":"object","required":["drug","weight_kg"],"description":"Which medicine, for a child of what weight and age.","properties":{"drug":{"type":"string","description":"Brand printed on the bottle (Calpol, Tylenol, Apiretal, Dalsy, Nurofen, Advil...) or the generic name"},"weight_kg":{"type":"number","description":"The child weight in kilograms; the dose is calculated from it"},"age_months":{"type":"integer","description":"Age in months, if known: it changes the warnings and can refuse the dose altogether"}}}'

DOSE_DEL='{"type":"object","description":"The dose read from a fixed table, with the millilitres for each presentation sold and the limits that go with it.","properties":{"generic":{"type":"string","description":"The active substance the brand resolves to"},"brand":{"type":["string","null"],"description":"The brand recognised from the request; null when a generic name was given"},"mg_min":{"type":"number","description":"Lower end of the dose in milligrams for this weight"},"mg_max":{"type":"number","description":"Upper end of the dose in milligrams for this weight"},"ml_by_form":{"type":"array","items":{"type":"object"},"description":"Millilitres for each strength sold, so the carer measures from the bottle they have"},"interval_hours":{"type":"array","items":{"type":"number"},"description":"Minimum and maximum hours between doses"},"max_doses_per_day":{"type":"integer","description":"Hard ceiling of doses in 24 hours"},"warnings":{"type":"array","items":{"type":"string"},"description":"Age limits and combinations to avoid, taken from the same guide"},"refer":{"type":"boolean","description":"true when the child must be seen by a doctor instead of medicated at home"},"source":{"type":"string","description":"The dosing guide the table comes from, with its edition"},"disclaimer":{"type":"string","description":"Information from published guidelines. Not a prescription."}}}'

VAC_REQ='{"type":"object","required":["country"],"description":"Which country schedule you want.","properties":{"country":{"type":"string","description":"ISO 3166-1 alpha-2. Transcribed schedules available: ES, GB, US"}}}'

VAC_DEL='{"type":"object","description":"The transcribed schedule of that country, with the body that issues it.","properties":{"country":{"type":"string","description":"The country the schedule belongs to"},"meta":{"type":"object","description":"Name of the schedule, issuing body, source URL and the date it was reviewed"},"schedule":{"type":"array","items":{"type":"object"},"description":"Each age with the vaccines due and what they protect against"},"disclaimer":{"type":"string","description":"A transcribed table. Your own health service decides what applies to your child."}}}'

ORS_REQ='{"type":"object","required":["weight_kg"],"description":"The weight and age of the child who is vomiting or has diarrhoea.","properties":{"weight_kg":{"type":"number","description":"The child weight in kilograms"},"age_months":{"type":"integer","description":"Age in months: under and over one year get different volumes"}}}'

ORS_DEL='{"type":"object","description":"How much oral rehydration solution to give and when to stop and seek help.","properties":{"age_band":{"type":"string","description":"infant or child: the volumes differ under and over one year"},"lines":{"type":"array","items":{"type":"string"},"description":"How much solution per intake and how often, in plain sentences"},"warnings":{"type":"array","items":{"type":"string"},"description":"When to stop and see a doctor or go to the emergency department"},"sources":{"type":"array","items":{"type":"string"},"description":"The product leaflet and the parent sheet the figures come from"},"disclaimer":{"type":"string","description":"Fluids, not medicine. Information from published guidelines."}}}'

update() {
  local name="$1" req="$2" del="$3" id
  id=$(acp offering list --json | python3 -c "
import json, sys
for o in json.load(sys.stdin):
    if o['name'] == '$name':
        print(o['id'])
        break
")
  [ -n "$id" ] || { echo "   !! $name not found"; return 1; }
  acp offering update --offering-id "$id" --requirements "$req" --deliverable "$del" --json >/dev/null
  echo "   $name"
}

echo "== filling in every schema description"
update "paediatric_question_with_sources" "$ASK_REQ" "$ASK_DEL"
update "child_medicine_dose" "$DOSE_REQ" "$DOSE_DEL"
update "childhood_vaccination_schedule" "$VAC_REQ" "$VAC_DEL"
update "oral_rehydration_plan" "$ORS_REQ" "$ORS_DEL"
