"""Percentiles por país: la tabla que usa cada cartilla, y la herramienta que la calcula (13-sep-2026).

El operador pidió llevar los percentiles a todos los idiomas y países que se pudiera. Lo primero
fue averiguar qué tabla usa cada país, porque no todos usan la de la OMS y una página que lo diera
por hecho mentiría justo en el número que el padre compara con su cartilla. Verificado en fuentes
oficiales:

- **Estados Unidos**: OMS hasta los 2 años, CDC 2000 de 2 a 20 (cdc.gov). Los datos LMS del CDC
  son de dominio público → se calculan exactamente.
- **Brasil** (Ministério da Saúde, 2007) y **Rusia** (Minzdrav, 2017): OMS 2006 y 2007 enteras.
- **Portugal** (DGS, Programa Nacional de Saúde Infantil e Juvenil 2013): OMS 2006 y 2007 enteras.
- **México** (NOM-031): OMS 2006 confirmada hasta los 5 años; después, sin fuente oficial leída.
- **Reino Unido**: UK-WHO en el Red Book hasta los 4 años (basada en la OMS); UK90 después.
- **India**: la IAP recomienda OMS hasta los 5 años y sus tablas IAP 2015 de 5 a 18.
- **España**: la AEPap recomienda Fundación Orbegozo 2011 y OMS; cada comunidad elige.
- **Arabia Saudí**: tablas nacionales de 2005 adoptadas por el Consejo de Servicios de Salud.
- **Francia**: AFPA-CRESS/Inserm-CGM 2018 en el carnet de santé.
- **Alemania**: Kromeyer-Hauschild 2001 en el U-Heft (KBV).

Las tablas nacionales con derechos (UK90, IAP 2015, Saudí, francesa, alemana, Orbegozo) NO se
reproducen: la página dice cuál usa el país, enlaza la fuente oficial y avisa de que el percentil
de PediBot, calculado con la OMS, puede no coincidir con el de la cartilla.
"""

from __future__ import annotations

import csv
import json
import re

import pytest
import yaml

from pedibot.bot.growth import Growth, lms_z
from pedibot.settings import ROOT

LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")
REGISTRY = ROOT / "config" / "growth_charts.yaml"


@pytest.fixture(scope="module")
def g() -> Growth:
    return Growth(ROOT / "config" / "who_growth.json")


@pytest.fixture(scope="module")
def paises() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["countries"]


# ── el CDC, contra sus propias columnas de percentil ─────────────────────────────────────
CDC_PUNTOS = [
    # (tabla, sexo, edad en meses, columna, valor publicado, percentil)
    ("cdc_wfa", "m", 24.5, "P5", 10.70051298, 5),
    ("cdc_wfa", "m", 120.5, "P95", 46.15753154, 95),
    ("cdc_hfa", "f", 24.5, "P50", 85.3973169, 50),
    ("cdc_hfa", "m", 120.5, "P10", 130.4809221, 10),
    ("cdc_bmi", "f", 240.0, "P85", 26.47871966, 85),
    ("cdc_bmi", "m", 120.5, "P97", 23.72696086, 97),
]


@pytest.mark.parametrize(("tabla", "sexo", "meses", "col", "valor", "pct"), CDC_PUNTOS)
def test_el_percentil_del_cdc_sale_como_en_su_tabla(
    g: Growth, tabla: str, sexo: str, meses: float, col: str, valor: float, pct: float
):
    from pedibot.bot.growth import percentile

    L, M, S = g.lms(f"{tabla}_{sexo}", meses)
    assert percentile(lms_z(valor, L, M, S)) == pytest.approx(pct, abs=0.2)


def test_el_cdc_empieza_a_los_dos_anos(g: Growth):
    assert g.range("cdc_wfa_m") == (24.0, 240.0)
    assert g.range("cdc_bmi_f")[0] == 24.0


def test_en_estados_unidos_hasta_los_dos_anos_se_usa_la_oms(g: Growth):
    a = g.assess("m", age_months=18, weight_kg=11, height_cm=82, reference="cdc")
    assert all(not i.table.startswith("cdc_") for i in a.indicators)
    assert any("WHO" in s for s in a.sources)


def test_en_estados_unidos_desde_los_dos_anos_se_usa_el_cdc(g: Growth):
    a = g.assess("m", age_months=36, weight_kg=14.3, height_cm=95.3, reference="cdc")
    por = {i.name: i for i in a.indicators}
    assert {"wfa", "hfa", "bmi"} <= set(por), sorted(por)
    assert all(i.table.startswith("cdc_") for i in a.indicators)
    assert any("CDC" in s for s in a.sources)


