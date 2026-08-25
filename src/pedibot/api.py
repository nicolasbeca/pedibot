"""FastAPI app: POST /api/ask, POST /api/feedback, GET /api/health, GET /api/stats.

Bind to 127.0.0.1 behind Caddy (PRD §8). The engine is injected so tests can use FakeProvider.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pedibot import __version__
from pedibot.bot.answer import NO_SOURCE, Engine
from pedibot.bot.drugs import DrugCatalog
from pedibot.ops.store import AnswerRecord, OpsStore
from pedibot.settings import ROOT

# Built Astro site when present (make web-build), else the static prototype
STATIC_DIR = (
    (ROOT / "web" / "site" / "dist")
    if (ROOT / "web" / "site" / "dist").exists()
    else ROOT / "web" / "static"
)


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=1500)
    country: str | None = Field(default=None, max_length=2)
    lang: str | None = Field(default=None, pattern="^(es|en)$")
    session: str | None = Field(default=None, max_length=64)


class SourceOut(BaseModel):
    n: int
    citation: str
    url: str | None


class AskOut(BaseModel):
    answer_id: int
    session: str
    lang: str
    level: str
    banner: str | None
    text: str
    sources: list[SourceOut]
    disclaimer: str
    verification: str
    degraded: bool = False


class DoseIn(BaseModel):
    drug: str = Field(min_length=2, max_length=40)
    weight_kg: float = Field(gt=0.5, lt=150)
    age_months: float | None = Field(default=None, ge=0, le=216)
    country: str | None = Field(default=None, max_length=2)
    lang: str = Field(default="en", pattern="^(es|en)$")


class FeedbackIn(BaseModel):
    answer_id: int
    session: str
    value: int = Field(ge=-1, le=1)


@dataclass
class ApiConfig:
    allowed_origins: list[str]
    rate_limit_per_10min: int = 20
    rate_limit_per_day: int = 200
    max_daily_llm_usd: float = 2.0


def create_app(engine: Engine, ops: OpsStore, cfg: ApiConfig) -> FastAPI:
    from pedibot.bot.answer import DISCLAIMER

    app = FastAPI(title="PediBot API", version=__version__, docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.allowed_origins,
        allow_methods=["POST", "GET"],
        allow_headers=["content-type"],
    )

    def client_ip(req: Request) -> str:
        fwd = req.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return req.client.host if req.client else "0.0.0.0"

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "ok": True,
            "version": __version__,
            "index_chunks": engine.retriever.index.size(),
            "prompt": engine.prompt_version,
            "cost_today_usd": round(ops.cost_today_usd(), 4),
        }

    @app.get("/api/stats")
    def stats(days: int = 7) -> dict[str, object]:
        return ops.stats(days=days)

    @app.post("/api/ask", response_model=AskOut)
    def ask(body: AskIn, request: Request) -> AskOut:
        ip = client_ip(request)
        if (
            ops.hit_and_count(ip, 10) > cfg.rate_limit_per_10min
            or ops.count_day(ip) > cfg.rate_limit_per_day
        ):
            raise HTTPException(
                429, "Too many questions from this connection. Please try again later."
            )
        session = body.session or secrets.token_urlsafe(16)
        degraded = ops.cost_today_usd() >= cfg.max_daily_llm_usd
        t0 = time.perf_counter()
        if degraded:
            # spending cap reached: retrieval-only answer (no LLM) — PRD §8 "tope de gasto"
            lang = body.lang or "en"
            hits, _ = engine.retriever.search(body.question, lang)
            from pedibot.bot.answer import Answer

            text = (
                NO_SOURCE[lang]
                if not hits
                else (
                    "Today's answer budget is used up, so here are the relevant guideline passages instead:"
                    if lang == "en"
                    else "El presupuesto de respuestas de hoy se ha agotado; aquí tienes los pasajes relevantes de las guías:"
                )
            )
            sources = [f"[{i}] {h.chunk.citation()}" for i, h in enumerate(hits, 1)]
            a = Answer(
                text,
                "routine",
                None,
                sources,
                lang,
                None,
                None,
                [h.chunk.chunk_id for h in hits],
                "degraded",
            )
        else:
            hist = ops.history(session) if body.session else []
            a = engine.ask(body.question, country=body.country, lang=body.lang, history=hist)
        latency = int((time.perf_counter() - t0) * 1000)
        rec = AnswerRecord(
            session=session,
            lang=a.lang,
            country=body.country,
            question=body.question,
            answer=a.render(),
            level=a.level,
            verification=a.verification,
            chunk_ids=a.chunk_ids,
            prompt_version=a.prompt_version,
            model=a.llm.model if a.llm else None,
            tokens_in=a.llm.tokens_in if a.llm else 0,
            tokens_out=a.llm.tokens_out if a.llm else 0,
            cost_usd=a.llm.cost_usd if a.llm else 0.0,
            latency_ms=latency,
        )
        answer_id = ops.log_answer(rec)
        ops.add_turn(session, "user", body.question)
        ops.add_turn(session, "assistant", a.text)
        out_sources: list[SourceOut] = []
        for s in a.sources:
            n = int(s[1 : s.index("]")])
            url = None
            cit = s[s.index("]") + 2 :]
            if " — http" in cit:
                cit, url = cit.rsplit(" — ", 1)
            out_sources.append(SourceOut(n=n, citation=cit, url=url))
        return AskOut(
            answer_id=answer_id,
            session=session,
            lang=a.lang,
            level=a.level,
            banner=a.banner,
            text=a.text,
            sources=out_sources,
            disclaimer=DISCLAIMER[a.lang],
            verification=a.verification,
            degraded=degraded,
        )

    @app.get("/api/drugs")
    def drugs_list(country: str | None = None, lang: str = "en") -> dict[str, object]:
        cat = engine.drugs
        if cat is None:
            raise HTTPException(503, "drug catalogue not loaded")
        return {
            key: {
                "generic": d.generic.get(lang, d.generic["en"]),
                "brands": [
                    {"name": b.name, "countries": list(b.countries), "forms": list(b.forms)}
                    for b in cat.brands_for(key, country)
                ],
                "notes": d.notes.get(lang, d.notes.get("en", "")),
                "source": d.source,
            }
            for key, d in cat.drugs.items()
        }

    @app.post("/api/dose")
    def dose(body: DoseIn) -> dict[str, object]:
        from pedibot.bot.dose import DoseError, calculate

        cat = engine.drugs
        resolved = cat.resolve(body.drug) if cat else None
        key = resolved[0] if resolved else body.drug.lower()
        try:
            r = calculate(key, body.weight_kg, body.age_months)
        except DoseError as e:
            raise HTTPException(422, str(e)) from e
        brand = resolved[1] if resolved else None
        forms = brand.strengths_mg_per_ml() if brand else []
        if not forms:
            forms = [(p.name, p.mg_per_ml) for p in r.drug.presentations]
        ml_by_form = [
            {
                "form": label,
                "ml_min": round(r.mg_min / mg_ml, 1),
                "ml_max": round(r.mg_max / mg_ml, 1),
            }
            for label, mg_ml in forms
        ]
        info = cat.drugs[key] if cat else None
        return {
            "drug": key,
            "generic": info.generic.get(body.lang, info.generic["en"]) if info else r.drug.name_en,
            "brand": brand.name if brand else None,
            "weight_kg": r.weight_kg,
            "mg_min": r.mg_min,
            "mg_max": r.mg_max,
            "interval_hours": list(r.interval_hours),
            "max_doses_per_day": r.max_doses_per_day,
            "ml_by_form": ml_by_form,
            "refer": r.refer,
            "warnings": r.warnings,
            "notes": info.notes.get(body.lang, "") if info else "",
            "source": r.drug.source,
        }

    @app.post("/api/feedback")
    def feedback(body: FeedbackIn) -> dict[str, bool]:
        ok = ops.set_feedback(body.answer_id, body.session, body.value)
        if not ok:
            raise HTTPException(404, "answer not found for this session")
        return {"ok": True}

    static = STATIC_DIR
    if static.exists():
        app.mount("/", StaticFiles(directory=static, html=True), name="static")
    return app


def app_from_settings() -> FastAPI:
    from pedibot.bot.answer import EmergencyNumbers
    from pedibot.bot.llm import provider_from_settings
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.bot.triage import Triage
    from pedibot.index.store import Index
    from pedibot.ingest.classify import Taxonomy
    from pedibot.settings import get_settings

    s = get_settings()
    llm = provider_from_settings()
    engine = Engine(
        Retriever(
            Index(s.index_db_path),
            Synonyms(s.config_dir / "synonyms.yaml"),
            llm=llm,
            top_k=s.retrieval_top_k,
            taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
        ),
        Triage(s.config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(s.config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(s.config_dir / "drugs.yaml"),
    )
    cfg = ApiConfig(
        allowed_origins=[o.strip() for o in s.allowed_origins.split(",") if o.strip()],
        rate_limit_per_10min=s.rate_limit_per_10min,
        rate_limit_per_day=s.rate_limit_per_day,
        max_daily_llm_usd=s.max_daily_llm_usd,
    )
    return create_app(engine, OpsStore(s.ops_db_path), cfg)
