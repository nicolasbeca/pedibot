"""What a tweet is not allowed to say (6-sep-2026).

The operator asked for seven drafts a week to post from his own account. A post is a public
claim, and the site's entire argument is that it does not guess — so the cost of one invented
number in a tweet is higher than the reach the tweet buys.

The model therefore writes from a fact sheet that was counted, not remembered, and every draft is
read back before it can be sent. These are the rules it is read against. Each one is a way the
project has already been wrong somewhere else:

  · a number nobody measured (CLAUDE.md: "NO inventar resultados ni inflar números")
  · a clinician's approval that does not exist — no doctor has reviewed these guides, and that
    is the one claim that would actually hurt somebody
  · a dose or an age threshold, which is not a thing to put in a tweet at all
"""

from __future__ import annotations

import json
import pathlib

import pytest

from pedibot.bot.llm import FakeProvider
from pedibot.ops.tweets import (
    MAX_CHARS,
    allowed_numbers,
    fact_sheet,
    facts,
    load_history,
    problems,
    remember,
    write_batch,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]

FACTS = {
    "guides": 483,
    "guides_per_language": {"en": 63, "es": 60},
    "language_names": ["English", "Spanish"],
    "languages": 8,
    "documents": 288,
    "organisations": 18,
    "organisation_names": ["WHO", "NHS", "RKI"],
    "vaccine_countries": 7,
    "vaccine_country_codes": ["BR", "ES"],
    "vaccine_authorities": ["Ministerio de Sanidad", "NHS"],
    "medicines_in_the_dose_calculator": 4,
    "guide_titles_english": ["What should I do if my child has a fever?"],
}
OK = allowed_numbers(FACTS)


def test_the_measured_numbers_are_the_only_ones_allowed() -> None:
    assert {"483", "63", "60", "8", "288", "18", "7", "4"} <= OK
    assert "1200" not in OK and "39" not in OK


@pytest.mark.parametrize(
    ("draft", "why"),
    [
        ("PediBot answers from 1200 published documents.", "números"),
        ("Every guide is reviewed by a paediatrician before it goes up.", "prohibida"),
        ("Our guides are doctor-approved and free.", "prohibida"),
        ("It can diagnose croup from a description.", "prohibida"),
        ("Give 15 mg per kg every six hours.", "números"),
        ("Read it at https://pedibot.xyz", "enlace"),
        ("Ask @pedibot anything.", "cuenta"),
        ("x" * (MAX_CHARS + 1), "caracteres"),
        ("   ", "vacío"),
    ],
)
def test_a_draft_that_breaks_a_rule_is_not_sent(draft: str, why: str) -> None:
    found = problems(draft, FACTS)
    assert found, f"debería haberse rechazado: {draft[:60]}"
    assert any(why in f for f in found), f"esperaba «{why}», salió {found}"


def test_a_true_and_measured_draft_passes() -> None:
    good = (
        "483 guides in 8 languages, written only from 288 published documents. "
        "Every sentence carries the number of the document it came from."
    )
    assert problems(good, FACTS) == []


def test_the_fact_sheet_carries_no_number_the_verifier_would_reject() -> None:
    """The sheet is what the model copies from. A number in it that the verifier does not know
    would train the model to write drafts that are then thrown away."""
    import re

    assert not [n for n in re.findall(r"\d+", fact_sheet(FACTS)) if n not in OK]


def test_the_sample_facts_carry_every_key_the_sheet_reads() -> None:
    """This is how three tests broke at once: a key was added to facts() and the sample here did
    not have it, so fact_sheet() raised KeyError and nothing said which key."""
    real = facts(ROOT, ROOT / "index" / "pedibot.db")
    assert set(real) == set(FACTS), f"faltan en el ejemplo: {sorted(set(real) - set(FACTS))}"


def test_facts_are_counted_in_this_deployment_not_stored() -> None:
    """A constant in a prompt goes stale in silence and starts being false. These are counted
    from the repository and the index every time the job runs."""
    f = facts(ROOT, ROOT / "index" / "pedibot.db")
    assert f["guides"] > 400 and f["languages"] == 8
    assert f["documents"] > 200 and f["organisations"] > 5
    assert f["vaccine_countries"] == len(f["vaccine_country_codes"])
    assert f["guide_titles_english"], "sin títulos reales no se puede citar una guía de verdad"


def test_the_batch_keeps_the_good_ones_and_says_why_it_dropped_the_rest() -> None:
    reply = "\n".join(
        [
            "1. 483 guides in 8 languages, each statement numbered to its document.",
            "2. Reviewed by paediatricians before publication.",  # a lie
            "3. Built from 9999 documents.",  # a number nobody measured
            "4. It says so when no source covers the question, instead of answering.",
            '5. "What should I do if my child has a fever?" — the answer names its sources.',
        ]
    )
    kept, dropped = write_batch(FakeProvider(reply), FACTS, n=7)
    assert len(kept) == 3, kept
    assert not any("paediatricians" in k for k in kept)
    assert any("prohibida" in d for d in dropped)
    assert any("9999" in d for d in dropped)
    # and the numbering the model reached for is gone from what would be pasted
    assert not any(k[0].isdigit() and k[1] in ".)" for k in kept)


