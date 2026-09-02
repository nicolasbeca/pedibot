#!/usr/bin/env bash
# PediBot's ACP catalogue: jobs, resources and subscription packages (1-sep-2026).
#
# Prices sit at the floor of the marketplace on purpose: the point is to be found by other
# agents, not to earn. Each product is its own job, because one generic offering matches
# almost no search; the worker routes each form to the endpoint that serves it, and doses and
# schedules come from fixed tables rather than from the model.
#
# Running `create` twice duplicates entries. This is meant to be read first and run once.
set -euo pipefail
cd /opt/pedibot

DOSE_REQ='{"type":"object","required":["drug","weight_kg"],"properties":{"drug":{"type":"string","description":"Brand printed on the bottle (Calpol, Tylenol, Apiretal, Dalsy, Nurofen, Advil...) or the generic name"},"weight_kg":{"type":"number","description":"The child weight in kg"},"age_months":{"type":"integer","description":"Age in months, if known: it changes the warnings"}}}'
DOSE_DEL='{"type":"object","properties":{"generic":{"type":"string"},"brand":{"type":["string","null"]},"mg_min":{"type":"number"},"mg_max":{"type":"number"},"ml_by_form":{"type":"array","items":{"type":"object"},"description":"Millilitres for each strength sold"},"interval_hours":{"type":"array","items":{"type":"number"}},"max_doses_per_day":{"type":"integer"},"warnings":{"type":"array","items":{"type":"string"}},"refer":{"type":"boolean","description":"true when the child must be seen instead of medicated"},"source":{"type":"string"},"disclaimer":{"type":"string"}}}'

VAC_REQ='{"type":"object","required":["country"],"properties":{"country":{"type":"string","description":"ISO 3166-1 alpha-2. Transcribed schedules: ES, GB, US"}}}'
VAC_DEL='{"type":"object","properties":{"country":{"type":"string"},"meta":{"type":"object","description":"Name of the schedule, issuing body, source URL and review date"},"schedule":{"type":"array","items":{"type":"object"},"description":"Each age with the vaccines due and what they protect against"},"disclaimer":{"type":"string"}}}'

ORS_REQ='{"type":"object","required":["weight_kg"],"properties":{"weight_kg":{"type":"number","description":"The child weight in kg"},"age_months":{"type":"integer","description":"Age in months: under and over one year get different volumes"}}}'
ORS_DEL='{"type":"object","properties":{"ml_per_intake":{"type":"array","items":{"type":"number"}},"every_minutes":{"type":"array","items":{"type":"number"}},"notes":{"type":"array","items":{"type":"string"}},"source":{"type":"string"},"disclaimer":{"type":"string"}}}'

NOPARAMS='{"type":"object","properties":{},"description":"No parameters: plain GET."}'

DOSE_DESC="Paracetamol or ibuprofen dose for a child by weight, read from fixed tables: the model is never involved in a number. Takes the brand printed on the bottle (Calpol, Tylenol, Apiretal, Dalsy, Nurofen, Advil and more, across 12 countries) or the generic name, and returns the mg range, the millilitres for each strength sold, the interval, the daily maximum and the age warnings. Refuses and refers when the child is too young to be medicated at home. Source: the AEPap dosing guide."

VAC_DESC="The official childhood vaccination schedule of a country, transcribed from the health authority itself: Spain (Ministerio de Sanidad 2025), the United Kingdom (NHS) and the United States (CDC 2025). Returns every age with the vaccines due and what each protects against, plus the issuing body, the source URL and the date it was reviewed. A transcribed table, not a recollection of one."

ORS_DESC="How much oral rehydration solution to offer a child who is vomiting or has diarrhoea: volume per intake, how often, and what to do when the child brings it back up. By weight and age, from the AEMPS leaflet for the solution and the SEUP parent sheet on vomiting. These are fluids, not medicine, and the figures come from the leaflet."

SRC_DESC="Every document PediBot is allowed to quote: 214 entries with the organisation, title, year, topic, licence and the URL of the original. This is the provenance behind every answer, published so it can be checked instead of trusted."

BRAND_DESC="Which brand is which medicine, and at what concentration, across 12 countries: Calpol, Tylenol, Apiretal, Dalsy, Nurofen, Advil and the rest, mapped to paracetamol or ibuprofen with the mg per ml of every presentation sold."

