"""ACP worker: pricing and job routing (1-sep-2026).

Two lessons brought over from the Regime agent:

1. The budget we propose must be the price the buyer saw on the listing. With the price in a
   constant, lowering it in the marketplace left the worker charging the old one (0.01 listed,
   0.05 proposed — five times the advertised price to the first ever buyer).
2. One generic offering is invisible. Each product is its own job with its own form, so the
   worker must route the form to the right endpoint: doses and vaccination schedules come from
   fixed tables, never from the model.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location("acp_worker", ROOT / "ops" / "acp_worker.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    sys.modules["acp_worker"] = m
    spec.loader.exec_module(m)
    return m


OFFERINGS = [
    {"id": "off-1", "name": "paediatric_question_with_sources", "priceValue": 0.01},
    {"id": "off-2", "name": "child_medicine_dose", "priceValue": 0.02},
]


# ── price ────────────────────────────────────────────────────────────────────


def test_the_price_comes_from_the_offering():
    m = _mod()
    table = m.prices_from(OFFERINGS)
    assert table["off-1"] == "0.01"
    assert table["child_medicine_dose"] == "0.02"


def test_a_job_is_charged_the_price_of_its_own_offering():
    m = _mod()
    table = m.prices_from(OFFERINGS)
    assert m.price_for({"offering": {"id": "off-2"}}, table, fallback="0.99") == "0.02"


def test_an_unidentified_job_is_charged_the_cheapest():
    """Better to undercharge than to charge more than the listing says."""
    m = _mod()
    assert m.price_for({"id": "x"}, m.prices_from(OFFERINGS), fallback="0.99") == "0.01"


def test_without_a_price_table_the_fallback_is_used():
    m = _mod()
    assert m.price_for({"id": "x"}, {}, fallback="0.01") == "0.01"


# ── routing ──────────────────────────────────────────────────────────────────


def test_a_weight_and_a_medicine_go_to_the_dose_table_not_to_the_model():
    m = _mod()
    route = m.route({"drug": "Calpol", "weight_kg": 14})
    assert route.path == "/api/dose" and route.method == "POST"
    assert route.payload["drug"] == "Calpol" and route.payload["weight_kg"] == 14.0


def test_a_country_alone_asks_for_the_vaccination_schedule():
    m = _mod()
    route = m.route({"country": "GB"})
    assert route.path.startswith("/api/vaccines") and route.method == "GET"
    assert "country=GB" in route.path


def test_a_weight_without_a_medicine_is_the_rehydration_plan():
    m = _mod()
    route = m.route({"weight_kg": 12})
    assert route.path.startswith("/api/ors") and route.method == "GET"


def test_a_free_question_goes_to_the_engine():
    m = _mod()
    route = m.route({"question": "my 3 year old has a barking cough", "country": "ES"})
    assert route.path == "/api/agent/ask" and route.method == "POST"
    assert route.payload["question"].startswith("my 3 year old")
    assert route.payload["country"] == "ES"


def test_a_question_wins_over_the_other_fields():
    """A buyer that sends both wants the answer, not the calculator."""
    m = _mod()
    assert m.route({"question": "how much for 14 kg?", "weight_kg": 14}).path == "/api/agent/ask"


def test_an_unusable_form_is_not_routed():
    m = _mod()
    assert m.route({}) is None
    assert m.route({"lang": "en"}) is None


def test_the_worker_knows_the_same_languages_as_the_engine() -> None:
    """It runs as a standalone script on the server, so its list is a copy — copies drift."""
    from pedibot.bot.answer import SUPPORTED_LANGS as ENGINE

    assert set(_mod().SUPPORTED_LANGS) == set(ENGINE)


def test_the_requested_language_reaches_every_tool() -> None:
    m = _mod()
    assert m.route({"question": "Ma fille tousse", "lang": "fr"}).payload["lang"] == "fr"
    assert m.route({"drug": "Doliprane", "weight_kg": 14, "lang": "fr"}).payload["lang"] == "fr"
    assert "lang=fr" in m.route({"country": "FR", "lang": "fr"}).path
    assert "lang=fr" in m.route({"weight_kg": 12, "lang": "fr"}).path
    # an unknown language falls back to English rather than to a blank answer
    # a code that will never be one of ours, not the next language on the roadmap: this line
    # said "pt" and broke the day Portuguese shipped
    unknown = next(c for c in ("zz", "qq", "xx") if c not in m.SUPPORTED_LANGS)
    assert m.route({"question": "hi", "lang": unknown}).payload["lang"] == "en"
