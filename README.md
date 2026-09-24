# PediBot

**A paediatric answer for a worried parent, with the source attached.** Live at
[pedibot.xyz](https://pedibot.xyz) — free, no account, eight languages.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22932517.svg)](https://doi.org/10.5281/zenodo.22932517)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)

A parent whose child has a fever at eleven at night gets a search results page. PediBot gives
them the paragraph the guideline actually writes about that, in their own language, with the
document it came from named and linked. When nothing in its library supports an answer, it says
so instead of filling the gap.

It does not diagnose. It is not a medical service. It says so on every answer.

---

## What is built

Every number below is counted from the files in this repository, never typed by hand — see
[DATOS.md](DATOS.md), which is generated, and `scripts/check_docs.py`, which fails the build if a
document repeats one of them wrongly.

- **645 paediatric documents** from paediatric societies, health ministries and the WHO, each
  with its licence read and recorded, and each answer cites the ones it used.
- **Emergency numbers for 90 countries**, each from the page of the body that publishes it. In
  eight of them the source states that no national service exists, and the page says that rather
  than invent a number.
- **Childhood vaccination schedules for 66 countries**, transcribed from the official document,
  with the issuing ministry and the date it was last checked.
- **96 red-flag rules** in nine languages, each one backed by a document that says so.
- **Paracetamol and ibuprofen dosing by weight**, from fixed tables, calculated in the page
  without a model, for the strength of the bottle the parent has in their hand.
- **WHO growth standards**: percentiles and z-scores, plus MUAC for acute malnutrition.
- **511 guides** written from the corpus, in eight languages.

## How an answer is made

    triage → retrieval → drafting → verification → assembly

1. **Triage** runs first and offline, on rules, not on a model: anything that looks like an
   emergency gets the banner and the local emergency number before a single token is generated.
2. **Retrieval** searches the indexed corpus (SQLite FTS5 plus vectors), with a cross-lingual
   bridge so that a question in Spanish reaches an English leaflet.
3. **Drafting** is the only step a language model touches, and it is handed the retrieved
   passages and told to use nothing else.
4. **Verification** rejects a draft with no citation, with a citation that points nowhere, or
   with a medicine dose that does not come from the sanctioned dosing table. A rejected draft is
   regenerated once; if it fails again, the answer is a refusal, not a guess.
5. **Assembly** puts the banner first, the answer second and the sources at the end.

The result of that last rule, measured on the live service: of the answers given, about 3% end
in "I have no reliable source for this". That number is the point of the whole design.

## Running it

    uv sync
    uv run pedibot ingest FUENTES --out index    # build the corpus index
    uv run pedibot ask "my 2 year old has a fever of 38.5"
    uv run pytest                                # 10.336 tests
    uv run pedibot eval                          # the golden set, end to end

The chat needs an API key for a language model; everything else — triage, doses, vaccination
schedules, emergency numbers, growth charts — works offline and without one.

## No lock-in

The chat talks to any OpenAI-compatible endpoint: `OpenAICompatibleProvider` takes a `base_url`,
so a local server — Ollama, vLLM, llama.cpp — works in place of a hosted model, and the corpus,
the index and every rule stay on your machine. Triage, doses, vaccination schedules, emergency
numbers, growth charts and MUAC need no model at all. The index is SQLite, the catalogue is JSON
and CSV, the site is static files. Nothing here needs a proprietary service to run.

## Licences, and why there are three

- **The code** is [AGPL-3.0-or-later](LICENSE). Use it, study it, run it. If you offer it as a
  service over a network, publish your changes too.
- **The catalogue** — the selection of documents, the classification and the metadata — is
  [CC0](dataset/LICENSE): public domain, take it. It is served as
  [sources.json](https://pedibot.xyz/dataset/sources.json) and listed, document by document with
  its licence, at [pedibot.xyz/sources](https://pedibot.xyz/sources).
- **The documents themselves** belong to the bodies that wrote them. The catalogue points at
  them and records each one's licence; it does not relicense them. Three documents in the
  corpus cannot be redistributed at all, and the public catalogue says so.

## For the curious, in Spanish

The project's own record is written in Spanish, because that is the language it is worked in:

- [STATE.md](STATE.md) — what was done, day by day.
- [LESSONS.md](LESSONS.md) — every mistake worth remembering, with what it cost and what it
  changed. It is the most useful file here if you want to know how this really went.
- [PRD.md](PRD.md) — the original plan.
- [CLAUDE.md](CLAUDE.md) — how the work is done.

---

## Ownership

Copyright © 2026 Nicolás Beca. The code is licensed under AGPL-3.0-or-later; the catalogue is
dedicated to the public domain under CC0. The name PediBot and the logo belong to the author and
are not covered by either licence: fork the code freely, but call your fork something else.

Contact: pedibot.ai@gmail.com

---

⚠️ **This is not medical advice and it does not replace a paediatrician.** If you think a child
is seriously ill, call your local emergency number.
