"""`pedibot` command line: ingest, search, triage, dose, ask."""

from __future__ import annotations

import csv
import json
import os
from importlib.metadata import version
from pathlib import Path

import typer
from loguru import logger

from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.growth import Growth
from pedibot.bot.vaccines import Vaccines
from pedibot.settings import ROOT, get_settings

#: Las lenguas en las que se publican guías. `doctor` mira que a ninguna se le acabe la
#: materia: una cola vacía y un proceso roto se leen igual desde fuera (L126).
LANGS_PUBLICADAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")

app = typer.Typer(help="PediBot v2 — pediatric assistant grounded in verified guidelines.")


#: Errores que son del USUARIO, no del programa: se dicen en una línea y se sale con 2, que es
#: lo que usa `typer` para «me has pedido algo imposible». Una traza de Python de veinte líneas
#: dice «esto está roto», y no lo está: le han pedido un fármaco que no existe (11-sep-2026).
def _falla(mensaje: str, pista: str = "") -> typer.Exit:
    typer.secho(f"error: {mensaje}", fg=typer.colors.RED, err=True)
    if pista:
        typer.secho(pista, err=True)
    return typer.Exit(code=2)


def _version_callback(valor: bool) -> None:
    if valor:
        typer.echo(f"pedibot {version('pedibot')}")
        raise typer.Exit()


@app.callback()
def _raiz(
    version_: bool = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Qué código está corriendo de verdad.",
    ),
) -> None:
    """PediBot v2 — pediatric assistant grounded in verified guidelines."""


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
        # con el catálogo delante, para que lo retirado se vaya de verdad (24-sep-2026)
        chunks = load_all_chunks(out, catalogo={r.doc_id for r in reports if r.doc_id != "?"})
        n = build_index(chunks, s.index_db_path)
        typer.echo(f"index: {n} chunks → {s.index_db_path}  {dump_index_stats(s.index_db_path)}")

    # El código de salida cuenta el RESULTADO, no el hecho de haber llegado al final. Con una
    # ruta equivocada esto fallaba los 422 documentos, reconstruía el índice con los JSONL
    # viejos y devolvía 0: doce timers miran `$?` y habrían dado la ingesta por buena
    # (11-sep-2026). Es la L127 por el otro lado — allí conté un código de salida como si
    # fuera un resultado; aquí el código de salida no contaba el resultado.
    fallidos = by_status.get("error", 0) + by_status.get("no_text", 0)
    if fallidos:
        typer.secho(
            f"ingesta incompleta: {fallidos} de {len(reports)} documentos sin procesar",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)


