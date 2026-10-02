"""El esquema de cada herramienta promete lo que el código cumple (2-oct-2026).

Las ocho herramientas del agente (ACP y MCP) se describen en `ops/acp_catalogue.json`. Glama las
puntúa, y los asistentes eligen por ese esquema; un cliente que valide estrictamente rechaza lo
que el esquema no admite. Al repasarlas salieron promesas que el código no cumplía:

- `childhood_vaccination_schedule`: la descripción decía 75 países y el parámetro, ocho. Un modelo
  que lea el parámetro no pide Kenia.
- `oral_rehydration_plan` exigía el peso y decía «by weight and age»; `/api/ors` no lo lee. Y no
  ofrecía `vomiting`, que sí cambia la respuesta.
- `child_medicine_dose` no pasaba el país, y el bote de 200 mg/5 ml de Haití y la República
  Dominicana no salía primero por ACP ni por MCP.
- `child_friendly_health_explanation` exigía `mode`, con un solo valor posible.
- Ningún número tenía rango, y la calculadora sólo acepta de 1 a 120 kg.

Regla: los límites del esquema son los del manejador. Si el manejador acepta más, el esquema
puede ser más estrecho; nunca más ancho.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAT = json.loads((ROOT / "ops" / "acp_catalogue.json").read_text(encoding="utf-8"))
OFF = {o["name"]: o for o in CAT["offerings"]}


def props(name: str) -> dict:
    return OFF[name]["requirements"]["properties"]


def _worker():
    spec = importlib.util.spec_from_file_location("acp_worker", ROOT / "ops" / "acp_worker.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    sys.modules["acp_worker"] = m
    spec.loader.exec_module(m)
    return m


# ── enums y defaults ─────────────────────────────────────────────────────────


def test_every_default_is_inside_its_enum():
    for o in CAT["offerings"]:
        for k, p in o["requirements"]["properties"].items():
            if "enum" in p and "default" in p:
                assert p["default"] in p["enum"], (o["name"], k)


def test_every_required_field_is_a_property():
    for o in CAT["offerings"]:
        r = o["requirements"]
        assert set(r.get("required", [])) <= set(r["properties"]), o["name"]


def test_the_language_enum_is_the_engines():
    from pedibot.bot.answer import SUPPORTED_LANGS
    from pedibot.bot.strings import tool_strings

    for o in CAT["offerings"]:
        p = o["requirements"]["properties"].get("lang")
        if p:
            assert set(p["enum"]) == set(SUPPORTED_LANGS), o["name"]
            for lang in p["enum"]:
                assert tool_strings(lang), lang


def test_the_vaccine_countries_are_the_schedules_we_have():
    from pedibot.bot.vaccines import Vaccines

    v = Vaccines(ROOT / "config" / "vaccines.yaml")
    p = props("childhood_vaccination_schedule")["country"]
    assert sorted(p["enum"]) == sorted(v.countries)
    for c in p["enum"]:
        assert v.resolve_country(c) == c
    # y la descripción de la oferta no puede decir otro número
    assert f"{len(v.countries)} countries" in OFF["childhood_vaccination_schedule"]["description"]


def test_sex_values_are_what_the_growth_handler_takes():
    from pedibot.bot.growth import Growth  # noqa: F401 — que exista

    assert props("child_growth_percentile")["sex"]["enum"] == ["m", "f"]


# ── números ──────────────────────────────────────────────────────────────────


def test_dose_limits_are_the_calculators():
    from pedibot.bot.dose import DoseError, calculate

    w = props("child_medicine_dose")["weight_kg"]
    calculate("paracetamol", w["minimum"], None)
    calculate("paracetamol", w["maximum"], None)
    for fuera in (w["minimum"] - 0.1, w["maximum"] + 0.1):
        with pytest.raises(DoseError):
            calculate("paracetamol", fuera, None)
    a = props("child_medicine_dose")["age_months"]
    assert (a["minimum"], a["maximum"]) == (0, 216)  # DoseIn: ge=0, le=216


def test_growth_limits_are_the_endpoints():
    p = props("child_growth_percentile")
    assert (p["age_months"]["minimum"], p["age_months"]["maximum"]) == (0, 240)
    assert (p["weight_kg"]["exclusiveMinimum"], p["weight_kg"]["exclusiveMaximum"]) == (0.5, 200)
    assert (p["height_cm"]["exclusiveMinimum"], p["height_cm"]["exclusiveMaximum"]) == (30, 220)


def test_every_number_has_a_range():
    for o in CAT["offerings"]:
        for k, p in o["requirements"]["properties"].items():
            if p.get("type") in ("number", "integer"):
                assert ("minimum" in p or "exclusiveMinimum" in p) and (
                    "maximum" in p or "exclusiveMaximum" in p
                ), (o["name"], k)


def test_country_codes_are_two_letters():
    for o in CAT["offerings"]:
        p = o["requirements"]["properties"].get("country")
        if p and "enum" not in p:
            assert p.get("pattern") == "^[A-Za-z]{2}$", o["name"]


# ── lo que cada herramienta pide y lo que el código usa ──────────────────────


def test_the_child_explanation_does_not_ask_for_mode():
    assert "mode" not in props("child_friendly_health_explanation")


def test_rehydration_asks_for_what_the_handler_reads():
    p = props("oral_rehydration_plan")
    assert "weight_kg" not in p
    assert p["vomiting"]["type"] == "boolean"
    assert "weight" not in OFF["oral_rehydration_plan"]["description"].lower()


def test_an_unknown_medicine_is_explained_in_the_parameter():
    d = props("child_medicine_dose")["drug"]["description"].lower()
    assert "unknown" in d and "paracetamol" in d and "ibuprofen" in d


# ── el enrutado por oferta ───────────────────────────────────────────────────


def test_the_dose_carries_the_country():
    r = _worker().route({"drug": "Calpol", "weight_kg": 14, "country": "ht"}, "child_medicine_dose")
    assert r.path == "/api/dose" and r.payload["country"] == "HT"


def test_rehydration_needs_no_weight_and_passes_vomiting():
    r = _worker().route({"age_months": 24, "vomiting": True}, "oral_rehydration_plan")
    assert r.path.startswith("/api/ors") and "vomiting=true" in r.path
    assert _worker().route({}, "oral_rehydration_plan").path.startswith("/api/ors")


def test_the_named_offering_wins_over_the_fields():
    """Una dosis sin peso no es un calendario de vacunas porque traiga país."""
    assert _worker().route({"drug": "Calpol", "country": "GB"}, "child_medicine_dose") is None


def test_the_child_explanation_is_for_a_child_without_mode():
    r = _worker().route({"question": "why fever?"}, "child_friendly_health_explanation")
    assert r.payload["mode"] == "child"


def test_every_example_routes_by_its_offering():
    w = _worker()
    for o in CAT["offerings"]:
        assert w.route(o["example"], o["name"]) is not None, o["name"]


def test_the_age_description_is_what_the_charts_do():
    from pedibot.bot.growth import Growth

    g = Growth(ROOT / "config" / "who_growth.json")
    g.assess("m", 228, 60, 170, reference="who")
    with pytest.raises(ValueError):
        g.assess("m", 229, 60, 170, reference="who")
    g.assess("m", 240, 60, 170, reference="cdc")
    assert "228" in props("child_growth_percentile")["age_months"]["description"]
