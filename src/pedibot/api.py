"""FastAPI app: POST /api/ask, POST /api/feedback, GET /api/health, GET /api/stats.

Bind to 127.0.0.1 behind Caddy (PRD §8). The engine is injected so tests can use FakeProvider.
"""

from __future__ import annotations

import re
import secrets
import time
from collections.abc import Mapping
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pedibot import __version__
from pedibot.bot.answer import SUPPORTED_LANGS, Answer, Engine
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.followups import Followups
from pedibot.bot.growth import Growth, load_countries
from pedibot.bot.llm import LLMUnavailable
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


class GuideOut(BaseModel):
    """The guide built from the same sources the answer used. Absent when there is none."""

    title: str
    url: str


#: How many calm questions in a day before mentioning who pays for this. Five is "somebody is
#: really using it", and the line shows on that one and never again — there is no counter to
#: store and no way for it to become a nag.
INVITE_AFTER = 5


def _should_invite(answer: object, ops: object, session: str) -> bool:
    """Whether to put one quiet line about the support page under this answer.

    NEVER on an alarm. A parent whose child has just had a seizure is not asked for money, and
    that is the whole of the rule: everything else here is about not being tiresome.
    """
    if getattr(answer, "level", "routine") != "routine":
        return False
    if getattr(answer, "verification", "") not in (
        "ok",
        "regenerated",
        "dose_calculator",
        "vaccine_schedule",
        "growth_chart",
    ):
        return False
    try:
        return int(ops.answers_today(session)) == INVITE_AFTER  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — a counter is never a reason to fail an answer
        return False


class ToolOut(BaseModel):
    """A page of the site that answers the question better than prose. The web puts the words on
    it: `kind` keeps the eight translations in i18n.ts instead of in the engine."""

    kind: str
    url: str


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
    guide: GuideOut | None = None
    tool: ToolOut | None = None
    #: El número que marcar, sólo con nivel emergencia y país conocido: el cliente lo pinta
    #: como un botón `tel:`. Con la frase de respaldo sin país («112 en la UE, 911 en
    #: América») no se manda nada — sacarle un número sería marcar el equivocado.
    call: str | None = None
    #: Las preguntas que vienen después, en la lengua del padre y según el asunto de la
    #: respuesta. Cada una tiene fuente en el corpus (config/followups.yaml y su prueba).
    #: Vacío sin fuente o con nivel emergencia: ahí el padre tiene que estar llamando.
    followups: list[str] = []
    #: Fiebre sin edad: se ha respondido, y el chat ofrece los botones de edad debajo.
    ask_age: bool = False
    #: True exactly once, on a calm fifth question of the day: an invitation to the support page.
    #: Never on an answer with a warning sign — see `_should_invite`.
    invite: bool = False


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


def _ml(mg: float, mg_per_ml: float) -> float:
    """Mililitros a partir de miligramos, SIEMPRE hacia abajo.

    Nunca al más cercano: redondear hacia arriba pone en la jeringa más volumen del que justifican
    los miligramos. Medido el 6-sep-2026, cuando los extremos de la banda usaban `round()` y 277
    de 710 subían — en un bebé de 5 kg con gotas de 100 mg/ml la web enseñaba 0,8 ml donde el
    exacto era 0,75, es decir 16 mg/kg contra los 15 del techo.

    Hacia abajo se queda corto por centésimas, y quedarse corto con un antitérmico no hace daño.
    """
    return int(mg / mg_per_ml * 10) / 10


_MARCABLE = re.compile(r"\d{2,6}")


def dialable(numbers: Mapping[str, object], country: str | None, known: set[str]) -> str | None:
    """El primer número marcable del país, o nada si no hay país o el país no está."""
    if not country or country.upper() not in known:
        return None
    m = _MARCABLE.search(str(numbers.get("emergency") or ""))
    return m.group(0) if m else None


def next_questions(engine: Engine, table: Followups, question: str, a: Answer) -> list[str]:
    """Sólo bajo una respuesta con fuente y sin alarma, y nunca la que el padre acaba de hacer."""
    if a.verification not in ("ok", "regenerated") or a.level == "emergency":
        return []
    tax = getattr(engine.retriever, "taxonomy", None)
    if tax is None:
        return []
    topic = tax.topic_for(question + " " + " ".join(a.expansion))
    return table.for_topic(topic, a.lang, asked=question)


