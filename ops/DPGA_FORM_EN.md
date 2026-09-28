# DPGA application — the answers in English, ready to paste

> Version in Spanish, with the reasoning behind each answer: [`DPGA.md`](DPGA.md).
> Figures re-read on 28-sep-2026 from `DATOS.md` and the live site. The DPGA asks for everything in
> English, so every link below points to an English page or to the English README — never to
> PRD, LESSONS or DATOS, which are in Spanish.
>
> Category to choose: **Open Software**. Not "Open AI System": the DPGA guide says explicitly that
> software using a third-party LLM for some features is Open Software.

---

## 0 · General information

**Name:** PediBot

**Website:** https://pedibot.xyz

**Source code:** https://github.com/nicolasbeca/pedibot

**Short description (one line):**

A free paediatric answer for a worried parent, built only from published paediatric guidelines, and naming the document every time.

**Long description:**

PediBot answers the questions families ask when a child is ill — fever, dosing, rashes, vaccines, growth, when to go to hospital — using only what paediatric societies, ministries of health and the WHO already publish for parents, and citing the document each sentence comes from. It is free, needs no account, and works in eight languages (English, Spanish, French, Portuguese, German, Russian, Hindi and Arabic).

Before any language model is involved, a rule-based triage checks 96 red-flag rules and, when one fires, puts the local emergency number first (90 countries, including all 54 in Africa). Doses come from an authorised table, not from the model. A verification step rejects any draft that does not cite, cites something that does not exist, or states a dose outside the table; if the second attempt also fails, the answer is a refusal.

Vaccination schedules (66 countries), growth charts (78 countries) and MUAC screening work with no model at all. The catalogue of 632 source documents is published as open data (CC0).

---

## 1 · Relevance to the SDGs

**SDG 3 — Good health and well-being.** Targets **3.2** (end preventable deaths of newborns and children under 5) and **3.8** (universal health coverage, including access to quality health information).

PediBot gives any parent with a phone the guidance their own health system already publishes, in their language and with the source attached. What ties it to target 3.2 is the data it carries: the emergency number of all 54 African countries and the vaccination schedule of all 54; MUAC (mid-upper arm circumference) screening for acute malnutrition, the tool community programmes use where there is no scale; and WHO growth charts for countries without their own. The 96 red-flag rules are written so that a parent recognises a seriously ill child and seeks care, not so that they stay at home: when one fires, the emergency number comes first.

Evidence: https://pedibot.xyz/about

---

## 2 · Open licensing

| Asset | Licence | Link |
|---|---|---|
| Source code | AGPL-3.0-or-later (OSI-approved) | https://github.com/nicolasbeca/pedibot/blob/master/LICENSE |
| Catalogue of sources (data) | CC0 1.0 | https://huggingface.co/datasets/PediBot/pedibot-sources |

The clinical documents themselves belong to the bodies that publish them (NHS, CDC, WHO, ministries of health) and are not relicensed: the catalogue points to them and records each one's licence. Three documents in the corpus cannot be redistributed, and the public catalogue says so.

---

## 3 · Clear ownership

Copyright © 2026 Nicolás Beca, stated in the README (Ownership section): https://github.com/nicolasbeca/pedibot#ownership

The name PediBot and the logo belong to the author and are not covered by the licence: the code can be forked, the brand cannot. Public contact: pedibot.ai@gmail.com, shown on every page of the site.

Archived at Zenodo (CERN) with a DOI: https://doi.org/10.5281/zenodo.22932517

---

## 4 · Platform independence

Core dependencies: Python, FastAPI, SQLite (with FTS5), and a static site built with Astro. All open source; everything installs with `uv sync`.

The only external service is the language model that writes the final answer, and it is replaceable: the chat talks to any OpenAI-compatible endpoint (`OpenAICompatibleProvider` takes a `base_url`), so a local open-source server — Ollama, vLLM, llama.cpp — works in its place without changing the code. Triage, doses, vaccination schedules, emergency numbers, growth charts and MUAC need no model at all: they are rules and tables and run locally.

Evidence: https://github.com/nicolasbeca/pedibot#no-lock-in

