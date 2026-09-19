"""Las rutas de la cuenta de familia (19-sep-2026).

Todo lo que toca datos de un niño vive aquí y no en `api.py`, por lo mismo que vive en otra base
de datos: para que se pueda leer entero de una sentada y para que nadie añada sin querer una
consulta que no pregunte de quién es el hijo.

La sesión va en una **cookie `HttpOnly`**, no en un `localStorage`: un testigo que JavaScript
puede leer es un testigo que cualquier cosa inyectada en la página puede llevarse, y esto abre
el nombre y la fecha de nacimiento de un niño.

Lo que este módulo NO hace, y está dicho también en la tienda: no verifica el correo ni recupera
contraseñas, porque el proyecto no tiene todavía por dónde mandar un correo. Cuando lo tenga, es
aquí donde se añade.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pedibot.bot.growth import DAYS_PER_MONTH, Growth
from pedibot.family.store import MIN_PASSWORD, FamilyStore
from pedibot.family.vaccines import next_appointment, pending, schedule_for_child, to_ics
from pedibot.settings import ROOT

COOKIE = "pedibot_family"
#: Un año y pico. Quien apunta el peso de su hija una vez al mes no tiene que volver a entrar
#: cada semana, y la cookie se puede cerrar desde el propio sitio.
COOKIE_MAX_AGE = 400 * 24 * 3600


class DoseIn(BaseModel):
    """La visita se identifica por la EDAD a la que toca, no por el nombre de la vacuna.

    El ministerio cambia de producto y el nombre cambia con él; la edad del calendario no. Una
    cartilla guardada por nombre se rompería sola el día que el país pase de pentavalente a
    hexavalente, y con ella el histórico de cada niño.
    """

    age_months: float = Field(ge=0, le=252)
    #: opcional a propósito: quien se acuerda del día lo pone, quien no, marca y sigue
    given_on: str | None = None


class RegisterIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=MIN_PASSWORD, max_length=200)
    lang: str | None = Field(default=None, max_length=5)
    newsletter: bool = False


class LoginIn(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class ChildIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    birth_date: str = Field(min_length=10, max_length=10)
    sex: str | None = Field(default=None, pattern="^[mf]$")
    country: str | None = Field(default=None, max_length=2)


class ChildPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    birth_date: str | None = Field(default=None, min_length=10, max_length=10)
    sex: str | None = Field(default=None, pattern="^[mf]$")
    country: str | None = Field(default=None, max_length=2)


class MeasurementIn(BaseModel):
    date: str = Field(min_length=10, max_length=10)
    weight_kg: float | None = Field(default=None, gt=0, lt=150)
    height_cm: float | None = Field(default=None, gt=20, lt=230)
    head_cm: float | None = Field(default=None, gt=20, lt=80)
    note: str | None = Field(default=None, max_length=200)


class NewsletterIn(BaseModel):
    on: bool


def age_months(birth_date: str, on: dt.date | None = None) -> float:
    """La edad hoy, en meses. Se calcula al preguntar: una edad guardada envejece mal."""
    nacio = dt.date.fromisoformat(birth_date)
    hoy = on or dt.date.today()
    return max(0.0, (hoy - nacio).days / DAYS_PER_MONTH)


def family_router(
    store: FamilyStore, growth: Growth | None = None, max_attempts: int = 10
) -> APIRouter:
    router = APIRouter()
    curvas = growth or Growth(ROOT / "config" / "who_growth.json")

    def quien(token: str | None) -> dict[str, Any]:
        usuario = store.user_for(token or "")
        if usuario is None:
            raise HTTPException(401, "no account")
        return usuario

    def actual(pedibot_family: str | None = Cookie(default=None)) -> dict[str, Any]:
        return quien(pedibot_family)

    # Nota de un intento que no vale, para que nadie lo repita: `Usuario = Annotated[...,
    # Depends(actual)]` aquí dentro NO funciona. Con `from __future__ import annotations`
    # las anotaciones son cadenas y FastAPI las resuelve mirando los globales del módulo,
    # donde un alias local no existe: el parámetro se convierte en una consulta y toda ruta
    # con cuenta contesta 422. Se queda el idioma de siempre, `= Depends(actual)`, que es el
    # mismo que usa `cli.py` con typer y que el proyecto ya declara en su pyproject.

    def _pon_cookie(respuesta: Response, token: str, req: Request) -> None:
        respuesta.set_cookie(
            COOKIE,
            token,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            # en local se prueba por http; en producción Caddy sirve todo por https
            secure=req.url.scheme == "https",
            path="/",
        )

    def _con_edad(hijo: dict[str, Any]) -> dict[str, Any]:
        return {**hijo, "age_months": round(age_months(hijo["birth_date"]), 1)}

    def _percentil(
        sexo: str | None, meses: float, peso: float | None, talla: float | None
    ) -> dict[str, float]:
        """El percentil de ese punto, si se puede. Sin sexo no hay tabla que valga, así que se
        calla en vez de inventarse una."""
        fuera: dict[str, float] = {}
        if not sexo or (peso is None and talla is None):
            return fuera
        try:
            a = curvas.assess(sexo, meses, weight_kg=peso, height_cm=talla)
        except (ValueError, KeyError):
            return fuera
        for ind in a.indicators:
            if ind.name == "wfa":
                fuera["weight_percentile"] = ind.percentile
            elif ind.name == "lhfa":
                fuera["height_percentile"] = ind.percentile
        return fuera

    # ── la cuenta ─────────────────────────────────────────────────────────────────────────────

    @router.post("/api/family/register")
    def register(datos: RegisterIn, req: Request) -> Response:
        try:
            user_id = store.register(datos.email, datos.password, lang=datos.lang)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        if user_id is None:
            # 409 y nada más. Decir «ya existe» es decir quién está dado de alta, pero callarlo
            # del todo impide registrarse a quien simplemente lo olvidó: el 409 sin texto es el
            # término medio que usan casi todos.
            raise HTTPException(409, "already registered")
        if datos.newsletter:
            store.set_newsletter(user_id, True)
        token = store.open_session(user_id)
        r = JSONResponse({"ok": True})
        _pon_cookie(r, token, req)
        return r

    def _ip(req: Request) -> str:
        fwd = req.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return req.client.host if req.client else "0.0.0.0"

    @router.post("/api/family/login")
    def login(datos: LoginIn, req: Request) -> Response:
        # Una contraseña se adivina probando. Diez intentos por cuarto de hora y desde la misma
        # conexión no le estorban a nadie que se haya equivocado dos veces, y le quitan la
        # gracia a quien prueba una lista.
        if store.note_attempt(_ip(req)) > max_attempts:
            raise HTTPException(429, "too many attempts, try again later")
        token = store.login(datos.email, datos.password)
        if token is None:
            # la misma respuesta para «no existe» y para «contraseña mala»
            raise HTTPException(401, "wrong email or password")
        r = JSONResponse({"ok": True})
        _pon_cookie(r, token, req)
        return r

    @router.post("/api/family/logout")
    def logout(pedibot_family: str | None = Cookie(default=None)) -> Response:
        if pedibot_family:
            store.logout(pedibot_family)
        r = JSONResponse({"ok": True})
        r.delete_cookie(COOKIE, path="/")
        return r

    @router.get("/api/family/me")
    def me(usuario: dict[str, Any] = Depends(actual)) -> dict[str, Any]:
        return {
            "email": usuario["email"],
            "lang": usuario["lang"],
            "newsletter": usuario["newsletter"],
            "children": [_con_edad(h) for h in store.children(usuario["id"])],
        }

    @router.post("/api/family/newsletter")
    def newsletter(
        datos: NewsletterIn, usuario: dict[str, Any] = Depends(actual)
    ) -> dict[str, bool]:
        store.set_newsletter(usuario["id"], datos.on)
        return {"ok": True}

    @router.get("/api/family/unsubscribe")
    def unsubscribe(t: str = "") -> dict[str, bool]:
        """Va por GET y sin cookie a propósito: es el enlace del pie de un correo, y quien
        quiere irse no tiene por qué acordarse de su contraseña."""
        return {"ok": store.unsubscribe(t)}

    @router.get("/api/family/export")
    def export(usuario: dict[str, Any] = Depends(actual)) -> Response:
        datos = store.export(usuario["id"])
        return Response(
            json.dumps(datos, ensure_ascii=False, indent=1),
            media_type="application/json",
            headers={"content-disposition": 'attachment; filename="pedibot-mis-datos.json"'},
        )

    @router.delete("/api/family/account")
    def delete_account(usuario: dict[str, Any] = Depends(actual)) -> Response:
        store.delete_account(usuario["id"])
        r = JSONResponse({"ok": True})
        r.delete_cookie(COOKIE, path="/")
        return r

    # ── los hijos ─────────────────────────────────────────────────────────────────────────────

    @router.get("/api/family/children")
    def children(usuario: dict[str, Any] = Depends(actual)) -> list[dict[str, Any]]:
        return [_con_edad(h) for h in store.children(usuario["id"])]

    @router.post("/api/family/children")
    def add_child(datos: ChildIn, usuario: dict[str, Any] = Depends(actual)) -> dict[str, Any]:
        try:
            cid = store.add_child(
                usuario["id"],
                name=datos.name,
                birth_date=datos.birth_date,
                sex=datos.sex,
                country=datos.country,
            )
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        hijo = store.child(usuario["id"], cid)
        assert hijo is not None
        return _con_edad(hijo)

    @router.patch("/api/family/children/{child_id}")
    def update_child(
        child_id: int, datos: ChildPatch, usuario: dict[str, Any] = Depends(actual)
    ) -> dict[str, Any]:
        cambios = {k: v for k, v in datos.model_dump().items() if v is not None}
        try:
            ok = store.update_child(usuario["id"], child_id, **cambios)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        if not ok:
            raise HTTPException(404, "no such child")
        hijo = store.child(usuario["id"], child_id)
        assert hijo is not None
        return _con_edad(hijo)

    @router.delete("/api/family/children/{child_id}")
    def delete_child(child_id: int, usuario: dict[str, Any] = Depends(actual)) -> dict[str, bool]:
        if not store.delete_child(usuario["id"], child_id):
            raise HTTPException(404, "no such child")
        return {"ok": True}

    # ── las medidas ───────────────────────────────────────────────────────────────────────────

    @router.get("/api/family/children/{child_id}/measurements")
    def measurements(
        child_id: int, usuario: dict[str, Any] = Depends(actual)
    ) -> list[dict[str, Any]]:
        hijo = store.child(usuario["id"], child_id)
        if hijo is None:
            raise HTTPException(404, "no such child")
        fuera = []
        for m in store.measurements(usuario["id"], child_id):
            meses = round(age_months(hijo["birth_date"], dt.date.fromisoformat(m["date"])), 1)
            fuera.append(
                {
                    **m,
                    "age_months": meses,
                    **_percentil(hijo.get("sex"), meses, m.get("weight_kg"), m.get("height_cm")),
                }
            )
        return fuera

    @router.get("/api/family/children/{child_id}/vaccines")
    def child_vaccines(
        child_id: int,
        lang: str = "en",
        usuario: dict[str, Any] = Depends(actual),
    ) -> dict[str, Any]:
        """El calendario de su país, con las FECHAS de este niño (19-sep-2026).

        Es el mismo calendario oficial que ya contesta el chat, con su fecha de nacimiento
        sumada. Lo que toca ahora, lo que queda atrás —marcado, no escondido— y lo que viene.
        De aquí saldrán los recordatorios de la app.
        """
        hijo = store.child(usuario["id"], child_id)
        if hijo is None:
            raise HTTPException(404, "no such child")
        puestas = store.doses(usuario["id"], child_id)
        citas = schedule_for_child(hijo, lang=lang, given=puestas)
        return {
            "country": hijo.get("country"),
            "appointments": citas,
            "next": next_appointment(citas),
            # Lo que le tocaba y no consta. Va aparte y no mezclado en la lista porque es la
            # única parte del calendario que pide hacer algo hoy.
            "pending": pending(citas),
        }

    @router.post("/api/family/children/{child_id}/doses", status_code=204)
    def mark_dose(
        child_id: int,
        body: DoseIn,
        usuario: dict[str, Any] = Depends(actual),
    ) -> Response:
        """Marcar una visita del calendario como puesta (20-sep-2026).

        La cartilla de papel se moja, se pierde y se queda en el pueblo. Esta no. Se marca la
        visita entera y no la vacuna suelta, porque una visita es lo que ocurre de verdad: se va
        al centro, se ponen las que tocan ese día y se vuelve.
        """
        if not store.mark_dose(usuario["id"], child_id, body.age_months, body.given_on):
            raise HTTPException(404, "no such child")
        return Response(status_code=204)

    @router.delete("/api/family/children/{child_id}/doses/{age_months}", status_code=204)
    def unmark_dose(
        child_id: int,
        age_months: float,
        usuario: dict[str, Any] = Depends(actual),
    ) -> Response:
        """Desmarcar. Tiene que costar lo mismo que marcar: aquí se falla con el dedo."""
        if store.child(usuario["id"], child_id) is None:
            raise HTTPException(404, "no such child")
        store.unmark_dose(usuario["id"], child_id, age_months)
        return Response(status_code=204)

    @router.get("/api/family/children/{child_id}/vaccines.ics")
    def child_vaccines_ics(
        child_id: int,
        lang: str = "en",
        usuario: dict[str, Any] = Depends(actual),
    ) -> Response:
        """Las citas que vienen, para el calendario del teléfono (19-sep-2026).

        La app avisará con una notificación local. La web no puede programar un aviso para dentro
        de cuatro meses, así que da el dato en el formato que entiende cualquier calendario y que
        avise él. Es la respuesta honesta a esa diferencia.
        """
        hijo = store.child(usuario["id"], child_id)
        if hijo is None:
            raise HTTPException(404, "no such child")
        # con la cartilla delante: lo que ya está puesto no tiene que volver a sonar
        puestas = store.doses(usuario["id"], child_id)
        ics = to_ics(hijo, schedule_for_child(hijo, lang=lang, given=puestas))
        nombre = "".join(ch for ch in str(hijo["name"]) if ch.isalnum()) or "pedibot"
        return Response(
            ics,
            media_type="text/calendar; charset=utf-8",
            headers={"content-disposition": f'attachment; filename="{nombre}-vacunas.ics"'},
        )

    @router.post("/api/family/children/{child_id}/measurements")
    def add_measurement(
        child_id: int,
        datos: MeasurementIn,
        usuario: dict[str, Any] = Depends(actual),
    ) -> dict[str, Any]:
        try:
            mid = store.add_measurement(
                usuario["id"],
                child_id,
                date=datos.date,
                weight_kg=datos.weight_kg,
                height_cm=datos.height_cm,
                head_cm=datos.head_cm,
                note=datos.note,
            )
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        if mid is None:
            raise HTTPException(404, "no such child")
        return {"ok": True, "id": mid}

    @router.delete("/api/family/children/{child_id}/measurements/{measurement_id}")
    def delete_measurement(
        child_id: int,
        measurement_id: int,
        usuario: dict[str, Any] = Depends(actual),
    ) -> dict[str, bool]:
        if not store.delete_measurement(usuario["id"], child_id, measurement_id):
            raise HTTPException(404, "no such measurement")
        return {"ok": True}

    return router