def create_app(engine: Engine, ops: OpsStore, cfg: ApiConfig, vision_fn=None) -> FastAPI:  # type: ignore[no-untyped-def]
    from pedibot.bot.llm import vision_json
    from pedibot.bot.vaccines import format_answer

    vision_fn = vision_fn or vision_json
    followups = Followups(ROOT / "config" / "followups.yaml")
    _growth = Growth(ROOT / "config" / "who_growth.json")
    _growth_countries = load_countries(ROOT / "config" / "growth_charts.yaml")
    from pedibot.bot.answer import DISCLAIMER

    app = FastAPI(title="PediBot API", version=__version__, docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.allowed_origins,
        allow_methods=["POST", "GET"],
        allow_headers=["content-type", "x-pedibot-client"],
    )

    def client_source(req: Request) -> str:
        """Who is asking, for the panel — never for the answer, which is the same for everybody.

        Our own chat sends `x-pedibot-client: web` and our scripts send `test`. Anything else
        gets `unknown`, INCLUDING a request with no header at all: the front end always sends it,
        so an anonymous POST is not the front end. That direction is deliberate — the panel would
        rather miss a reader than show the operator his own tests as parents. Nothing here changes
        what gets answered, so a wrong header costs nobody an answer.
        """
        v = (req.headers.get("x-pedibot-client") or "").strip().lower()
        return v if v in ("web", "test") else "unknown"

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

    @app.post("/api/team", status_code=204)
    async def team(request: Request) -> Response:
        """Un navegador que abrió /admin avisa desde cada página: lo suyo no es de un lector.

        Reetiqueta su sesión (ver `OpsStore.mark_team_session`) y, al llegar con la cabecera
        `test`, deja su IP marcada en el registro del servidor para el contador de visitas. Un
        desconocido que lo llame sólo consigue esconderse a sí mismo: las sesiones son aleatorias
        y no se pueden adivinar las de otro.
        """
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 — cuerpo vacío o no JSON: nada que reetiquetar
            body = {}
        session = body.get("session") if isinstance(body, dict) else None
        if isinstance(session, str) and 0 < len(session) <= 64:
            ops.mark_team_session(session)
        return Response(status_code=204)

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
            a = engine.answer_without_model(body.question, body.country, body.lang, "degraded")
        else:
            hist = ops.history(session) if body.session else []
            try:
                a = engine.ask(
                    body.question,
                    country=body.country,
                    lang=body.lang,
                    history=hist,
                    mode=body.mode,
                )
            except LLMUnavailable:
                # DeepSeek caído, lento o sin saldo. Hasta el 7-sep-2026 esto salía como un 500 y
                # el padre veía «algo ha fallado por nuestra parte»: se tiraba a la basura un
                # triaje ya hecho y unos pasajes ya recuperados, y ni siquiera quedaba registrado,
                # así que no había forma de saber cuántas veces pasaba. Se contesta como sin
                # presupuesto, pero con OTRA etiqueta: aquello lo decidimos nosotros, esto es una
                # avería y tiene que poder contarse aparte.
                a = engine.answer_without_model(body.question, body.country, body.lang, "no_model")
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
            source=client_source(request),
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
            invite=_should_invite(a, ops, session),
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
            guide=GuideOut(title=a.guide.title, url=a.guide.url) if a.guide else None,
            tool=ToolOut(kind=a.tool.kind, url=a.tool.url) if a.tool else None,
            call=(
                dialable(
                    engine.numbers.get(body.country, a.lang),
                    body.country,
                    {c for c in engine.numbers.raw if c != "default"},
                )
                if a.level == "emergency"
                else None
            ),
            followups=next_questions(engine, followups, body.question, a),
            ask_age=a.ask_age,
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
        from pedibot.bot.dose import DoseError, calculate, presentation_label
        from pedibot.bot.strings import tool_strings

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
                "form": presentation_label(label, body.lang),
                "ml": _ml(r.mg, mg_ml),
                "ml_min": _ml(r.mg_min, mg_ml),
                "ml_max": _ml(r.mg_max, mg_ml),
            }
            for label, mg_ml in forms
        ]
        info = cat.drugs[key] if cat else None
        # Cuando el fármaco no es para este niño, la respuesta no lleva la cifra. Decisión del
        # operador (8-sep-2026): la web enseñaba «50 mg» en grande y la tabla de mililitros, y
        # DEBAJO el «no dar sin consultar» — para el ibuprofeno en un bebé de dos meses, que su
        # propia ficha excluye. Se dice por qué no, y de dónde sale; no se dice cuánto.
        #
        # Las claves siguen ahí, en nulo: quien ya leía `mg` no se encuentra un KeyError, se
        # encuentra un «no hay cifra», que es la verdad.
        T = tool_strings(body.lang)
        return {
            "drug": key,
            "generic": info.generic.get(body.lang, info.generic["en"])
            if info
            else r.drug.names.get(body.lang, r.drug.names["en"]),
            "brand": brand.name if brand else None,
            "weight_kg": r.weight_kg,
            "mg": None if r.refer else r.mg,
            "mg_min": None if r.refer else r.mg_min,
            "mg_max": None if r.refer else r.mg_max,
            "interval_hours": list(r.interval_hours),
            "max_doses_per_day": r.max_doses_per_day,
            "ml_by_form": [] if r.refer else ml_by_form,
            "refer": r.refer,
            "warnings": r.warnings,
            # los mismos avisos en el idioma del lector. La web enseñaba los identificadores
            # internos tal cual — «⚠️ Do not give without medical advice: under_3_months_refer,
            # below_min_age» — en los ocho idiomas, teniendo las ocho traducciones a mano.
            "warnings_text": [T["dose_warn"].get(w, w) for w in r.warnings],
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
        from pedibot.bot.photo import SOURCE, VISION_SYSTEM, interpret, parse, signs_seen
        from pedibot.settings import get_settings

        s = get_settings()
        if not s.photo_enabled or not s.deepseek_api_key:
            raise HTTPException(503, "photo check disabled")
        ip = client_ip(request)
        if ops.hit_and_count(ip, 10) > cfg.rate_limit_per_10min:
            raise HTTPException(429, "Too many requests")
        if ops.cost_today_usd() >= cfg.max_daily_llm_usd:
            raise HTTPException(503, "daily budget reached")
        try:
            raw, cost = vision_fn(
                s.deepseek_api_key,
                s.deepseek_base_url,
                s.deepseek_vision_model,
                VISION_SYSTEM,
                body.image_b64,
                body.mime,
            )
        except LLMUnavailable:
            # Aquí no hay respuesta de reserva que dar: sin modelo de visión no hay lectura de la
            # foto, y no vamos a inventarla. Pero es un 503 («ahora no puedo, inténtalo luego»),
            # no un 500 («se nos ha roto algo»), que es lo que salía hasta el 7-sep-2026.
            raise HTTPException(503, "photo check unavailable right now") from None
        d = parse(raw)
        # con el idioma: sin país elegido la "cifra" es una frase, y una frase tiene idioma.
        # Hasta el 8-sep-2026 esta llamada era la única de las cuatro que no lo pasaba, así
        # que la lectura de una foto en alemán terminaba en «...rufen Sie your local
        # emergency number an» — el fallo que EmergencyNumbers.get documenta como arreglado.
        nums = engine.numbers.get(body.country, body.lang)
        # sin str(): en un país sin número nacional esto convertía None en la cadena
        # "None" y la metía en la frase que lee el padre (18-sep-2026).
        numero = nums["emergency"]
        level, text = interpret(d, body.lang, numero if numero else None)
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
                source=client_source(request),
            )
        )
        # La foto queda escrita en la conversación, con lo que se vio. Sin esto, el mensaje
        # siguiente del padre —«no desaparecen cuando aprieto», que es la respuesta a lo que le
        # acabamos de pedir— llegaba sin contexto, y solo es rutina.
        vistos = signs_seen(d, body.lang)
        ops.add_turn(session, "user", "[foto] " + vistos if vistos else "[foto]")
        ops.add_turn(session, "assistant", text)
        return {"level": level, "text": text, "signs": d, "source": SOURCE, "session": session}

    @app.post("/api/agent/ask")
    def agent_ask(body: AskIn, request: Request) -> dict[str, object]:
        """Machine-to-machine endpoint for Virtuals ACP jobs (idea 10). Same engine, same safety
        checks; returns structured JSON with sources. Auth: X-Api-Key in AGENT_API_KEYS.

        Lo de «same safety checks» era falso hasta el 7-sep-2026: este camino ni miraba el tope de
        gasto del día ni sobrevivía a una avería del modelo. Es el TERCER frente con el mismo
        agujero (L38) y el más fácil de olvidar, porque no lo usa una persona.

        El tope se aplica aquí también, y no es obvio: el comprador paga el trabajo, así que se
        podría argumentar que su gasto no debería contar. Se aplica porque el saldo de DeepSeek es
        uno solo — si un comprador (o un fallo suyo) lo agota, quien se queda sin respuesta es un
        padre. Primero el padre."""
        import os

        keys = {k.strip() for k in os.environ.get("AGENT_API_KEYS", "").split(",") if k.strip()}
        if not keys or request.headers.get("x-api-key") not in keys:
            raise HTTPException(401, "invalid api key")
        if ops.cost_today_usd() >= cfg.max_daily_llm_usd:
            a = engine.answer_without_model(body.question, body.country, body.lang, "degraded")
        else:
            try:
                # el modo niño viaja también desde un agente: «child_friendly_health_explanation»
                a = engine.ask(body.question, country=body.country, lang=body.lang, mode=body.mode)
            except LLMUnavailable:
                a = engine.answer_without_model(body.question, body.country, body.lang, "no_model")
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
                source="agent",
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
            "guide": {"title": a.guide.title, "url": a.guide.url} if a.guide else None,
            "tool": {"kind": a.tool.kind, "url": a.tool.url} if a.tool else None,
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

    #: El envoltorio de una respuesta compartida, en los ocho idiomas. Estaba escrito
    #: `"…" if lang != "es" else "…"`, la forma exacta que el candado del i18n prohíbe en la web:
    #: seis de los ocho idiomas recibían la rama inglesa. Un padre alemán compartía su respuesta
    #: en alemán envuelta en un título y una nota legal en inglés (8-sep-2026).
    SHARED = {
        "en": (
            "PediBot — shared answer",
            "Shared from PediBot. Information from official paediatric guidelines — not medical advice.",
        ),
        "es": (
            "PediBot — respuesta compartida",
            "Compartido desde PediBot. Información de guías pediátricas oficiales — no es consejo médico.",
        ),
        "fr": (
            "PediBot — réponse partagée",
            "Partagé depuis PediBot. Information issue de recommandations pédiatriques officielles — ce n'est pas un avis médical.",
        ),
        "de": (
            "PediBot — geteilte Antwort",
            "Geteilt über PediBot. Information aus offiziellen kinderärztlichen Leitlinien — keine medizinische Beratung.",
        ),
        "ru": (
            "PediBot — ответ, которым поделились",
            "Отправлено из PediBot. Информация из опубликованных педиатрических рекомендаций — не медицинская консультация.",
        ),
        "ar": (
            "PediBot — إجابة تمت مشاركتها",
            "تمت المشاركة من PediBot. معلومات مأخوذة من إرشادات طب الأطفال المنشورة — وليست استشارة طبية.",
        ),
        "pt": (
            "PediBot — resposta partilhada",
            "Partilhado a partir do PediBot. Informação de diretrizes pediátricas oficiais — não é aconselhamento médico.",
        ),
        "hi": (
            "PediBot — साझा किया गया उत्तर",
            "PediBot से साझा किया गया। प्रकाशित बाल रोग दिशानिर्देशों से जानकारी — यह चिकित्सकीय सलाह नहीं है।",
        ),
    }

    @app.get("/a/{token}", response_class=HTMLResponse)
    def shared_answer(token: str) -> str:
        d = ops.get_share(token)
        if not d:
            raise HTTPException(404, "not found")
        import html

        lang = str(d["lang"])
        title, note = SHARED.get(lang, SHARED["en"])
        # El árabe se lee de derecha a izquierda. La web lo sabe desde el primer día
        # (`dirFor(lang)` en Base.astro) y esta página, que es HTML escrito a mano aparte, no:
        # una respuesta árabe compartida salía maquetada al revés.
        direction = "rtl" if lang == "ar" else "ltr"
        body_html = html.escape(str(d["answer"])).replace("\n", "<br>")
        q = html.escape(str(d["question"]))
        return f"""<!doctype html><html lang="{lang}" dir="{direction}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>{title}</title>
<style>body{{margin:0;background:#FFFDF9;color:#2B3A35;font-family:"Atkinson Hyperlegible",system-ui,sans-serif;line-height:1.6}}main{{max-width:720px;margin:0 auto;padding:32px 18px}}.q{{background:#E3F4EF;border-radius:18px;padding:14px 18px;margin-bottom:14px}}.a{{background:#fff;border:1px solid #EAE4DA;border-radius:18px;padding:16px 20px;box-shadow:0 10px 30px rgba(43,58,53,.07)}}.n{{color:#8A9992;font-size:.85rem;margin-top:14px}}a{{color:#2F6B57}}</style></head>
<body><main><p><a href="/">← pedibot.xyz</a></p><div class="q">{q}</div><div class="a">{body_html}</div><p class="n">{note}</p></main></body></html>"""

    @app.get("/api/growth")
    def growth(
        sex: str = Query(pattern="^[mfMF]$"),
        age_months: float = Query(ge=0, le=240),
        weight_kg: float | None = Query(default=None, gt=0.5, lt=200),
        height_cm: float | None = Query(default=None, gt=30, lt=220),
        lang: str = Query(default="en", pattern=_LANG_PATTERN),
        country: str | None = Query(default=None, min_length=2, max_length=2),
    ) -> dict[str, object]:
        """La curva de crecimiento, calculada: sin modelo y sin guardar nada (13-sep-2026).

        Con país, la tabla es la que usa su cartilla cuando PediBot la tiene (Estados Unidos: el
        CDC desde los 2 años) y la respuesta dice cuál usa el país, para que el padre sepa si el
        percentil es comparable con el de su cartilla.
        """
        from pedibot.bot.growth import describe

        pais = _growth_countries.get((country or "").upper())
        reference = str(pais["calculator"]) if pais else "who"
        try:
            a = _growth.assess(sex, age_months, weight_kg, height_cm, reference=reference)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        out = describe(a, lang)
        out["reference"] = reference
        if pais:
            out["country"] = {
                "code": (country or "").upper(),
                "match": pais["match"],
                "body": pais["body"],
                "source": pais["source"],
                "charts": pais["charts"],
            }
        return out

    # ── para agentes (y para quien quiera): lo que PediBot ya hace sin modelo (13-sep-2026) ──
    @app.get("/api/growth/countries")
    def growth_countries() -> dict[str, object]:
        """Qué tabla de crecimiento usa la cartilla de cada país, con su fuente oficial."""
        return {"countries": _growth_countries}

    @app.get("/api/triage")
    def triage_check(
        text: str = Query(min_length=2, max_length=1500),
        lang: str = Query(default="en", pattern=_LANG_PATTERN),
        country: str | None = Query(default=None, min_length=2, max_length=2),
    ) -> dict[str, object]:
        """Los signos de alarma de un texto, con las reglas fijas del triaje: sin modelo.

        Lo mismo que corre antes de cada respuesta del chat, expuesto solo: el nivel, qué regla saltó
        y con qué ficha, el aviso en la lengua pedida y el número que marcar si el país se conoce.
        """
        from pedibot.bot.answer import build_banner

        tr = engine.triage.assess(text)
        nums = engine.numbers.get(country, lang)
        motivos = tr.reasons(lang)
        return {
            "level": tr.level,
            "rules": [
                {"id": r.id, "level": r.level, "reason": motivos[i], "source": r.source}
                for i, r in enumerate(tr.matched)
            ],
            "banner": build_banner(tr, lang, nums),
            "call": (
                dialable(nums, country, {c for c in engine.numbers.raw if c != "default"})
                if tr.level == "emergency"
                else None
            ),
            "numbers": nums,
            "age_months": tr.age_months,
            "disclaimer": DISCLAIMER.get(lang, DISCLAIMER["en"]),
        }

    @app.get("/api/emergency-numbers")
    def emergency_numbers(
        country: str | None = Query(default=None, min_length=2, max_length=2),
        lang: str = Query(default="en", pattern=_LANG_PATTERN),
    ) -> dict[str, object]:
        """El número de emergencias de un país; sin país, la lista de países que se conocen."""
        conocidos = sorted(c for c in engine.numbers.raw if c != "default")
        if not country:
            return {"countries": conocidos}
        c = country.upper()
        if c not in conocidos:
            raise HTTPException(404, f"no numbers for {c}; known: {conocidos}")
        return {"country": c, "numbers": engine.numbers.get(c, lang)}

    @app.get("/api/guides")
    def guides_search(
        q: str = Query(min_length=2, max_length=200),
        lang: str = Query(default="en", pattern=_LANG_PATTERN),
        limit: int = Query(default=5, ge=1, le=10),
    ) -> dict[str, object]:
        """Las guías publicadas de un tema, en la lengua pedida, con su dirección."""
        idx = engine.guides
        if idx is None:
            raise HTTPException(503, "guides not loaded")
        return {
            "guides": [
                {"title": g.title, "topic": g.topic, "url": f"https://pedibot.xyz{g.url}"}
                for g in idx.search(q, lang, limit)
            ]
        }

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
    from pedibot.bot.guides import GuideIndex
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
            Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
            llm=llm,
            top_k=s.retrieval_top_k,
            taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
        ),
        Triage(s.config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(s.config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(s.config_dir / "drugs.yaml"),
        vaccines=Vaccines(s.config_dir / "vaccines.yaml"),
        growth=Growth(s.config_dir / "who_growth.json"),
        guides=GuideIndex(s.content_dir),
    )
    cfg = ApiConfig(
        allowed_origins=[o.strip() for o in s.allowed_origins.split(",") if o.strip()],
        rate_limit_per_10min=s.rate_limit_per_10min,
        rate_limit_per_day=s.rate_limit_per_day,
        max_daily_llm_usd=s.max_daily_llm_usd,
    )
    return create_app(engine, OpsStore(s.ops_db_path), cfg)
