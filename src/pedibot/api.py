"""FastAPI app: POST /api/ask, POST /api/feedback, GET /api/health, GET /api/stats.

Bind to 127.0.0.1 behind Caddy (PRD §8). The engine is injected so tests can use FakeProvider.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pedibot import __version__
from pedibot.bot.answer import NO_SOURCE, SUPPORTED_LANGS, Engine
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.strings import data_lang
from pedibot.bot.vaccines import Vaccines
from pedibot.ops.store import AnswerRecord, OpsStore
from pedibot.settings import ROOT

# Built Astro site when present (make web-build), else the static prototype
STATIC_DIR = (
    (ROOT / "web" / "site" / "dist")
    if (ROOT / "web" / "site" / "dist").exists()
    else ROOT / "web" / "static"
)


# Built from the engine's own list instead of typed out: this was written "^(es|en|fr)$"
# and silently rejected every request from the German and Russian pages with a 422 —
# the sites were live and their chat answered nothing at all.
_LANG_PATTERN = "^(" + "|".join(SUPPORTED_LANGS) + ")$"


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=1500)
    country: str | None = Field(default=None, max_length=2)
    lang: str | None = Field(default=None, pattern=_LANG_PATTERN)
    session: str | None = Field(default=None, max_length=64)
    mode: str = Field(default="parent", pattern="^(parent|child)$")


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
    options: list[str] = []


class DoseIn(BaseModel):
    drug: str = Field(min_length=2, max_length=40)
    weight_kg: float = Field(gt=0.5, lt=150)
    age_months: float | None = Field(default=None, ge=0, le=216)
    country: str | None = Field(default=None, max_length=2)
    lang: str = Field(default="en", pattern=_LANG_PATTERN)


class PhotoIn(BaseModel):
    image_b64: str = Field(min_length=100, max_length=6_000_000)
    mime: str = Field(default="image/jpeg", pattern="^image/(jpeg|png|webp)$")
    lang: str = Field(default="en", pattern=_LANG_PATTERN)
    country: str | None = Field(default=None, max_length=2)
    session: str | None = Field(default=None, max_length=64)


class ShareIn(BaseModel):
    answer_id: int
    session: str


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


def create_app(engine: Engine, ops: OpsStore, cfg: ApiConfig, vision_fn=None) -> FastAPI:  # type: ignore[no-untyped-def]
    from pedibot.bot.llm import vision_json
    from pedibot.bot.vaccines import format_answer

    vision_fn = vision_fn or vision_json
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
            a = engine.ask(
                body.question, country=body.country, lang=body.lang, history=hist, mode=body.mode
            )
        latency = int((time.perf_counter() - t0) * 1000)
        rec = AnswerRecord(
            session=session,
            lang=a.lang,
            country=body.country,
            question=body.question,
            answer=a.render_debug(),
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
            text=a.clean_text,
            sources=out_sources,
            disclaimer=DISCLAIMER[a.lang],
            verification=a.verification,
            degraded=degraded,
            options=list(getattr(a, "options", [])),
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
                # down, never nearest: rounding up puts the volume above the milligrams
                "ml": int(r.mg / mg_ml * 10) / 10,
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
            "mg": r.mg,
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

    @app.get("/api/vaccines")
    def vaccines(
        country: str = "ES", age_months: float | None = None, lang: str = "en"
    ) -> dict[str, object]:
        v = engine.vaccines
        if v is None:
            raise HTTPException(503, "vaccine schedules not loaded")
        c = v.resolve_country(country)
        if c is None:
            raise HTTPException(404, f"no schedule for {country}; available: {v.countries}")
        due, nxt = v.at_age(c, age_months, lang) if age_months is not None else ([], None)
        return {
            "country": c,
            "meta": v.meta(c, lang),
            "schedule": [s.__dict__ for s in v.schedule(c, lang)],
            "due": [s.__dict__ for s in due],
            "next": nxt.__dict__ if nxt else None,
            "text": format_answer(v, c, age_months, lang),
        }

    @app.post("/api/photo")
    def photo(body: PhotoIn, request: Request) -> dict[str, object]:
        from pedibot.bot.photo import SOURCE, VISION_SYSTEM, interpret, parse
        from pedibot.settings import get_settings

        s = get_settings()
        if not s.photo_enabled or not s.deepseek_api_key:
            raise HTTPException(503, "photo check disabled")
        ip = client_ip(request)
        if ops.hit_and_count(ip, 10) > cfg.rate_limit_per_10min:
            raise HTTPException(429, "Too many requests")
        if ops.cost_today_usd() >= cfg.max_daily_llm_usd:
            raise HTTPException(503, "daily budget reached")
        raw, cost = vision_fn(
            s.deepseek_api_key,
            s.deepseek_base_url,
            s.deepseek_vision_model,
            VISION_SYSTEM,
            body.image_b64,
            body.mime,
        )
        d = parse(raw)
        nums = engine.numbers.get(body.country)
        level, text = interpret(d, body.lang, str(nums["emergency"]))
        session = body.session or secrets.token_urlsafe(16)
        ops.log_answer(
            AnswerRecord(
                session=session,
                lang=body.lang,
                country=body.country,
                question="[photo]",
                answer=text,
                level=level if level != "unsure" else "routine",
                verification="photo",
                chunk_ids=[],
                prompt_version="photo_v1",
                model=s.deepseek_vision_model,
                tokens_in=0,
                tokens_out=0,
                cost_usd=cost,
                latency_ms=0,
            )
        )
        return {"level": level, "text": text, "signs": d, "source": SOURCE, "session": session}

    @app.post("/api/agent/ask")
    def agent_ask(body: AskIn, request: Request) -> dict[str, object]:
        """Machine-to-machine endpoint for Virtuals ACP jobs (idea 10). Same engine, same safety
        checks; returns structured JSON with sources. Auth: X-Api-Key in AGENT_API_KEYS."""
        import os

        keys = {k.strip() for k in os.environ.get("AGENT_API_KEYS", "").split(",") if k.strip()}
        if not keys or request.headers.get("x-api-key") not in keys:
            raise HTTPException(401, "invalid api key")
        a = engine.ask(body.question, country=body.country, lang=body.lang)
        ops.log_answer(
            AnswerRecord(
                session="agent_" + secrets.token_urlsafe(8),
                lang=a.lang,
                country=body.country,
                question=body.question,
                answer=a.render_debug(),
                level=a.level,
                verification=a.verification,
                chunk_ids=a.chunk_ids,
                prompt_version=a.prompt_version,
                model=a.llm.model if a.llm else None,
                tokens_in=a.llm.tokens_in if a.llm else 0,
                tokens_out=a.llm.tokens_out if a.llm else 0,
                cost_usd=a.llm.cost_usd if a.llm else 0.0,
                latency_ms=0,
            )
        )
        return {
            "level": a.level,
            "banner": a.banner,
            "answer": a.clean_text,
            "sources": a.sources,
            "verification": a.verification,
            "lang": a.lang,
            "disclaimer": DISCLAIMER[a.lang],
        }

    @app.get("/api/checklist")
    def checklist(lang: str = "en") -> dict[str, object]:
        import yaml

        from pedibot.settings import get_settings

        raw = yaml.safe_load(
            (get_settings().config_dir / "er_checklist.yaml").read_text(encoding="utf-8")
        )
        pick = lambda node: node[data_lang(node, lang)]  # noqa: E731
        return {
            "source": pick(raw["source_label"]),
            "levels": {k: pick(v) for k, v in raw["levels"].items()},
            "categories": {k: pick(v) for k, v in raw["categories"].items()},
            "items": [
                {"level": i["level"], "cat": i["cat"], "text": i[data_lang(i, lang)]}
                for i in raw["items"]
            ],
        }

    @app.post("/api/share")
    def share(body: ShareIn) -> dict[str, str]:
        token = ops.create_share(body.answer_id, body.session)
        if not token:
            raise HTTPException(404, "answer not found for this session")
        return {"token": token, "path": f"/a/{token}"}

    @app.get("/a/{token}", response_class=HTMLResponse)
    def shared_answer(token: str) -> str:
        d = ops.get_share(token)
        if not d:
            raise HTTPException(404, "not found")
        import html

        lang = str(d["lang"])
        title = "PediBot — shared answer" if lang != "es" else "PediBot — respuesta compartida"
        body_html = html.escape(str(d["answer"])).replace("\n", "<br>")
        q = html.escape(str(d["question"]))
        note = (
            "Shared from PediBot. Information from official paediatric guidelines — not medical advice."
            if lang != "es"
            else "Compartido desde PediBot. Información de guías pediátricas oficiales — no es consejo médico."
        )
        return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>{title}</title>
<style>body{{margin:0;background:#FFFDF9;color:#2B3A35;font-family:"Atkinson Hyperlegible",system-ui,sans-serif;line-height:1.6}}main{{max-width:720px;margin:0 auto;padding:32px 18px}}.q{{background:#E3F4EF;border-radius:18px;padding:14px 18px;margin-bottom:14px}}.a{{background:#fff;border:1px solid #EAE4DA;border-radius:18px;padding:16px 20px;box-shadow:0 10px 30px rgba(43,58,53,.07)}}.n{{color:#8A9992;font-size:.85rem;margin-top:14px}}a{{color:#2F6B57}}</style></head>
<body><main><p><a href="/">← pedibot.xyz</a></p><div class="q">{q}</div><div class="a">{body_html}</div><p class="n">{note}</p></main></body></html>"""

    @app.get("/api/ors")
    def ors(
        age_months: float | None = None, vomiting: bool = False, lang: str = "en"
    ) -> dict[str, object]:
        from pedibot.bot.ors import advise

        a = advise(age_months, vomiting, lang)
        return {
            "age_band": a.age_band,
            "lines": a.lines,
            "warnings": a.warnings,
            "sources": a.sources,
            "refer": a.refer,
        }

    @app.post("/api/feedback")
    def feedback(body: FeedbackIn) -> dict[str, bool]:
        ok = ops.set_feedback(body.answer_id, body.session, body.value)
        if not ok:
            raise HTTPException(404, "answer not found for this session")
        return {"ok": True}

    # operator panel (Caddy basic-auth protects /admin in production)
    from pedibot.admin import make_router

    app.include_router(make_router(lambda: ops.con))

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
        vaccines=Vaccines(s.config_dir / "vaccines.yaml"),
    )
    cfg = ApiConfig(
        allowed_origins=[o.strip() for o in s.allowed_origins.split(",") if o.strip()],
        rate_limit_per_10min=s.rate_limit_per_10min,
        rate_limit_per_day=s.rate_limit_per_day,
        max_daily_llm_usd=s.max_daily_llm_usd,
    )
    return create_app(engine, OpsStore(s.ops_db_path), cfg)
