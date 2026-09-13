"""La curva de crecimiento: lo que dice la OMS, sin modelo y sin cuenta (13-sep-2026).

Mirando qué ofrecen los competidores (Ada, Buoy, Tiyare, ChildrensMD para síntomas; ParentZ,
GrowthKit, InfantChart para crecimiento) y qué preguntan los padres de la India y el Golfo —«mi
hijo está muy delgado y no gana peso», en hindi y en árabe, en la batería del 13-sep—, lo que
falta en PediBot y pesa allí es **dónde está el niño en la curva de la OMS**. Los rastreadores
de crecimiento son apps con cuenta, en inglés, y no hablan con nadie: ninguno enseña el umbral
de la OMS ni dice cuándo eso es una urgencia.

Esto fija que la herramienta calcule EXACTAMENTE lo que publican las tablas de la OMS —los
patrones 2006 (0–5 años) y la referencia 2007 (5–19)— con el método LMS y la corrección que la
propia OMS aplica más allá de ±3 desviaciones en los indicadores de peso; que clasifique con los
cortes de la OMS (emaciación, retraso del crecimiento, bajo peso, sobrepeso, delgadez); que la
desnutrición aguda grave salga como urgencia; y que exista en las ocho lenguas y desde el chat.
"""

from __future__ import annotations

import re

import pytest

from pedibot.bot.growth import Growth, lms_z
from pedibot.settings import ROOT

LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


@pytest.fixture(scope="module")
def g() -> Growth:
    return Growth(ROOT / "config" / "who_growth.json")


# ── el método LMS, contra las columnas SD que publica la OMS ────────────────────────────
@pytest.mark.parametrize(
    ("x", "L", "M", "S", "z"),
    [
        # weight-for-age niños, día 365: SD2neg 7,741 · SD0 9,646 · SD3 13,341
        (7.741, 0.0645, 9.646, 0.10925, -2),
        (9.646, 0.0645, 9.646, 0.10925, 0),
        (13.341, 0.0645, 9.646, 0.10925, 3),
        # weight-for-height niños 90 cm: SD2neg 11,022 · SD3 16,576
        (11.022, -0.3521, 12.8864, 0.08032, -2),
        (16.576, -0.3521, 12.8864, 0.08032, 3),
        # BMI niñas 120 meses: SD2neg 13,47 · SD2 22,57
        (13.47, -1.4864, 16.6133, 0.12307, -2),
        (22.57, -1.4864, 16.6133, 0.12307, 2),
        # talla niños 228 meses (L=1, normal): SD2neg 161,947
        (161.947, 1, 176.5432, 0.04134, -2),
    ],
)
def test_el_z_sale_como_en_la_tabla_de_la_oms(x: float, L: float, M: float, S: float, z: float):
    assert lms_z(x, L, M, S) == pytest.approx(z, abs=0.01)


def test_mas_alla_de_tres_desviaciones_se_corrige_como_la_oms():
    """La OMS no extrapola la curva LMS más allá de ±3 en los indicadores de peso: a partir de
    ahí cada desviación vale lo que va de SD2 a SD3. Su propia columna SD4 está calculada así:
    niños día 365, SD4 = 14,7 = SD3 + (SD3 − SD2) = 13,341 + 1,358."""
    assert lms_z(14.7, 0.0645, 9.646, 0.10925, restricted=True) == pytest.approx(4.0, abs=0.01)
    assert lms_z(6.111, 0.0645, 9.646, 0.10925, restricted=True) == pytest.approx(-4.0, abs=0.01)


# ── las tablas ────────────────────────────────────────────────────────────────────────────
def test_las_catorce_tablas_estan_y_cubren_lo_que_dicen(g: Growth):
    esperadas = {
        "wfa_m": (0, 1856),
        "wfa_f": (0, 1856),
        "lhfa_m": (0, 1856),
        "lhfa_f": (0, 1856),
        "wfl_m": (45, 110),
        "wfl_f": (45, 110),
        "wfh_m": (65, 120),
        "wfh_f": (65, 120),
        "hfa519_m": (61, 228),
        "hfa519_f": (61, 228),
        "bmi519_m": (61, 228),
        "bmi519_f": (61, 228),
        "wfa510_m": (61, 120),
        "wfa510_f": (61, 120),
    }
    for nombre, (lo, hi) in esperadas.items():
        xs = g.range(nombre)
        assert xs == (lo, hi), f"{nombre}: {xs}"


def test_entre_dos_filas_se_interpola(g: Growth):
    """día 365 M=9,646 y día 366 está en la tabla: a mitad de camino, a mitad de camino."""
    a = g.lms("wfa_m", 365.0)
    b = g.lms("wfa_m", 366.0)
    m = g.lms("wfa_m", 365.5)
    assert min(a[1], b[1]) <= m[1] <= max(a[1], b[1]) and m[1] != a[1]