CHECK_DESC="What to take and what to expect when a child goes to a paediatric emergency department, from the SEUP parent material: documents, the medication list, what helps the triage nurse and what happens at each step."

VACRES_DESC="The transcribed childhood vaccination schedules for Spain, the United Kingdom and the United States, with the issuing body and the source URL. The same data the paid job returns, as a plain file for whoever prefers to parse it."

FEED_DESC="The feed of PediBot parent-facing guides. Each one is written only from published guidelines and names the organisation behind every clinical sentence."

echo "== 1. the offering that already existed: snake_case name and floor price"
acp offering update --offering-id 01a03e94-20a1-7a00-aed6-79cc26e8b8f9 \
  --name "paediatric_question_with_sources" --price-value 0.01 --json >/dev/null
echo "   ok"

echo "== 2. one job per product"
acp offering create --name "child_medicine_dose" --description "$DOSE_DESC" \
  --price-type fixed --price-value 0.01 --sla-minutes 5 \
  --requirements "$DOSE_REQ" --deliverable "$DOSE_DEL" \
  --no-required-funds --no-hidden --json >/dev/null
echo "   child_medicine_dose"

acp offering create --name "childhood_vaccination_schedule" --description "$VAC_DESC" \
  --price-type fixed --price-value 0.01 --sla-minutes 5 \
  --requirements "$VAC_REQ" --deliverable "$VAC_DEL" \
  --no-required-funds --no-hidden --json >/dev/null
echo "   childhood_vaccination_schedule"

acp offering create --name "oral_rehydration_plan" --description "$ORS_DESC" \
  --price-type fixed --price-value 0.01 --sla-minutes 5 \
  --requirements "$ORS_REQ" --deliverable "$ORS_DEL" \
  --no-required-funds --no-hidden --json >/dev/null
echo "   oral_rehydration_plan"

echo "== 3. resources: free files, no escrow"
acp resource create --name "paediatric_source_catalogue" --description "$SRC_DESC" \
  --url "https://pedibot.xyz/sources.json" --params "$NOPARAMS" --no-hidden --json >/dev/null
echo "   paediatric_source_catalogue"

acp resource create --name "child_medicine_brand_table" --description "$BRAND_DESC" \
  --url "https://pedibot.xyz/api/drugs" --params "$NOPARAMS" --no-hidden --json >/dev/null
echo "   child_medicine_brand_table"

acp resource create --name "emergency_department_checklist" --description "$CHECK_DESC" \
  --url "https://pedibot.xyz/api/checklist" \
  --params '{"type":"object","description":"Optional language for the checklist.","properties":{"lang":{"type":"string","enum":["en","es","fr","de"],"default":"en","description":"Language of the warning-sign wording: en, es, fr or de. The source is the same SEUP sheet in every case."}}}' \
  --no-hidden --json >/dev/null
echo "   emergency_department_checklist"

acp resource create --name "childhood_vaccination_schedules" --description "$VACRES_DESC" \
  --url "https://pedibot.xyz/api/vaccines?country=GB" \
  --params '{"type":"object","properties":{"country":{"type":"string","description":"ES, GB or US"}},"description":"One country per call."}' \
  --no-hidden --json >/dev/null
echo "   childhood_vaccination_schedules"

acp resource create --name "paediatric_guides_feed" --description "$FEED_DESC" \
  --url "https://pedibot.xyz/rss.xml" --params "$NOPARAMS" --no-hidden --json >/dev/null
echo "   paediatric_guides_feed"

echo "== 4. subscription packages"
S7=$(acp subscription create --name "pedibot_answers_7d" --price 0.25 --duration-days 7 --json \
     | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
S30=$(acp subscription create --name "pedibot_answers_30d" --price 0.50 --duration-days 30 --json \
     | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "   $S7 / $S30"

echo "== 5. attach both packages to every job"
acp offering list --json \
  | python3 -c "import json,sys; [print(o['id']) for o in json.load(sys.stdin)]" \
  | while read -r id; do
      [ -n "$id" ] || continue
      acp offering update --offering-id "$id" --subscription-ids "$S7,$S30" --json >/dev/null
      echo "   attached $id"
    done
