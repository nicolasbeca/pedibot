"""Ambiguous words must not drag in the wrong leaflet (26-ago-2026).

Probing questions the corpus does not cover showed the bot answering confidently from the wrong
sheet: "se hace pis en la cama" reached the dehydration leaflet (pis → deshidratación), "le han
oído un soplo" reached the ear-infection sheet (oído = heard, not ear) and "un bulto en el pecho"
of an 11-year-old boy reached the breastfeeding guide (pecho = chest, not breast). Now those
triggers are phrases, which the expansion supports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.retrieval import Synonyms

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def syn() -> Synonyms:
    return Synonyms(ROOT / "config" / "synonyms.yaml")


def test_heard_is_not_an_ear(syn: Synonyms):
    assert "otitis" not in syn.expand("le han oído un soplo en el corazón", "es")
    assert "otitis" in syn.expand("le duele el oído desde anoche", "es")
    assert "otitis" in syn.expand("se toca mucho la oreja", "es")


def test_chest_is_not_a_breast(syn: Synonyms):
    assert "lactancia materna" not in syn.expand("tiene un bulto en el pecho, tiene 11 años", "es")
    assert "lactancia materna" in syn.expand("no se agarra bien al pecho al mamar", "es")


def test_wetting_the_bed_is_not_dehydration(syn: Synonyms):
    assert "deshidratación" not in syn.expand("se hace pis en la cama con 7 años", "es")
    assert "deshidratación" in syn.expand("hace muy poco pis desde ayer", "es")
