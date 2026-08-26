"""`pedibot` command line: ingest, search, triage, dose, ask."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import typer
from loguru import logger

from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.vaccines import Vaccines
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
    from pedibot.ingest.classify import Taxonomy

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
            taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
        ),
        Triage(s.config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(s.config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(s.config_dir / "drugs.yaml"),
        vaccines=Vaccines(s.config_dir / "vaccines.yaml"),
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
    llm: bool = typer.Option(
        False, "--llm", help="also draft every answer with the REAL LLM (costs money)"
    ),
    judge: bool = typer.Option(
        False, "--judge", help="with --llm: second call judging faithfulness (costs money)"
    ),
) -> None:
    """Golden-set evaluation of triage + retrieval + routing (no LLM needed)."""
    import datetime as dt

    from pedibot.eval import fake_engine_from_settings, load_golden, run_eval

    if llm:
        _llm_eval(golden, report_dir, judge)
        return
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


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8601, reload: bool = False) -> None:
    """Run the HTTP API (uvicorn). Needs DEEPSEEK_API_KEY unless LLM_PROVIDER=fake."""
    import uvicorn

    uvicorn.run("pedibot.api:app_from_settings", host=host, port=port, reload=reload, factory=True)


@app.command()
def publish(
    topic: str | None = None,
    lang: str = "en",
    n: int = 1,
    fake: bool = False,
    site_url: str = "https://pedibot.xyz",
    social: bool = typer.Option(
        True,
        "--social/--no-social",
        help="syndicate to Bluesky / Telegram channel / X if configured",
    ),
) -> None:
    """Generate grounded article(s) → web/content/<lang>/ + publish/queue/x/. Auto-publish policy."""
    from pedibot.bot.llm import FakeProvider, provider_from_settings
    from pedibot.index.store import Index
    from pedibot.publish.articles import generate_article, pending_topics, write_article

    s = get_settings()
    fake_text = "TITLE: t\nSUMMARY: s\nBODY:\n## What it is\nx [1]."
    llm = FakeProvider(fake_text) if fake else provider_from_settings()
    index = Index(s.index_db_path)
    content = ROOT / "web" / "content"
    queue = ROOT / "publish" / "queue"
    topics = [topic] if topic else pending_topics(content, lang)[:n]
    for t in topics:
        try:
            a = generate_article(index, llm, t, lang)
        except ValueError as e:
            typer.echo(f"  ! {t}: {e}")
            continue
        md, q = write_article(a, content, queue, site_url)
        typer.echo(
            f"  ✓ {t} → {md}  (social text: {q})  cost=${a.llm.cost_usd:.4f} {a.verification}"
        )
        if social and not fake:
            from pedibot.publish.social import Post, providers_from_env, syndicate

            prefix = "/es" if lang == "es" else ""
            post = Post(a.title, a.summary, f"{site_url}{prefix}/guides/{a.slug}", lang)
            res = syndicate(post, providers_from_env())
            typer.echo(f"    social: {res or 'no providers configured'}")


def _llm_eval(golden: Path, report_dir: Path, use_judge: bool = False) -> None:
    import datetime as dt

    from pedibot.api import app_from_settings  # noqa: F401  (validates settings/provider)
    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.llm import provider_from_settings
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.bot.triage import Triage
    from pedibot.eval import load_golden, run_llm_eval
    from pedibot.index.store import Index
    from pedibot.ingest.classify import Taxonomy

    s = get_settings()
    prov = provider_from_settings()
    eng = Engine(
        Retriever(
            Index(s.index_db_path),
            Synonyms(s.config_dir / "synonyms.yaml"),
            llm=prov,
            top_k=s.retrieval_top_k,
            taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
        ),
        Triage(s.config_dir / "red_flags.yaml"),
        prov,
        EmergencyNumbers(s.config_dir / "emergency_numbers.yaml"),
    )
    rep = run_llm_eval(eng, load_golden(golden), use_judge=use_judge)
    summ = rep.summary()
    typer.echo(json.dumps(summ, indent=2))
    for c in rep.cases:
        if c.verification == "fallback":
            typer.echo(f"  ! {c.id} «{c.q}» → fallback (draft failed verification twice)")
        if c.judge_verdict and c.judge_verdict != "faithful":
            typer.echo(f"  ⚖ {c.id} {c.judge_verdict}: {c.judge_notes} {c.judge_issues}")
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / f"eval_llm_{dt.date.today().isoformat()}.json"
    out.write_text(
        json.dumps(
            {"summary": summ, "cases": [c.__dict__ for c in rep.cases]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    typer.echo(f"→ {out}")


@app.command()
def balance(warn_below_pct: float = 20.0, initial_usd: float = 0.0) -> None:
    """DeepSeek account balance (GET /user/balance). Exit code 2 when below the warning threshold."""
    from pedibot.bot.llm import deepseek_balance

    s = get_settings()
    b = deepseek_balance(s.deepseek_api_key, s.deepseek_base_url)
    typer.echo(json.dumps(b, indent=2))
    raw_total = b.get("total_usd")
    total = float(raw_total) if isinstance(raw_total, (int, float)) else None
    if total is not None and initial_usd > 0:
        pct = 100 * total / initial_usd
        typer.echo(f"remaining: {pct:.1f}% of {initial_usd} USD")
        if pct < warn_below_pct:
            typer.echo("⚠️  BALANCE LOW — top up at platform.deepseek.com")
            raise typer.Exit(code=2)
    elif total is not None and total < 1.0:
        typer.echo("⚠️  BALANCE LOW (< 1 USD) — top up at platform.deepseek.com")
        raise typer.Exit(code=2)


@app.command()
def telegram() -> None:
    """Run the public Telegram chatbot (long polling). Needs TELEGRAM_PUBLIC_BOT_TOKEN."""
    from pedibot.telegram_bot import front_from_settings, run_polling

    s = get_settings()
    if not s.telegram_public_bot_token:
        raise typer.BadParameter("TELEGRAM_PUBLIC_BOT_TOKEN missing in .env")
    run_polling(front_from_settings(), s.telegram_public_bot_token)


@app.command()
def announce(
    text: str,
    lang: str | None = None,
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force", help="ignore the 14-day guard"),
) -> None:
    """Send a RARE notice to people who used the Telegram bot (no channel, opt-out honoured)."""
    from pedibot.announce import send_announcement, too_soon
    from pedibot.ops.store import OpsStore

    s = get_settings()
    ops = OpsStore(s.ops_db_path)
    soon, last = too_soon(ops)
    if soon and not force:
        raise typer.BadParameter(
            f"last notice was {last} (<14 days). Use --force only if it matters."
        )
    if not s.telegram_public_bot_token:
        raise typer.BadParameter("TELEGRAM_PUBLIC_BOT_TOKEN missing")
    res = send_announcement(ops, s.telegram_public_bot_token, text, lang, dry_run)
    typer.echo(json.dumps(res))


if __name__ == "__main__":
    logger.disable("pedibot")
    app()