# ── la valoración, con los cortes de la OMS ───────────────────────────────────────────────
def test_un_nino_en_la_mediana_esta_en_el_percentil_50(g: Growth):
    a = g.assess("m", age_months=24, weight_kg=12.15, height_cm=87.1)
    por = {i.name: i for i in a.indicators}
    assert {"wfa", "lhfa", "wfh"} <= set(por)
    for i in por.values():
        assert abs(i.z) < 0.15, (i.name, i.z)
        assert 44 <= i.percentile <= 56
        assert i.flag == "normal"
    assert a.level == "routine"


def test_la_desnutricion_aguda_grave_es_una_urgencia(g: Growth):
    """OMS: peso para la talla por debajo de −3 DE es desnutrición aguda grave. Niño de 90 cm:
    SD3neg 10,226 kg."""
    a = g.assess("m", age_months=30, weight_kg=9.9, height_cm=90)
    wfh = next(i for i in a.indicators if i.name == "wfh")
    assert wfh.z < -3 and wfh.flag == "severely_wasted"
    assert a.level == "urgent"


def test_emaciacion_moderada_y_sobrepeso(g: Growth):
    a = g.assess("m", age_months=30, weight_kg=10.6, height_cm=90)
    assert next(i for i in a.indicators if i.name == "wfh").flag == "wasted"
    a = g.assess("m", age_months=30, weight_kg=15.5, height_cm=90)
    assert next(i for i in a.indicators if i.name == "wfh").flag == "overweight"
    a = g.assess("m", age_months=30, weight_kg=17.0, height_cm=90)
    assert next(i for i in a.indicators if i.name == "wfh").flag == "obese"


def test_retraso_del_crecimiento(g: Growth):
    """niñas día 1000 (≈33 meses): SD2neg 85,487 cm."""
    a = g.assess("f", age_months=1000 / 30.4375, height_cm=85.0)
    assert next(i for i in a.indicators if i.name == "lhfa").flag == "stunted"
    a = g.assess("f", age_months=1000 / 30.4375, height_cm=81.0)
    assert next(i for i in a.indicators if i.name == "lhfa").flag == "severely_stunted"


def test_menor_de_dos_anos_usa_la_tabla_de_longitud_y_mayor_la_de_talla(g: Growth):
    a = g.assess("f", age_months=18, weight_kg=10, height_cm=80)
    assert next(i for i in a.indicators if i.name == "wfh").table == "wfl_f"
    a = g.assess("f", age_months=30, weight_kg=12, height_cm=90)
    assert next(i for i in a.indicators if i.name == "wfh").table == "wfh_f"


def test_de_cinco_a_diecinueve_se_usa_la_referencia_2007(g: Growth):
    a = g.assess("f", age_months=150, weight_kg=40, height_cm=150)
    por = {i.name: i for i in a.indicators}
    assert "bmi" in por and "hfa" in por and "wfa" not in por, sorted(por)
    assert por["bmi"].table == "bmi519_f"
    a = g.assess("f", age_months=100, weight_kg=26.0, height_cm=130)
    assert "wfa" in {i.name for i in a.indicators}, "el peso para la edad llega hasta los 10 años"


def test_delgadez_y_sobrepeso_de_cinco_a_diecinueve(g: Growth):
    """niñas 120 meses: BMI SD2neg 13,47 · SD1 19,032 · SD2 22,57."""
    alto = 130.0
    for bmi, flag in ((13.0, "thin"), (16.6, "normal"), (20.0, "overweight"), (23.0, "obese")):
        a = g.assess("f", age_months=120, weight_kg=bmi * (alto / 100) ** 2, height_cm=alto)
        assert next(i for i in a.indicators if i.name == "bmi").flag == flag, (bmi, flag)


def test_solo_con_el_peso_se_da_lo_que_se_puede(g: Growth):
    a = g.assess("m", age_months=24, weight_kg=12.15)
    assert [i.name for i in a.indicators] == ["wfa"]
    assert a.missing == ["height"]


def test_fuera_de_rango_se_dice_y_no_se_inventa(g: Growth):
    with pytest.raises(ValueError):
        g.assess("m", age_months=240, weight_kg=60, height_cm=170)
    a = g.assess("m", age_months=24, weight_kg=12, height_cm=130)
    assert "wfh" not in {i.name for i in a.indicators}, "130 cm no está en la tabla de 2 años"
    assert any("wfh" in n for n in a.notes)


