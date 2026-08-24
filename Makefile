.PHONY: install test lint format typecheck ingest search eval
install:
	uv sync --group dev
test:
	uv run pytest tests/ -q
lint:
	uv run ruff check src/ tests/
format:
	uv run ruff format src/ tests/
typecheck:
	uv run mypy src/
ingest:
	uv run pedibot ingest FUENTES --out index
eval:
	uv run pedibot eval eval/golden.jsonl
