"""`pedibot` command line: ingest, search, triage, dose, ask."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import typer
from loguru import logger

from pedibot.settings import ROOT, get_settings

app = typer.Typer(help="PediBot v2 — pediatric assistant grounded in verified guidelines.")


@app.command()
def ingest(
    sources: Path = typer.Argument(ROOT / "FUENTES"),
    out: Path = typer.Option(ROOT / "index", "--out"),
    force: bool = typer.Option(
        False, "--force", help="re-process even if the PDF hash is unchanged"
    ),
    no_index: bool = typer.Option(False, "--no-index", help="only write JSONL, skip SQLite build"),
) -> None:
    """PDFs → chunks JSONL → SQLite FTS5 index. Writes index/ingest_report.csv."""
    from pedibot.index.store import build_index, dump_index_stats
    from pedibot.ingest.pipeline import load_all_chunks, run_ingest

    s = get_settings()
    reports = run_ingest(
        sources, out, s.config_dir / "fuentes.yaml", s.config_dir / "taxonomia.yaml", force=force
    )
    rep_path = out / "ingest_report.csv"
    with rep_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "doc_id",
                "file",
                "status",
                "pages",
                "words",
                "sections",
                "chunks",
                "red_flag",
                "dose",
                "detail",
            ]
        )
        for r in reports:
            w.writerow(
                [
                    r.doc_id,
                    r.file,
                    r.status,
                    r.n_pages,
                    r.n_words,
                    r.n_sections,
                    r.n_chunks,
                    r.n_red_flag,
                    r.n_dose,
                    r.detail,
                ]
            )
    by_status: dict[str, int] = {}
    for r in reports:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    typer.echo(f"ingest: {by_status}  → {rep_path}")
    for r in reports:
        if r.status in ("error", "no_text"):
            typer.echo(f"  ! {r.file}: {r.status} {r.detail}")
    if not no_index:
        chunks = load_all_chunks(out)
        n = build_index(chunks, s.index_db_path)
        typer.echo(f"index: {n} chunks → {s.index_db_path}  {dump_index_stats(s.index_db_path)}")


@app.command()
def search(query: str, k: int = 6, red_flag: bool = False) -> None:
    """Lexical search in the index (with cross-lingual expansion)."""
    from pedibot.bot.retrieval import Retriever, Synonyms, detect_lang
    from pedibot.index.store import Index
    from pedibot.ingest.classify import Taxonomy

    s = get_settings()
    r = Retriever(
        Index(s.index_db_path),
        Synonyms(s.config_dir / "synonyms.yaml"),
        top_k=k,
        taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
    )
    lang = detect_lang(query)
    hits, extra = r.search(query, lang, red_flag_boost=red_flag)
    typer.echo(f"lang={lang} expansion={extra}")
    for h in hits:
        c = h.chunk
        typer.echo(
            f"{h.score:7.2f}  {c.chunk_id}  [{c.doc_type}{' RF' if c.is_red_flag else ''}{' DOSE' if c.is_dose_table else ''}]"
        )
        typer.echo(f"         {c.text[:160]}…")


@app.command()
def triage(text: str, lang: str = "en") -> None:
    """Rule-based severity assessment of a message."""
    from pedibot.bot.triage import Triage

    s = get_settings()
    t = Triage(s.config_dir / "red_flags.yaml").assess(text)
    typer.echo(
        json.dumps(
            {
                "level": t.level,
                "age_months": t.age_months,
                "fever": t.has_fever,
                "reasons": t.reasons(lang),
                "rules": [r.id for r in t.matched],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command()
def dose(drug: str, kg: float, months: float | None = None, lang: str = "en") -> None:
    """Deterministic dose calculator (paracetamol / ibuprofen)."""
    from pedibot.bot.dose import calculate, format_result

    typer.echo(format_result(calculate(drug, kg, months), lang))


@app.command()
def ask(
    query: str, country: str | None = None, fake: bool = False, show_chunks: bool = False
) -> None:
    """Full pipeline. --fake uses a canned LLM (no API key needed) to exercise triage+retrieval."""
    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.llm import FakeProvider, provider_from_settings
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.bot.triage import Triage
    from pedibot.index.store import Index

    s = get_settings()
    llm = (
        FakeProvider(lambda sys_, user: "Fake draft based on the sources [1].")
        if fake
        else provider_from_settings()
    )
    eng = Engine(
        Retriever(
            Index(s.index_db_path),
            Synonyms(s.config_dir / "synonyms.yaml"),
            llm=None if fake else llm,
            top_k=s.retrieval_top_k,
        ),
        Triage(s.config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(s.config_dir / "emergency_numbers.yaml"),
    )
    a = eng.ask(query, country=country)
    typer.echo(a.render())
    typer.echo(f"\n--- level={a.level} verification={a.verification} expansion={a.expansion}")
    if a.llm:
        typer.echo(
            f"--- tokens in/out={a.llm.tokens_in}/{a.llm.tokens_out} cost=${a.llm.cost_usd:.5f} model={a.llm.model}"
        )
    if show_chunks:
        typer.echo("--- chunks: " + ", ".join(a.chunk_ids))


@app.command("eval")
def eval_cmd(
    golden: Path = ROOT / "eval" / "golden.jsonl",
    k: int = 3,
    report_dir: Path = ROOT / "eval" / "reports",
) -> None:
    """Golden-set evaluation of triage + retrieval + routing (no LLM needed)."""
    import datetime as dt

    from pedibot.eval import fake_engine_from_settings, load_golden, run_eval

    rep = run_eval(fake_engine_from_settings(), load_golden(golden), k=k)
    summ = rep.summary()
    typer.echo(json.dumps(summ, indent=2))
    fails = rep.failures()
    typer.echo(f"\n{len(fails)} cases with problems:")
    for f in fails:
        typer.echo("  " + f)
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / f"eval_{dt.date.today().isoformat()}.json"
    out.write_text(
        json.dumps(
            {"summary": summ, "failures": fails, "n": len(rep.cases)}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    typer.echo(f"→ {out}")


if __name__ == "__main__":
    logger.disable("pedibot")
    app()
