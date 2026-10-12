"""An English guide gives a temperature in °F too (12-oct-2026).

Most English readers are in the United States (72 % of the real questions), where a thermometer
reads °F. The chat has converted since 2-oct (`con_fahrenheit`); the guides did not, and the two
that matter most — "What should I do if my child has a fever" and "What temperature is a fever
in children" — said "38°C or higher" and nothing else. Seven English guides, fourteen lines,
nearly all of them the "under 3 months with 38 °C" warning.
"""

from __future__ import annotations

import pathlib

from pedibot.bot.temperature import con_fahrenheit

ROOT = pathlib.Path(__file__).resolve().parents[1]
EN = ROOT / "web" / "content" / "en"


def _sin_fahrenheit(text: str) -> list[str]:
    """Lines the converter would still change: a body temperature in °C without its °F."""
    return [
        line.strip()[:90]
        for line in text.splitlines()
        # the sources quote titles verbatim
        if not line.strip().startswith(('- "[', "[")) and con_fahrenheit(line) != line
    ]


def test_every_body_temperature_in_an_english_guide_has_its_fahrenheit() -> None:
    offenders = []
    for f in sorted(EN.glob("*.md")):
        for line in _sin_fahrenheit(f.read_text(encoding="utf-8")):
            offenders.append(f"{f.name}: {line}")
    assert not offenders, offenders


def test_a_temperature_already_given_with_a_slash_is_left_alone() -> None:
    assert con_fahrenheit("a high fever (40°C/104°F)") == "a high fever (40°C/104°F)"


def test_a_temperature_already_in_brackets_is_left_alone() -> None:
    assert con_fahrenheit("around 37°C (98.6°F)") == "around 37°C (98.6°F)"


def test_fahrenheit_given_first_is_left_alone() -> None:
    assert con_fahrenheit("around 98.6°F (37°C)") == "around 98.6°F (37°C)"


def test_inside_brackets_no_second_bracket() -> None:
    assert con_fahrenheit("(less than 38C)") == "(less than 38C / 100.4 °F)"


def test_the_threshold_gets_its_fahrenheit() -> None:
    assert con_fahrenheit("38°C or higher") == "38°C (100.4 °F) or higher"


def _article(lang: str, body: str):
    from types import SimpleNamespace

    from pedibot.publish.articles import Article

    return Article(
        topic="fiebre",
        lang=lang,
        title="When is 38°C a fever?",
        summary="NHS says 38°C or more.",
        body_md=body,
        sources=['[1] NHS — "High temperature (fever) in children", p. 1 — https://www.nhs.uk/'],
        chunk_ids=[],
        llm=SimpleNamespace(model="fake"),
        verification="ok",
    )


def test_a_new_english_guide_is_written_with_fahrenheit() -> None:
    md = _article("en", "## What it is\n\nA temperature of 38°C or higher [1].").markdown()
    assert not _sin_fahrenheit(md), _sin_fahrenheit(md)
    assert "100.4 °F" in md


def test_a_spanish_guide_keeps_celsius_alone() -> None:
    md = _article("es", "## Qué es\n\nUna temperatura de 38 °C o más [1].").markdown()
    assert "°F" not in md


def test_the_english_checklist_gives_fahrenheit_too() -> None:
    """/emergency and every /emergency/<country> in English said "above 39 °C" and "above
    38 °C" alone: the page a parent in the US opens in a hurry (12-oct-2026)."""
    import json

    import yaml

    items = yaml.safe_load((ROOT / "config" / "er_checklist.yaml").read_text(encoding="utf-8"))
    lines = [i["en"] for i in items["items"]]
    signs = json.loads((ROOT / "web" / "site" / "src" / "data" / "warning_signs.json").read_text(encoding="utf-8"))
    lines += [v for v in _english_strings(signs)]
    offenders = [line for line in lines if con_fahrenheit(line) != line]
    assert not offenders, offenders


def _english_strings(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "en" and isinstance(v, str):
                yield v
            else:
                yield from _english_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _english_strings(v)