def test_las_fuentes_son_las_de_la_oms(g: Growth):
    a = g.assess("m", age_months=24, weight_kg=12.15, height_cm=87.1)
    assert any("2006" in s for s in a.sources)
    a = g.assess("m", age_months=120, weight_kg=31, height_cm=138)
    assert any("2007" in s for s in a.sources)


# ── la API y el sitio ─────────────────────────────────────────────────────────────────────
def test_la_api_devuelve_la_valoracion(tmp_path):
    from fastapi.testclient import TestClient

    from pedibot.api import ApiConfig, create_app
    from pedibot.ops.store import OpsStore

    class _Motor:
        retriever = None

    app = create_app(
        _Motor(), OpsStore(tmp_path / "o.db", salt="s"), ApiConfig(allowed_origins=["http://x"])
    )
    c = TestClient(app)
    r = c.get(
        "/api/growth",
        params={"sex": "m", "age_months": 24, "weight_kg": 12.15, "height_cm": 87.1, "lang": "es"},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["level"] == "routine" and {i["name"] for i in j["indicators"]} == {
        "wfa",
        "lhfa",
        "wfh",
    }
    assert all(i["label"] and i["flag_label"] for i in j["indicators"]), (
        "las etiquetas van traducidas"
    )
    r = c.get(
        "/api/growth",
        params={"sex": "m", "age_months": 30, "weight_kg": 9.9, "height_cm": 90, "lang": "hi"},
    )
    assert r.json()["level"] == "urgent" and r.json()["warnings"]
    r = c.get("/api/growth", params={"sex": "x", "age_months": 24, "weight_kg": 12})
    assert r.status_code == 422


@pytest.mark.parametrize("lang", LANGS)
def test_la_pagina_existe_en_cada_lengua(lang: str):
    base = ROOT / "web" / "site" / "src" / "pages"
    page = base / "growth.astro" if lang == "en" else base / lang / "growth.astro"
    assert page.exists(), f"falta {page}"
    assert "<Growth " in page.read_text(encoding="utf-8")


@pytest.mark.parametrize("lang", LANGS)
def test_las_palabras_estan_en_cada_lengua(lang: str):
    src = (ROOT / "web" / "site" / "src" / "i18n.ts").read_text(encoding="utf-8")
    bloque = src[src.index(f"  {lang}: {{") :]
    for clave in ("growth: {", "nav_growth:", "tool_growth:", "growthpage_title:"):
        assert (
            clave
            in bloque[: bloque.find("\n  " + ("es" if lang == "en" else "xx") + ": {") or None]
        ), f"{lang}: falta {clave}"
    m = re.search(r"nav_growth:\s*['\"]([^'\"]+)", bloque)
    assert m
    if lang != "en":
        en = re.search(r"nav_growth:\s*['\"]([^'\"]+)", src[src.index("  en: {") :]).group(1)
        assert m.group(1) != en, f"nav_growth en {lang} es la inglesa"


def test_el_sitio_enlaza_la_herramienta():
    base = (ROOT / "web" / "site" / "src" / "layouts" / "Base.astro").read_text(encoding="utf-8")
    assert "/growth" in base and "nav_growth" in base


# ── desde el chat ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "q",
    [
        "my 3 year old is very thin and not gaining weight",
        "is my child's weight normal for his age?",
        "mi hijo de 2 años está muy delgado y no gana peso",
        "¿qué percentil tiene mi hija?",
        "mon fils ne grossit pas",
        "mein Kind nimmt nicht zu",
        "ребёнок плохо набирает вес",
        "طفلي نحيف جدا ولا يزداد وزنه",
        "o meu filho não ganha peso",
        "मेरा बच्चा बहुत दुबला है और वजन नहीं बढ़ रहा",
    ],
)
def test_una_pregunta_de_peso_o_talla_lleva_a_la_curva(q: str):
    from pedibot.bot.growth import is_growth_question

    assert is_growth_question(q), q


@pytest.mark.parametrize(
    "q",
    [
        "how much paracetamol for 14 kg?",
        "mi hijo de 12 kg tiene fiebre, ¿cuánto dalsy?",
        "my child has a fever",
    ],
)
def test_una_dosis_o_una_fiebre_no_es_la_curva(q: str):
    from pedibot.bot.growth import is_growth_question

    assert not is_growth_question(q), q


def test_el_motor_enlaza_la_curva_y_el_chat_la_pinta():
    from pedibot.bot.answer import tool_link

    assert tool_link("growth", "hi").url == "/hi/growth"
    assert tool_link("growth", "en").url == "/growth"
    chat = (ROOT / "web/site/src/components/Chat.astro").read_text(encoding="utf-8")
    assert "tool_growth" in chat and "'growth'" in chat
