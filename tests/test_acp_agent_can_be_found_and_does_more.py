"""El agente ACP no había hecho ni un trabajo, y no era por falta de ofertas (13-sep-2026).

Revisado a petición del operador: desde el 26-ago el trabajador ha visto **cero trabajos** (su
estado está vacío, el mercado devuelve `{"jobs":[]}` y el registro sólo tiene arranques y
esperas agotadas). Y al buscar en el mercado «pediatric», «paediatric», «child health», «medical»,
«health» —o el propio nombre, «PediBot»— no aparecía. La causa, leída en el código del SDK: la
presencia de un agente es un **socket con latido** (`acp events listen`); el trabajador sólo
preguntaba por REST cada 30 s, así que el mercado lo tenía con `lastActiveAt: None` y la búsqueda no
lo listaba nunca. Con `events listen` abierto un minuto pasó a `2999-12-31`, la marca de «en línea».

Esto fija tres cosas:

1. **Presencia**: el trabajador mantiene `acp events listen` abierto y lo relanza si se cae; y se
   detiene limpio (cada despliegue dejaba un traceback de `KeyboardInterrupt` como «Failed»).
2. **Lo que se ofrece estaba viejo** (vacunas de 3 países con 8 publicados, 4 lenguas con 8, 214
   fuentes con 480): el catálogo pasa a un fichero versionado y comprobado.
3. **Servicios nuevos**, todos de lo que PediBot ya hace sin modelo: percentiles por país,
   comprobación de signos de alarma, números de emergencia, guías por tema, explicación para el niño
   y vacunas que tocan a una edad.
"""

from __future__ import annotations

import importlib.util
import json
import sys

import pytest

from pedibot.settings import ROOT

LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