@pytest.mark.parametrize(
    ("bmi_pct", "flag"),
    [(3, "cdc_underweight"), (50, "normal"), (90, "cdc_overweight"), (97, "cdc_obese")],
)
def test_las_categorias_de_imc_son_las_del_cdc(g: Growth, bmi_pct: float, flag: str):
    """CDC: bajo peso <5, saludable 5–<85, sobrepeso 85–<95, obesidad ≥95."""
    from statistics import NormalDist

    z = NormalDist().inv_cdf(bmi_pct / 100)
    L, M, S = g.lms("cdc_bmi_m", 120.5)
    bmi = M * (1 + L * S * z) ** (1 / L)
    talla = 139.0
    a = g.assess(
        "m", age_months=120.5, weight_kg=bmi * (talla / 100) ** 2, height_cm=talla, reference="cdc"
    )
    assert next(i for i in a.indicators if i.name == "bmi").flag == flag


def test_la_referencia_desconocida_se_rechaza(g: Growth):
    with pytest.raises(ValueError):
        g.assess("m", age_months=36, weight_kg=14, reference="uk90")


# ── el registro de países ─────────────────────────────────────────────────────────────────
def test_estan_los_paises_verificados(paises: dict):
    assert {"US", "BR", "RU", "PT", "MX", "GB", "IN", "ES", "SA", "FR", "DE"} <= set(paises)


def test_cada_pais_dice_que_tabla_usa_y_de_donde_sale(paises: dict):
    for code, p in paises.items():
        assert p["calculator"] in ("who", "cdc"), code
        assert p["match"] in ("full", "partial", "national"), code
        assert p["source"].startswith("https://"), code
        assert p["body"].strip(), code
        assert p["charts"], code
        for c in p["charts"]:
            assert c["name"].strip() and 0 <= c["from_months"] < c["to_months"] <= 240, (code, c)
        nacional = any(not c.get("who_based") for c in p["charts"])
        hasta = max(c["to_months"] for c in p["charts"] if c.get("who_based")) if not nacional else 0
        if p["match"] == "national":
            assert nacional and all(not c.get("who_based") for c in p["charts"]), code
        elif p["match"] == "partial":
            # o una tabla nacional en parte del rango, o la OMS confirmada sólo para una parte
            assert nacional or hasta < 228, f"{code}: «partial» sin tabla nacional ni rango corto"
        else:
            assert not nacional or p["calculator"] == "cdc", f"{code}: «full» con tabla nacional"


def test_los_que_usan_tablas_con_derechos_no_se_calculan_con_ellas(paises: dict):
    """Ni UK90, ni IAP 2015, ni la saudí, ni la francesa, ni la alemana, ni Orbegozo: sólo OMS y CDC."""
    for code in ("GB", "IN", "SA", "FR", "DE", "ES"):
        assert paises[code]["calculator"] == "who", code
        assert paises[code]["match"] in ("partial", "national"), code
    assert paises["US"]["calculator"] == "cdc" and paises["US"]["match"] == "full"
    assert all(paises[c]["match"] == "full" for c in ("BR", "RU", "PT"))
    assert paises["MX"]["match"] == "partial"
    assert paises["SA"]["match"] == "national" and paises["FR"]["match"] == "national"


def test_el_registro_viaja_al_sitio(paises: dict):
    data = json.loads((ROOT / "web/site/src/data/growth_charts.json").read_text(encoding="utf-8"))
    assert set(data) == set(paises), "growth_charts.json no es el registro: falta exportarlo"


# ── la API ────────────────────────────────────────────────────────────────────────────────
def test_la_api_elige_la_tabla_por_pais(tmp_path):
    from fastapi.testclient import TestClient

    from pedibot.api import ApiConfig, create_app
    from pedibot.ops.store import OpsStore

    class _Motor:
        retriever = None

    c = TestClient(
        create_app(
            _Motor(), OpsStore(tmp_path / "o.db", salt="s"), ApiConfig(allowed_origins=["http://x"])
        )
    )
    base = {"sex": "m", "age_months": 36, "weight_kg": 14.3, "height_cm": 95.3, "lang": "es"}
    us = c.get("/api/growth", params={**base, "country": "us"}).json()
    br = c.get("/api/growth", params={**base, "country": "BR"}).json()
    nada = c.get("/api/growth", params=base).json()
    assert us["reference"] == "cdc" and br["reference"] == "who" and nada["reference"] == "who"
    assert us["indicators"][0]["flag_label"], "etiquetas del CDC sin traducir"
    fr = c.get("/api/growth", params={**base, "country": "FR"}).json()
    assert fr["country"]["match"] == "national" and fr["country"]["charts"]


# ── el sitio ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("lang", LANGS)
def test_hay_pagina_por_pais_en_cada_lengua(lang: str):
    base = ROOT / "web/site/src/pages"
    page = (base / "growth" if lang == "en" else base / lang / "growth") / "[country].astro"
    assert page.exists(), page
    t = page.read_text(encoding="utf-8")
    assert "growth_charts.json" in t and "getStaticPaths" in t and "<Growth " in t


