# Installing and running PediBot

Every step below was run from a fresh `git clone` on 28 September 2026. It takes about
fifteen minutes, and nothing in it needs an API key: the language model is replaced by a
canned one (`LLM_PROVIDER=fake`) until you choose to plug in a real one.

## What you need

- **Python 3.12** and **[uv](https://docs.astral.sh/uv/)** (it installs the Python dependencies).
- **Node.js 22.12 or later** and npm, only to build the website.
- Git. Any OS: it runs on Linux in production and was tested on Windows.

## 1 · The engine

```sh
git clone https://github.com/nicolasbeca/pedibot.git
cd pedibot
uv sync                                   # installs everything into .venv
cp .env.example .env                      # settings; see "Configuration" below
uv run pedibot ingest FUENTES --out index # builds the search index (SQLite FTS5)
```

`ingest` reports **"ingesta incompleta: N de M documentos sin procesar"** on a fresh clone,
and that is expected: the PDFs of the corpus are not in the repository, because several of
their publishers allow citing them but not redistributing them. The web pages the corpus is
built from *are* in the repository (`FUENTES/web/`), so the index you get is most of the
production one. Every document, including the missing ones, is listed with its licence and
URL in `config/fuentes.yaml` and at <https://pedibot.xyz/sources>.

Try it — none of these calls a model:

```sh
uv run pedibot triage "my baby is 2 months old and has a fever"   # rule-based warning signs
uv run pedibot dose paracetamol 12                                 # deterministic dose for 12 kg
uv run pedibot ask --fake "my 2 year old has a fever of 38.5"      # whole pipeline, canned model
uv run pedibot doctor                                              # checks every piece fits
```

## 2 · The API

```sh
LLM_PROVIDER=fake uv run pedibot serve          # http://127.0.0.1:8601
curl http://127.0.0.1:8601/api/health
curl -X POST http://127.0.0.1:8601/api/ask -H 'content-type: application/json' \
     -H 'x-pedibot-client: web' \
     -d '{"question": "my baby is 2 months old and has a fever of 38.2", "lang": "en"}'
```

The OpenAPI schema is at <http://127.0.0.1:8601/openapi.json>.

## 3 · The website

The site is static (Astro). Its data comes from the Python side, so export it first:

```sh
uv run python scripts/export_catalog.py
cd web/site
npm ci
node scripts/export-country-names.mjs
npm run build          # static site in web/site/dist
npm run dev            # or a dev server at http://localhost:4321, with /api proxied to :8601
```

Run `uv run pedibot doctor` again afterwards: it should end with `DOCTOR-FIN problemas=0`.

## Configuration (`.env`)

| Setting | What it does |
|---|---|
| `LLM_PROVIDER` | `deepseek` (any OpenAI-compatible endpoint) or `fake` (canned answers, no key) |
| `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `DEEPSEEK_API_KEY` | the endpoint. Despite the name, any OpenAI-compatible server works — for a local open model, e.g. Ollama: `http://localhost:11434/v1`, the model you pulled, and any non-empty key |
| `PHOTO_ENABLED` | `false` switches off reading photos of medicine boxes |
| `MAX_DAILY_LLM_USD` | daily spending cap; above it the chat answers with the tools only |

Everything else in `.env.example` (Telegram, Bluesky, X) is optional and only used by the
channels and posting scripts.

## Tests

```sh
uv run pytest            # the whole suite, about 15 minutes
uv run pedibot eval      # the golden set: triage, retrieval and routing, end to end
```

## How it fits together

```
question ──► triage (rules, config/red_flags.yaml) ──► warning + emergency number first
         └─► retrieval (SQLite FTS5 over the corpus) ──► language model writes from those
             passages only ──► verification (citations, doses from the sanctioned table)
             ──► answer, or "I have no reliable source for this"
tools, no model: dose calculator (config/drugs.yaml) · vaccination schedules (config/vaccines.yaml)
                 · emergency numbers (config/emergency_numbers.yaml) · growth charts and MUAC
```

| Where | What |
|---|---|
| `src/pedibot/bot/` | triage, answer pipeline, verification, dose calculator, vaccines |
| `src/pedibot/ingest/`, `src/pedibot/index/` | from documents to the search index |
| `src/pedibot/api.py` | the HTTP API (FastAPI) |
| `src/pedibot/publish/` | the guide generator (daily guides for parents, in eight languages) |
| `config/` | all reference data, as YAML: the part a health worker can review without code |
| `web/site/` | the website (Astro); `web/content/` the guides as Markdown |
| `ops/` | deployment to a Linux server (`ops/deploy.sh`, systemd units) |

## Contributing

Issues and pull requests are welcome on GitHub. Two rules the code enforces with tests: a
clinical statement must come from a document in the catalogue with its licence recorded, and
a medicine dose must come from the sanctioned dosing table. Most of the notes in the
repository (`PRD.md`, `LESSONS.md`, `STATE.md`) are in Spanish; the README and this file are
the English entry points.