SBOM: attached (exported from GitHub's dependency graph).

A note on what the SBOM shows: a few NVIDIA CUDA packages with proprietary licences appear in it. They come only through the optional `embeddings` extra (`sentence-transformers` → PyTorch's GPU build) and are not needed to run PediBot: the default install does not include that extra, and where embeddings are wanted, PyTorch's CPU build — fully open (BSD) — works in their place with no code change.

---

## 5 · Documentation

The README explains what PediBot is, how an answer is built, how to install and run it, and the licences: https://github.com/nicolasbeca/pedibot#readme

To run it locally:

    uv sync
    uv run pedibot ingest FUENTES --out index
    uv run pedibot ask "my 2 year old has a fever of 38.5"
    uv run pytest

The repository has 10,427 automated tests and a golden set that is measured end to end before every deployment.

---

## 6 · Mechanism for extracting data

PediBot's non-personal data is its catalogue of sources, published in full, in non-proprietary formats, under CC0:

- JSON: https://pedibot.xyz/dataset/sources.json (632 documents)
- CSV: https://github.com/nicolasbeca/pedibot/blob/master/dataset/sources.csv
- Hugging Face, with a browsable table: https://huggingface.co/datasets/PediBot/pedibot-sources
- Human-readable list: https://pedibot.xyz/sources

They are generated from the catalogue with `uv run python scripts/export_dataset.py` and contain no user data: they come from the source catalogue, not from the usage log. Users with an account can also download all their own data from their account page.

---

## 7 · Privacy and applicable laws

Privacy policy: https://pedibot.xyz/legal (published in all eight languages)

Laws: EU General Data Protection Regulation (Regulation (EU) 2016/679, GDPR); Spain's Organic Law 3/2018 on Data Protection (LOPDGDD). The policy names both, identifies the data controller (Nicolás Beca, pedibot.ai@gmail.com) and states the user's rights of access, rectification, erasure and portability, and the right to complain to the Spanish Data Protection Agency (aepd.es).

What the system does:

- Without an account, no personal data is requested, and the site says so in those words.
- With an account (optional): e-mail, a hashed password and, for each child, name, date of birth, sex, country and the measurements the parent notes. Everything can be downloaded, and the account deleted, from the user's own page without asking anyone.
- Questions and answers are stored anonymously (random session token, no IP address) to evaluate quality. Conversation memory lasts 24 hours.
- The IP address is used only as a salted hash for rate limiting and is not stored in clear.
- No advertising trackers, no ads, no data sold or shared with third parties.

---

## 8 · Standards and best practices

- HTTP/JSON API with an OpenAPI schema (generated by FastAPI).
- Static HTML with `hreflang` and `sitemap.xml`.
- Open formats for data: JSON and CSV; CC0 licence for the catalogue.
- Citable software: DOI at Zenodo and a `CITATION.cff` file in the repository.
- Clinical content: only guidelines published by the bodies themselves (WHO, ministries of health, paediatric societies), each answer linking the original instead of rewriting it.

(If the form offers the DPGA's list of featured standards, tick the ones above that appear there.)

---

## 9 · Do no harm by design

A language model only writes, and only with the passages it is given. First there is a rule-based triage, with no model, that puts the warning and the emergency number before anything else. Then a verification step rejects the draft if it does not cite, cites something that does not exist, or states a dose that does not come from the authorised table. A rejected draft is regenerated once; if it fails again, the answer is a refusal. Measured on the live service: about 3% of answers end in "I have no reliable source for this", and that is the product working, not failing.

### 9a · Data privacy and security

As in indicator 7, plus: the account database is separate from the anonymous one; passwords are stored hashed; the server serves only over HTTPS; shared answer pages carry `noindex` and a random identifier that cannot be guessed, and whoever shared one can remove it from the page itself.

### 9b · Inappropriate and illegal content

PediBot does not publish user content: there is no forum, no comments, no profiles. The only thing a user can make public is their own answer, with the share button, and that page:

1. can only be created by whoever asked the question, from their own session;
2. is not indexed (`noindex`) and its address cannot be guessed;
3. can be removed by whoever created it, in one click, from the page itself;
4. and anyone who sees one that should not exist can write to pedibot.ai@gmail.com, published on every page.

Misleading content is what the answer pipeline is built against: nothing is said without a cited source, and doses outside the authorised table are rejected.

### 9c · Protection from harassment

There is no interaction between users: nobody can write to anybody inside PediBot; there are no public names, messages or comments. By construction there is no surface for harassment.

On minors: PediBot is written for the adult caring for a child. The children's data, when there is an account, is entered by that adult, who can delete it at any time. The chat never asks for the child's name or any identifying detail, and the site says explicitly that none is needed.

---

## Authorised representative (asked in indicators 7–9)

Name: Nicolás Beca
Title: Founder and maintainer, PediBot
E-mail: pedibot.ai@gmail.com