@pytest.mark.parametrize("lang", LANGS)
def test_las_frases_por_pais_estan_traducidas(lang: str):
    src = (ROOT / "web/site/src/i18n.ts").read_text(encoding="utf-8")
    ini = src.index(f"  {lang}: {{")
    sig = [
        src.find(f"\n  {x}: {{", ini + 5) for x in LANGS if src.find(f"\n  {x}: {{", ini + 5) > 0
    ]
    bloque = src[ini : min(sig) if sig else None]
    for clave in (
        "growthc_title",
        "growthc_full",
        "growthc_partial",
        "growthc_national",
        "growthc_source",
        "growthc_by_country",
    ):
        m = re.search(clave + r":\s*\"([^\"]+)\"", bloque)
        assert m and m.group(1).strip(), f"{lang}: falta {clave}"


def test_la_calculadora_acepta_el_pais():
    comp = (ROOT / "web/site/src/components/Growth.astro").read_text(encoding="utf-8")
    assert "country" in comp and "data-country" in comp


# ── el chat ───────────────────────────────────────────────────────────────────────────────
def test_el_chat_enlaza_la_pagina_de_su_pais():
    from pedibot.bot.answer import tool_link

    assert tool_link("growth", "hi", "IN").url == "/hi/growth/in"
    assert tool_link("growth", "en", "US").url == "/growth/us"
    assert tool_link("growth", "es", "ZZ").url == "/es/growth", (
        "un país sin página no puede dar un 404"
    )
    assert tool_link("growth", "es").url == "/es/growth"


# ── las fuentes del corpus ────────────────────────────────────────────────────────────────
def test_las_fuentes_para_padres_estan_en_el_catalogo():
    cat = yaml.safe_load((ROOT / "config/fuentes_web.yaml").read_text(encoding="utf-8"))["sources"]
    urls = {d["url"]: d for d in cat}
    for lang in ("en", "es", "fr", "ru", "ar"):
        pre = "" if lang == "en" else f"{lang}/"
        u = f"https://www.who.int/{pre}news-room/questions-and-answers/item/child-growth-standards"
        assert u in urls and urls[u]["lang"] == lang, u
    assert (
        "https://www.nhs.uk/baby/babys-development/height-weight-and-reviews/baby-height-and-weight/"
        in urls
    )


@pytest.mark.parametrize(
    ("lang", "q"),
    [
        ("es", "¿qué significa que mi hijo esté en el percentil 10?"),
        ("en", "what does the 25th centile on my baby's growth chart mean?"),
        ("fr", "que veut dire le percentile de mon bébé sur la courbe de croissance ?"),
        ("ru", "что значит перцентиль роста у ребёнка?"),
        ("ar", "ماذا يعني المئين في منحنى نمو طفلي؟"),
        ("hi", "मेरे बच्चे का ग्रोथ चार्ट पर्सेंटाइल क्या बताता है?"),
        ("de", "was bedeutet die Perzentile auf der Wachstumskurve?"),
        ("pt", "o que significa o percentil do meu bebé na curva de crescimento?"),
    ],
)
def test_una_pregunta_de_percentiles_encuentra_su_fuente(lang: str, q: str):
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.index.store import Index
    from pedibot.ingest.classify import Taxonomy

    r = Retriever(
        Index(ROOT / "index/pedibot.db"),
        Synonyms(ROOT / "config/synonyms.yaml", ROOT / "config/drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(ROOT / "config/taxonomia.yaml"),
    )
    hits, _ = r.search(q, lang)
    docs = [h.chunk.doc_id for h in hits[:3]]
    assert any("child_growth_standards" in d or "baby_height_and_weight" in d for d in docs), (
        lang,
        docs,
    )


def test_hay_guia_de_percentiles_en_el_plan():
    from pedibot.publish.articles import TOPIC_PLAN

    assert "percentiles_crecimiento" in TOPIC_PLAN
    docs = TOPIC_PLAN["percentiles_crecimiento"]["docs"]
    assert any("child_growth_standards" in d for d in docs)


def test_los_datos_del_cdc_son_los_que_publica(g: Growth):
    """Una fila entera contra el CSV descargado, para que el conversor no pierda precisión."""
    f = ROOT / "config" / "cdc_source_check.csv"
    if not f.exists():
        pytest.skip("sin copia del CSV del CDC en esta máquina")
    for row in csv.DictReader(f.open(encoding="utf-8")):
        L, M, S = g.lms(row["table"], float(row["Agemos"]))
        assert (L, M, S) == pytest.approx(
            (float(row["L"]), float(row["M"]), float(row["S"])), rel=1e-6
        )