def test_it_does_not_send_the_same_draft_two_weeks_running(tmp_path) -> None:
    line = "483 guides in 8 languages, each statement numbered to its document."
    kept, dropped = write_batch(FakeProvider(line), FACTS, n=7, already_sent=(line,))
    assert kept == []
    assert any("repetido" in d for d in dropped)


def test_what_went_out_is_remembered(tmp_path) -> None:
    (tmp_path / "data").mkdir()
    remember(tmp_path, ["uno de verdad y bastante largo para pasar el filtro"])
    assert load_history(tmp_path) == ["uno de verdad y bastante largo para pasar el filtro"]
    # a corrupt line is skipped, not fatal: this file is appended to weekly for years
    (tmp_path / "data" / "tweets_sent.jsonl").write_text(
        json.dumps({"date": "2026-09-06", "text": "bueno"}) + "\n{roto\n", encoding="utf-8"
    )
    assert load_history(tmp_path) == ["bueno"]


def test_it_will_not_say_that_an_answer_is_numbered() -> None:
    """A guide numbers every statement. A chat answer names its sources and shows no numbers —
    the same confusion the site's own legal page had to be corrected for on 5-sep. The prompt
    forbids it and the model wrote it anyway in two batches out of three, so it is checked here
    rather than asked for there."""
    bad = (
        "Each question gets an answer from a published guideline, and every sentence is "
        "tagged with the number of the document it came from."
    )
    assert any("numeradas" in p for p in problems(bad, FACTS))
    good = "Every statement in a guide carries the number of the document it came from."
    assert problems(good, FACTS) == []


def test_a_quoted_title_keeps_its_opening_quotation_mark() -> None:
    """The unwrapper used to strip quotes from both ends, so a draft that opened with a quoted
    guide title lost the opening mark and went out looking broken."""
    from pedibot.ops.tweets import _split

    assert _split('"What should I do if my child has a fever?" is one of the guides here.') == [
        '"What should I do if my child has a fever?" is one of the guides here.'
    ]
    # a draft the model wrapped whole is still unwrapped
    assert _split('"483 guides, written from published documents only."') == [
        "483 guides, written from published documents only."
    ]


def test_it_will_not_name_a_body_that_does_not_exist() -> None:
    """Fourth batch, first draft: "built from 288 published documents by 18 bodies including WHO,
    RKI, NHS, and Ecuchi". There is no Ecuchi — the corpus has an Ecimed and the model reached
    for something shaped like it. Every number was right, so nothing fired.

    A name is exactly as falsifiable as a number, and inventing a source on a site whose whole
    argument is that it names its sources is the same failure as inventing a count."""
    bad = "Built from 288 documents by 18 bodies including WHO, RKI, NHS and Ecuchi."
    assert any("nombres" in p and "Ecuchi" in p for p in problems(bad, FACTS))
    good = "Built from 288 documents by 18 bodies including WHO, NHS and RKI."
    assert problems(good, FACTS) == []


def test_a_capital_at_the_start_of_a_sentence_proves_nothing() -> None:
    """English capitalises the first word of every sentence, and after an opening quote. Treating
    those as names would reject almost everything."""
    assert problems("Vaccination schedules cover 7 countries. Each cites its own source.", FACTS) == []


def test_it_will_not_quote_a_guide_that_does_not_exist() -> None:
    """Quoting a title is the strongest thing one of these can do — it is checkable in one click.
    So it has to be checkable in one click."""
    real = FACTS["guide_titles_english"][0]
    assert problems(f'"{real}" is one of 483 guides.', FACTS) == []
    made_up = '"What should I do if my child swallowed a magnet?" is one of 483 guides.'
    assert any("título que no existe" in p for p in problems(made_up, FACTS))


@pytest.mark.parametrize(
    "draft",
    [
        "PediBot now has a token, PDBT, live on four chains.",
        "483 guides, 8 languages, and a coin to go with them.",
        "Connect your wallet to support the project.",
    ],
)
def test_the_health_account_never_posts_about_the_token(draft: str) -> None:
    """These go out from @pedibotai, the account of a children's health site. A token launched
    on 6-sep takes 1% of every trade, and one post that mixes the two turns a paediatric feed
    into token promotion — for a parent who came for a fever question, that is the moment the
    site stops being credible.

    The operator already keeps them apart: the token is off the homepage by his own decision.
    This is that separation held by the code instead of by somebody remembering.
    """
    assert any("token" in p for p in problems(draft, FACTS))