@app.command()
def search(query: str, k: int = 6, red_flag: bool = False) -> None:
    """Lexical search in the index (with cross-lingual expansion)."""
    # Un `--k` de cero o negativo llegaba tal cual al LIMIT del FTS y volcaba el índice
    # entero: 1.091 líneas por una errata (11-sep-2026).
    if k < 1:
        raise _falla(f"--k tiene que ser 1 o más, no {k}")
    from pedibot.bot.retrieval import Retriever, Synonyms, detect_lang
    from pedibot.index.store import Index
    from pedibot.ingest.classify import Taxonomy

    s = get_settings()
    r = Retriever(
        Index(s.index_db_path),
        Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
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
    from pedibot.bot.dose import DRUGS, DoseError, calculate, format_result

    try:
        typer.echo(format_result(calculate(drug, kg, months), lang))
    except DoseError as e:
        raise _falla(str(e), "fármacos: " + ", ".join(sorted(DRUGS))) from None


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
            Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
            llm=None if fake else llm,
            top_k=s.retrieval_top_k,
            taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
        ),
        Triage(s.config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(s.config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(s.config_dir / "drugs.yaml"),
        vaccines=Vaccines(s.config_dir / "vaccines.yaml"),
        growth=Growth(s.config_dir / "who_growth.json"),
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
    repeat: int = typer.Option(
        1,
        "--repeat",
        help="with --llm: run it N times and average (the single-run noise is ±0.13)",
    ),
) -> None:
    """Golden-set evaluation of triage + retrieval + routing (no LLM needed)."""
    import datetime as dt

    from pedibot.eval import fake_engine_from_settings, load_golden, run_eval

    if llm:
        _llm_eval(golden, report_dir, judge, repeat)
        return
    rep = run_eval(fake_engine_from_settings(), load_golden(golden), k=k)
    summ = rep.summary()
    typer.echo(json.dumps(summ, indent=2))
    fails = rep.failures()
    if rep.unmeasured_sources:
        # said out loud rather than folded into the ratio: those languages have no local
        # synonym table, so their retrieval goes through a translation call this harness
        # deliberately does not make
        typer.echo(
            f"\nsource_hit no medible en {len(rep.unmeasured_sources)} casos "
            "(idiomas sin sinónimos locales: su recuperación pasa por la IA)"
        )
    typer.echo(f"\n{len(fails)} cases with problems:")
    for f in fails:
        typer.echo("  " + f)
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / f"eval_{dt.date.today().isoformat()}.json"
    out.write_text(
        json.dumps(
            {
                "summary": summ,
                "failures": fails,
                "n": len(rep.cases),
                "source_hit_unmeasured": rep.unmeasured_sources,
            },
            ensure_ascii=False,
            indent=2,
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
    # Re-read the pending list before each article instead of taking it once: otherwise a batch
    # cannot see what the batch itself just wrote, and a run of 90 topics happily publishes both
    # `hives` and `urticaria` (2-sep-2026).
    written, failed = 0, set()  # `failed` matters: nothing is written, so the topic would be
    while written < n:  # picked again for ever on the next round
        if topic:
            t = topic if written == 0 and topic not in failed else None
        else:
            remaining = [x for x in pending_topics(content, lang) if x not in failed]
            t = remaining[0] if remaining else None
        if t is None:
            break
        try:
            a = generate_article(index, llm, t, lang)
        except ValueError as e:
            typer.echo(f"  ! {t}: {e}")
            failed.add(t)
            continue
        written += 1
        md, q = write_article(a, content, queue, site_url)
        typer.echo(
            f"  ✓ {t} → {md}  (social text: {q})  cost=${a.llm.cost_usd:.4f} {a.verification}"
        )
        if social and not fake:
            from pedibot.publish.social import Post, providers_from_env, syndicate

            # el inglés va en la raíz y TODO lo demás lleva su prefijo, como en el resto
            # del código. Escrito al revés, el enlace del post de una guía francesa,
            # alemana, rusa, árabe, portuguesa o hindi apuntaba a la versión inglesa.
            prefix = "" if lang == "en" else f"/{lang}"
            post = Post(a.title, a.summary, f"{site_url}{prefix}/guides/{a.slug}", lang)
            res = syndicate(post, providers_from_env())
            typer.echo(f"    social: {res or 'no providers configured'}")


def _llm_eval(golden: Path, report_dir: Path, use_judge: bool = False, repeat: int = 1) -> None:
    """Con `repeat > 1` se ejecuta N veces y se promedia.

    Hace falta porque la medición NO es reproducible: el mismo prompt, medido dos veces sin
    cambiar nada, dio 0,788 y 0,663 —amplitud 0,125— porque el modelo redacta distinto cada vez
    (parecido medio entre dos redacciones del mismo caso: 0,48; a temperatura 0 sigue en 0,68,
    o sea que no es cosa del parámetro sino del proveedor). Medido el 8-sep-2026.

    Con eso, una tirada suelta no puede distinguir dos prompts que se lleven menos de ~0,13, y
    esa es exactamente la magnitud de los cambios que se intentan. Promediando N tiradas el
    ruido baja con la raíz de N: tres tiradas lo dejan en ~0,07, cinco en ~0,06.

    No es gratis: cada tirada cuesta unos 0,07 $ y media hora. Por eso el valor por defecto
    sigue siendo 1 — pero cuando se compare un prompt con otro, una sola tirada no vale.
    """
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
            Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
            llm=prov,
            top_k=s.retrieval_top_k,
            taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
        ),
        Triage(s.config_dir / "red_flags.yaml"),
        prov,
        EmergencyNumbers(s.config_dir / "emergency_numbers.yaml"),
    )
    casos = load_golden(golden)
    tiradas = []
    for n in range(max(1, repeat)):
        if repeat > 1:
            typer.echo(f"— tirada {n + 1} de {repeat}")
        rep = run_llm_eval(eng, casos, use_judge=use_judge)
        tiradas.append(rep)
    summ = rep.summary()
    if repeat > 1:
        # el promedio de lo que varía, y el RANGO, que es lo que dice si una diferencia existe
        medias: dict[str, object] = {}
        for clave in ("faithful_rate", "citation_validity", "regenerated_rate"):
            crudos = [t.summary().get(clave) for t in tiradas]
            vals: list[float] = [
                float(v) for v in crudos if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            if vals:
                medias[clave] = round(sum(vals) / len(vals), 4)
                medias[f"{clave}_rango"] = [round(min(vals), 4), round(max(vals), 4)]
        medias["tiradas"] = len(tiradas)
        summ = {**summ, "promedio": medias}
        typer.echo(json.dumps(medias, indent=2, ensure_ascii=False))
        typer.echo(
            "  ↑ el rango es lo que importa: una diferencia menor que él no se distingue"
            " del azar (ver L59/L61 y la nota de answer_v5.md)."
        )
    typer.echo(json.dumps(rep.summary(), indent=2))
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
def flagged(clear: bool = False) -> None:
    """Answers marked as bad in /admin, ready to become golden cases.

    Prints each one with a draft entry for eval/golden.jsonl. The expected level and documents are
    left as they came out, marked TODO: a golden case states what SHOULD have happened, and taking
    that from the answer that was wrong would freeze the mistake into the test that guards it.
    """
    from pedibot.admin import load_flagged, save_flagged

    items = load_flagged()
    if not items:
        typer.echo("Nada marcado. En /admin, «marcar como mala» aparta una respuesta para aquí.")
        return
    for rec in items.values():
        typer.echo(f"\n── #{rec['id']}  {rec.get('lang', '?')}  {rec.get('ts', '')}")
        typer.echo(f"   P: {rec.get('question', '')}")
        answer = str(rec.get("answer", "")).split("\n\n")[0]
        typer.echo(f"   R: {answer[:300]}")
        draft = {
            "id": "TODO",
            "q": rec.get("question", ""),
            "lang": rec.get("lang", "es"),
            "level": f"TODO (salió {rec.get('level')})",
            "docs": ["TODO"],
        }
        typer.echo("   golden.jsonl: " + json.dumps(draft, ensure_ascii=False))
    typer.echo(f"\n{len(items)} marcadas.")
    if clear:
        save_flagged({})
        typer.echo("Lista vaciada.")


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


@app.command()
def broadcast(
    what: str = typer.Argument(..., help="project | guides"),
    dry_run: bool = typer.Option(False, "--dry-run", help="enseña qué publicaría y no publica"),
) -> None:
    """Las dos publicaciones periódicas de Bluesky (11-sep-2026).

    `project` cada dos días y `guides` una vez a la semana, una por idioma. Hasta hoy Bluesky
    sólo recibía algo al generarse una guía, y como nada lanzaba esa generación llevaba una
    semana en silencio.
    """
    from pedibot.publish import broadcast as b
    from pedibot.publish.social import providers_from_env, syndicate

    if what not in ("project", "guides"):
        raise typer.BadParameter("solo 'project' o 'guides'")
    # un ensayo no gasta el turno de la rotación: enseña lo siguiente sin consumirlo
    posts = (
        [b.project_post(advance=not dry_run)]
        if what == "project"
        else b.weekly_guides(advance=not dry_run)
    )
    providers = providers_from_env()
    if not providers and not dry_run:
        typer.echo("sin credenciales de ningún canal: no se publica nada")
        raise typer.Exit(0)
    for p in posts:
        if dry_run:
            typer.echo(f"[{p.lang}] {p.text()}\n---")
            continue
        res = syndicate(p, providers)
        ok = [k for k, v in res.items() if v]
        typer.echo(f"[{p.lang}] {'ok ' + ','.join(ok) if ok else 'sin salida'}: {p.url}")
    # la firma va al final a propósito: si el proceso muere antes, su ausencia es la prueba (L117)
    typer.echo(f"BROADCAST-FIN {what} publicadas={len(posts)}")


@app.command()
def doctor(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Revisión de la instalación: ¿casa cada pieza con las demás?

    Todo lo que se rompió en este proyecto es de la misma familia — una pieza deja de casar con
    otra y **nada falla**: documentos indexados sin entrada de catálogo y por tanto sin licencia
    registrada (L131), reglas de alarma citando una ficha inexistente (L137), las concentraciones
    del catálogo y las de la calculadora separadas (L142), países servidos sin número de
    emergencias, la cola de publicación vacía con el timer corriendo cada mañana (L126).

    Los candados de `tests/` ven todo eso, pero corren en el PC. Esto corre donde está el
    producto, y **sale con código 1 si algo está mal**, que es lo que permite colgarlo de un
    timer.
    """
    import sqlite3

    import yaml

    s = get_settings()
    malas = 0

    def ok(titulo: str, detalle: str) -> None:
        typer.secho(f"✓ {titulo}: ", fg=typer.colors.GREEN, nl=False)
        typer.echo(detalle)

    def mal(titulo: str, detalle: str) -> None:
        nonlocal malas
        malas += 1
        typer.secho(f"✗ {titulo}: ", fg=typer.colors.RED, nl=False, err=True)
        typer.echo(detalle, err=True)

    typer.echo(f"pedibot {version('pedibot')}  ·  {ROOT}")

    # ── catálogo ──────────────────────────────────────────────────────────────────────────
    catalogo: dict[str, dict] = {}
    try:
        for f in ("fuentes.yaml", "fuentes_web.yaml"):
            for d in yaml.safe_load((s.config_dir / f).read_text(encoding="utf-8"))["sources"]:
                catalogo[d["doc_id"]] = d
        ok("catálogo", f"{len(catalogo)} documentos")
    except Exception as e:  # noqa: BLE001 — aquí cualquier fallo es el hallazgo
        mal("catálogo", f"no se puede leer: {e}")

    # ── índice ────────────────────────────────────────────────────────────────────────────
    indexados: set[str] = set()
    if not s.index_db_path.exists():
        mal("índice", f"no existe: {s.index_db_path}")
    else:
        con = sqlite3.connect(f"file:{s.index_db_path}?mode=ro", uri=True)
        try:
            indexados = {r[0] for r in con.execute("SELECT DISTINCT doc_id FROM chunks")}
            pasajes = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            ok("índice", f"{len(indexados)} documentos, {pasajes} pasajes")
        finally:
            con.close()

    if catalogo and indexados:
        huerfanos = sorted(indexados - set(catalogo))
        if huerfanos:
            mal(
                "huérfanos",
                f"{len(huerfanos)} indexados sin catálogo (sin licencia): {huerfanos[:4]}",
            )
        else:
            ok("huérfanos", "ninguno; todo lo indexado tiene licencia registrada")

    # ── capa de seguridad ─────────────────────────────────────────────────────────────────
    try:
        reglas = yaml.safe_load((s.config_dir / "red_flags.yaml").read_text(encoding="utf-8"))[
            "rules"
        ]
        sin_fuente = [r["id"] for r in reglas if not r.get("source")]
        rotas = [
            (r["id"], r["source"])
            for r in reglas
            if r.get("source") and catalogo and r["source"] not in catalogo
        ]
        if sin_fuente or rotas:
            mal(
                "alarmas",
                f"{len(reglas)} reglas; sin fuente {sin_fuente}, fuente inexistente {rotas}",
            )
        else:
            ok("alarmas", f"{len(reglas)} reglas, todas con una ficha que existe detrás")
    except Exception as e:  # noqa: BLE001
        mal("alarmas", f"no se pueden leer: {e}")

    # ── dosis: las dos listas de concentraciones ──────────────────────────────────────────
    try:
        from pedibot.bot.dose import DRUGS

        drugs_yaml = yaml.safe_load((s.config_dir / "drugs.yaml").read_text(encoding="utf-8"))[
            "drugs"
        ]
        parejas = {"paracetamol": "paracetamol", "ibuprofen": "ibuprofeno"}
        desajuste = []
        for clave_y, clave_c in parejas.items():
            del_cat = {float(x) for x in drugs_yaml[clave_y]["strengths_mg_per_ml"]}
            de_calc = {p.mg_per_ml for p in DRUGS[clave_c].presentations}
            if del_cat != de_calc:
                desajuste.append(
                    f"{clave_y}: catálogo {sorted(del_cat)} ≠ calculadora {sorted(de_calc)}"
                )
        marcas = sum(len(v.get("brands") or []) for v in drugs_yaml.values())
        if desajuste:
            mal("dosis", "; ".join(desajuste))
        else:
            ok(
                "dosis",
                f"{marcas} marcas, y las concentraciones del catálogo son las que se ofrecen",
            )
    except Exception as e:  # noqa: BLE001
        mal("dosis", f"no se pueden comprobar: {e}")

    # ── emergencias ───────────────────────────────────────────────────────────────────────
    try:
        numeros = yaml.safe_load(
            (s.config_dir / "emergency_numbers.yaml").read_text(encoding="utf-8")
        )
        paises = {k for k in numeros if k != "default"}
        drugs_yaml = yaml.safe_load((s.config_dir / "drugs.yaml").read_text(encoding="utf-8"))[
            "drugs"
        ]
        servidos = {
            c
            for v in drugs_yaml.values()
            for b in (v.get("brands") or [])
            for c in (b.get("countries") or [])
        }
        vacunas = set(yaml.safe_load((s.config_dir / "vaccines.yaml").read_text(encoding="utf-8")))
        faltan = sorted((servidos | {v for v in vacunas if len(v) == 2}) - paises)
        if faltan:
            mal("emergencias", f"países servidos sin número: {faltan}")
        else:
            ok("emergencias", f"{len(paises)} países, y todos los que servimos están")
    except Exception as e:  # noqa: BLE001
        mal("emergencias", f"no se pueden comprobar: {e}")

    # ── cola de publicación ───────────────────────────────────────────────────────────────
    try:
        from pedibot.publish.articles import pending_topics

        contenido = ROOT / "web" / "content"
        cola = {lg: len(pending_topics(contenido, lg)) for lg in LANGS_PUBLICADAS}
        vacias = sorted(lg for lg, n in cola.items() if n == 0)
        if vacias:
            mal("cola", f"sin temas que publicar en {vacias}: el timer correría sin escribir nada")
        else:
            ok("cola", f"{min(cola.values())}–{max(cola.values())} temas por lengua")
        if verbose:
            typer.echo("    " + "  ".join(f"{lg}:{n}" for lg, n in cola.items()))
    except Exception as e:  # noqa: BLE001
        mal("cola", f"no se puede calcular: {e}")

    # ── sitio construido ──────────────────────────────────────────────────────────────────
    dist = ROOT / "web" / "site" / "dist"
    paginas = list(dist.rglob("index.html")) if dist.exists() else []
    if not paginas:
        mal("sitio", "no está construido en esta copia")
    else:
        import datetime as _dt

        cuando = _dt.datetime.fromtimestamp(max(p.stat().st_mtime for p in paginas))
        ok("sitio", f"{len(paginas)} páginas, rehecho {cuando:%Y-%m-%d %H:%M}")

    # ── cómo va respondiendo ────────────────────────────────────────────────────────────
    # No es una comprobación de que algo case: es el pulso. «regenerada» significa que el
    # verificador de citas tiró el primer borrador porque la fuente no lo sostenía, así que
    # es la tasa a la que el modelo se va de la fuente. Medido el 11-sep-2026 sobre 345
    # respuestas: 3 % en castellano y 0 % en francés, contra 17 % en ruso y 12 % en árabe —
    # el verificador trabaja más cuando la respuesta se escribe en un idioma distinto del de
    # la fuente, que es justo lo que pasa siempre en hindi (sin corpus propio).
    try:
        con = sqlite3.connect(f"file:{s.ops_db_path}?mode=ro", uri=True)
        try:
            total = con.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
            veredictos = dict(con.execute("SELECT verification, COUNT(*) FROM answers GROUP BY 1"))
        finally:
            con.close()
        if total:

            def pct(k: str) -> str:
                return f"{100 * veredictos.get(k, 0) / total:.0f} %"

            ok(
                "respuestas",
                f"{total} dadas · con fuente {pct('ok')} · regeneradas {pct('regenerated')} "
                f"· sin fuente {pct('no_source')}",
            )
        else:
            ok("respuestas", "ninguna todavía")
    except Exception as e:  # noqa: BLE001
        ok("respuestas", f"no se pueden leer ({e})")

    # ── clave del modelo (si la hay, nunca cuál) ──────────────────────────────────────────
    tiene = bool(getattr(s, "deepseek_api_key", None) or os.environ.get("DEEPSEEK_API_KEY"))
    ok("modelo", "clave presente" if tiene else "sin clave: sólo responden las herramientas")

    typer.echo("")
    if malas:
        typer.secho(f"DOCTOR-FIN problemas={malas}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.secho("DOCTOR-FIN problemas=0", fg=typer.colors.GREEN)


if __name__ == "__main__":
    logger.disable("pedibot")
    app()