def _worker():
    spec = importlib.util.spec_from_file_location("acp_worker", ROOT / "ops" / "acp_worker.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    sys.modules["acp_worker"] = m
    spec.loader.exec_module(m)
    return m


# ── 1. presencia ──────────────────────────────────────────────────────────────────────────
class _Proc:
    def __init__(self, vivo: bool):
        self.vivo = vivo

    def poll(self):
        return None if self.vivo else 1


def test_si_el_oyente_se_cae_se_relanza():
    w = _worker()
    lanzados = []

    def lanzar():
        lanzados.append(1)
        return _Proc(True)

    p = w.ensure_listener(None, lanzar)
    assert lanzados == [1] and p.poll() is None
    p2 = w.ensure_listener(p, lanzar)
    assert p2 is p and lanzados == [1], "con el oyente vivo no se lanza otro"
    p3 = w.ensure_listener(_Proc(False), lanzar)
    assert lanzados == [1, 1] and p3.poll() is None, "muerto, se relanza"


def test_el_oyente_es_events_listen_a_un_fichero():
    w = _worker()
    cmd = w.listener_command()
    assert cmd[:3] == ["acp", "events", "listen"] and "--output" in cmd
    assert "--all" not in cmd and "--legacy" not in cmd, (
        "--all se cuelga con la política restricted"
    )


def test_se_detiene_limpio():
    src = (ROOT / "ops" / "acp_worker.py").read_text(encoding="utf-8")
    assert "except KeyboardInterrupt" in src, "cada despliegue deja un traceback y un «Failed»"


# ── 3. el enrutado de los formularios nuevos ──────────────────────────────────────────────
def test_sexo_edad_y_medidas_van_a_la_curva_no_al_suero():
    w = _worker()
    r = w.route(
        {
            "sex": "f",
            "age_months": 30,
            "weight_kg": 12,
            "height_cm": 90,
            "country": "IN",
            "lang": "hi",
        }
    )
    assert (
        r and r.path.startswith("/api/growth?") and "country=IN" in r.path and "lang=hi" in r.path
    )
    solo_peso = w.route({"weight_kg": 12})
    assert solo_peso and solo_peso.path.startswith("/api/ors"), (
        "sin sexo sigue siendo el suero oral"
    )


def test_los_sintomas_van_al_triaje_sin_modelo():
    w = _worker()
    r = w.route({"symptoms": "my baby is not breathing properly", "country": "SA", "lang": "ar"})
    assert r and r.path.startswith("/api/triage?") and "country=SA" in r.path


def test_un_tema_va_a_las_guias():
    w = _worker()
    r = w.route({"topic": "fever", "lang": "es"})
    assert r and r.path.startswith("/api/guides?")


def test_la_explicacion_para_el_nino_pasa_el_modo():
    w = _worker()
    r = w.route({"question": "why do I have a fever?", "mode": "child", "lang": "en"})
    assert r and r.path == "/api/agent/ask" and r.payload["mode"] == "child"
    normal = w.route({"question": "fever in a 2 year old"})
    assert normal and normal.payload.get("mode", "parent") == "parent"


def test_las_vacunas_por_edad_pasan_la_edad():
    w = _worker()
    r = w.route({"country": "IN", "age_months": 9, "lang": "hi"})
    assert r and r.path.startswith("/api/vaccines?") and "age_months=9" in r.path


# ── 3. los endpoints nuevos ───────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    from fastapi.testclient import TestClient

    from pedibot.api import ApiConfig, create_app
    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.guides import GuideIndex
    from pedibot.bot.llm import FakeProvider
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.bot.triage import Triage
    from pedibot.index.store import Index
    from pedibot.ingest.classify import Taxonomy
    from pedibot.ops.store import OpsStore

    c = ROOT / "config"
    llm = FakeProvider("La fiebre no es peligrosa por sí misma, según la SEUP [1].")
    engine = Engine(
        Retriever(
            Index(ROOT / "index/pedibot.db"),
            Synonyms(c / "synonyms.yaml", c / "drugs.yaml"),
            taxonomy=Taxonomy(c / "taxonomia.yaml"),
        ),
        Triage(c / "red_flags.yaml"),
        llm,
        EmergencyNumbers(c / "emergency_numbers.yaml"),
        guides=GuideIndex(ROOT / "web" / "content"),
    )
    tmp = tmp_path_factory.mktemp("acp")
    app = create_app(
        engine,
        OpsStore(tmp / "o.db", salt="s"),
        ApiConfig(allowed_origins=["http://x"], rate_limit_per_10min=1000, rate_limit_per_day=1000),
    )
    return TestClient(app), llm


def test_triaje_emergencia_con_el_numero_del_pais(cliente):
    c, llm = cliente
    antes = len(llm.calls)
    j = c.get(
        "/api/triage",
        params={"text": "ابني لا يتنفس جيدا وشفتاه زرقاوان", "lang": "ar", "country": "SA"},
    ).json()
    assert j["level"] == "emergency"
    assert j["call"] == "997"
    assert j["rules"] and all(r["reason"] and r["source"] for r in j["rules"])
    assert j["banner"] and j["disclaimer"]
    assert len(llm.calls) == antes, "el triaje no puede tocar el modelo"


def test_triaje_rutina(cliente):
    c, _ = cliente
    j = c.get("/api/triage", params={"text": "mi hijo tiene mocos", "lang": "es"}).json()
    assert j["level"] == "routine" and j["rules"] == [] and j["banner"] is None


def test_numeros_de_emergencia(cliente):
    c, _ = cliente
    j = c.get("/api/emergency-numbers", params={"country": "IN"}).json()
    assert j["country"] == "IN" and "112" in str(j["numbers"]["emergency"])
    todos = c.get("/api/emergency-numbers").json()
    assert len(todos["countries"]) >= 35 and "SA" in todos["countries"]


def test_guias_por_tema(cliente):
    c, _ = cliente
    j = c.get("/api/guides", params={"q": "fiebre", "lang": "es"}).json()
    assert j["guides"], "ninguna guía de fiebre en castellano"
    g = j["guides"][0]
    assert g["url"].startswith("https://pedibot.xyz/es/guides/") and g["title"]
    assert len(j["guides"]) <= 5


def test_tablas_de_crecimiento_por_pais(cliente):
    c, _ = cliente
    j = c.get("/api/growth/countries").json()
    assert len(j["countries"]) >= 21 and j["countries"]["US"]["calculator"] == "cdc"


def test_la_respuesta_para_agentes_acepta_el_modo_nino(cliente, monkeypatch):
    c, llm = cliente
    monkeypatch.setenv("AGENT_API_KEYS", "k")
    r = c.post(
        "/api/agent/ask",
        json={
            "question": "mi hijo de 6 años tiene fiebre, ¿por qué?",
            "lang": "es",
            "mode": "child",
        },
        headers={"x-api-key": "k"},
    )
    assert r.status_code == 200
    assert "EXPLAIN TO THE CHILD" in llm.calls[-1][1], "el modo niño no llega al motor"


# ── 2. el catálogo versionado ─────────────────────────────────────────────────────────────
CATALOGO = ROOT / "ops" / "acp_catalogue.json"


@pytest.fixture(scope="module")
def catalogo() -> dict:
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


def test_estan_los_trabajos_de_siempre_y_los_nuevos(catalogo: dict):
    nombres = {o["name"] for o in catalogo["offerings"]}
    assert {
        "paediatric_question_with_sources",
        "child_medicine_dose",
        "childhood_vaccination_schedule",
        "oral_rehydration_plan",
        "child_growth_percentile",
        "paediatric_warning_sign_check",
        "child_friendly_health_explanation",
        "paediatric_guide_finder",
    } <= nombres


def test_cada_oferta_se_lee_entera(catalogo: dict):
    """El mercado marca en amarillo lo que no tiene descripción, y es lo único que lee un comprador."""
    for o in catalogo["offerings"] + catalogo["resources"]:
        assert 40 <= len(o["description"]) <= 500, (o["name"], len(o["description"]))
        esquemas = [o.get("requirements"), o.get("deliverable"), o.get("params")]
        for s in [e for e in esquemas if e]:
            assert s.get("description"), (o["name"], "esquema sin descripción")
            for k, p in (s.get("properties") or {}).items():
                assert p.get("description"), (o["name"], k, "propiedad sin descripción")


def test_las_ocho_lenguas_en_cada_formulario(catalogo: dict):
    for o in catalogo["offerings"]:
        lang = (o["requirements"].get("properties") or {}).get("lang")
        assert lang and lang.get("enum") == list(LANGS), (o["name"], lang)


def test_nada_viejo_en_las_descripciones(catalogo: dict):
    texto = json.dumps(catalogo)
    for viejo in (
        "214 entries",
        "en, es, fr or de",
        "Spain (Ministerio de Sanidad 2025), the United Kingdom (NHS) and the United States (CDC 2025)",
    ):
        assert viejo not in texto, viejo


def test_los_numeros_del_catalogo_son_los_de_verdad(catalogo: dict):
    import yaml

    vac = yaml.safe_load((ROOT / "config/vaccines.yaml").read_text(encoding="utf-8"))["countries"]
    g = yaml.safe_load((ROOT / "config/growth_charts.yaml").read_text(encoding="utf-8"))[
        "countries"
    ]
    por_nombre = {o["name"]: o for o in catalogo["offerings"] + catalogo["resources"]}
    assert f"{len(vac)} countries" in por_nombre["childhood_vaccination_schedule"]["description"]
    assert f"{len(g)} countries" in por_nombre["child_growth_percentile"]["description"]


def test_precios_en_el_suelo(catalogo: dict):
    assert all(o["price"] == 0.01 for o in catalogo["offerings"])


def test_el_trabajador_sabe_servir_cada_formulario(catalogo: dict):
    """Una oferta que el trabajador no sabe enrutar es un cobro sin entrega."""
    w = _worker()
    for o in catalogo["offerings"]:
        ejemplo = o["example"]
        assert w.route(ejemplo) is not None, (o["name"], ejemplo)


# ── la sincronización con el mercado ──────────────────────────────────────────────────────
def _sync():
    spec = importlib.util.spec_from_file_location("acp_sync", ROOT / "ops" / "acp_sync.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    sys.modules["acp_sync"] = m
    spec.loader.exec_module(m)
    return m


def test_la_sincronizacion_actualiza_lo_que_hay_y_crea_lo_que_falta(catalogo: dict):
    s = _sync()
    vivos = [
        {"id": "o1", "name": "paediatric_question_with_sources"},
        {"id": "o2", "name": "child_medicine_dose"},
    ]
    recursos = [{"name": "paediatric_source_catalogue"}, {"name": "emergency_numbers_by_country"}]
    p = s.plan(catalogo, vivos, recursos)
    assert {n for _, n in [(i, o["name"]) for i, o in p.update]} == {
        "paediatric_question_with_sources",
        "child_medicine_dose",
    }
    assert "child_growth_percentile" in {o["name"] for o in p.create}
    assert "emergency_numbers_by_country" not in {r["name"] for r in p.create_resources}, (
        "duplicaría el recurso"
    )
    assert p.stale_resources == ["paediatric_source_catalogue"], "el viejo se señala, no se toca"


def test_los_argumentos_llevan_los_esquemas_enteros(catalogo: dict):
    s = _sync()
    o = catalogo["offerings"][0]
    args = s.offering_args(o)
    assert json.loads(args[args.index("--requirements") + 1]) == o["requirements"]
    assert "--no-hidden" in args and args[args.index("--price-value") + 1] == "0.01"
