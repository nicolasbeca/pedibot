"""An answer must not send a parent somewhere they cannot go (5-sep-2026).

The guide generator has refused foreign emergency services since 3-sep — it was the worst thing
that audit found, 43 guides telling a reader anywhere in the world to dial 999. The answer engine
never got the same guard, and the rule was not even in its prompt. Read from the answer log:

    "The NHS advises asking for an urgent GP appointment or calling NHS 111 if you think your
     child may have croup"

to whoever asked, wherever they were. Three of the forty-seven answers logged did this.

One list, one message, two callers: the guide generator checks a filtered copy of its body,
because an article quotes its sources verbatim in a block that legitimately contains "NHS 111";
an answer is checked on exactly what the model wrote. The banner above an answer is ours and
carries the reader's OWN emergency number — it is never part of this.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.answer import FOREIGN_SERVICE, foreign_service_problem, load_prompt, verify_answer

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "text",
    [
        "According to the NHS, call NHS 111 if your child gets worse.",
        "Ask for an urgent GP appointment or get medical advice.",
        "Call 999 if the child is struggling to breathe.",
        "Take them to A&E without waiting.",
        "Call 911 right away.",
        "Ring the poison line on 1-800-222-1222.",
    ],
)
def test_a_service_from_one_country_is_refused(text: str) -> None:
    problem = foreign_service_problem(text)
    assert problem is not None, f"pasa desapercibido: {text!r}"
    assert problem.startswith("foreign_service")


@pytest.mark.parametrize(
    "text",
    [
        "Call your local emergency number now.",
        "According to the NHS, a high temperature is 38 °C or more.",
        "Go to the emergency department today if the fever lasts more than five days.",
        "Ask your doctor for an urgent appointment if the rash spreads.",
        "Fever usually lasts two to four days, according to the SEUP.",
    ],
)
def test_naming_the_organisation_is_not_the_same_as_sending_them_there(text: str) -> None:
    """The whole point of the site is naming the body behind a fact. That must stay allowed —
    a guard that cannot tell "according to the NHS" from "call NHS 111" would gut the answers."""
    assert foreign_service_problem(text) is None, f"falso positivo: {text!r}"


def test_the_answer_verifier_carries_the_guard() -> None:
    """`verify` is shared with the guide generator and checks citations and doses; the answer
    path adds this. A regression here is silent: the answer is produced and published."""

    class FakeChunk:
        is_dose_table = False
        is_dose_source = False
        org = "SEUP"

    class FakeHit:
        chunk = FakeChunk()

    hits = [FakeHit()]
    assert any("foreign_service" in p for p in verify_answer("Call NHS 111 [1].", hits))
    assert verify_answer("Fever lasts two to four days, according to the SEUP [1].", hits) == []
    # and an answer that cites but names nobody is sent back: the site says it names them
    assert any(
        "no_organisation_named" in p for p in verify_answer("Fever lasts a few days [1].", hits)
    )


def test_the_same_source_is_not_named_over_and_over() -> None:
    """This is the thing the operator called robotic, and the prompt cannot be trusted with it —
    the same instruction was in v3 in its opposite form and was obeyed about half the time. Two
    bodies named twice each is prose; one body named three times is a deposition."""

    class FakeChunk:
        is_dose_table = False
        is_dose_source = False
        org = "SEUP"

    class FakeHit:
        chunk = FakeChunk()

    hits = [FakeHit()]
    deposition = (
        "Fever is a defence, according to the SEUP [1]. It usually lasts two to four days,"
        " according to the SEUP [1]. According to the SEUP, watch the child's colour [1]."
    )
    assert any("repeated_attribution" in p for p in verify_answer(deposition, hits))

    prose = (
        "Fever is a defence and usually lasts two to four days, according to the SEUP [1]."
        " Keep the child hydrated and watch their colour. The SEUP asks you to look for red"
        " spots that do not fade when pressed [1]."
    )
    assert verify_answer(prose, hits) == []


def test_the_prompt_states_the_rule_it_is_verified_against() -> None:
    """A guard the prompt does not mention costs a whole extra generation every time it fires."""
    _, prompt = load_prompt()
    low = prompt.lower()
    assert "nhs 111" in low and "911" in low, "el prompt no nombra los servicios prohibidos"
    assert "your local emergency number" in low, "el prompt no da la alternativa"


def test_the_prompt_asks_for_the_organisation_once_per_source() -> None:
    """Naming it in every sentence is what made the answers read like a deposition — the Spanish
    fever answer said "Según la SEUP" four times in five sentences. The [n] marker stays on every
    statement, and that is what makes an answer checkable."""
    _, prompt = load_prompt()
    low = prompt.lower()
    # The rule was two instructions pulling apart — "the first sentence must name one" and "not in
    # every sentence" — and the model split the difference: 9 answers in 99 named nobody and 6
    # named the same body three times. One instruction now, and it says the number.
    # Measured, not guessed. Two instructions pulling apart ("the first sentence must name one"
    # and "not in every sentence") gave 15% retries. "Name each one EXACTLY ONCE" read as a cap
    # and gave 35%, all of them answers naming nobody. What the rule needs is a hard floor said
    # first and the ceiling said after it, which is what these two lines pin.
    assert "must name it in words" in low, "el suelo dejó de ser obligatorio"
    assert "do not name it again" in low, "falta el techo"
    assert "square brackets" in low, "el marcador [n] tiene que seguir siendo obligatorio"


def test_the_pattern_lives_in_one_place() -> None:
    """It used to be defined in `publish.articles`, and `bot.answer` cannot import from there
    without closing a circle — which is how the answer path ended up with no guard at all. Two
    copies of a list like this drift, and the copy that drifts is the one nobody is looking at."""
    articles = (ROOT / "src" / "pedibot" / "publish" / "articles.py").read_text(encoding="utf-8")
    assert "FOREIGN_SERVICE = re.compile" not in articles, "el generador ha vuelto a definir el suyo"
    assert "foreign_service_problem" in articles, "el generador ya no usa el guardián compartido"
    assert FOREIGN_SERVICE.search("call NHS 111"), "el patrón compartido no funciona"


def test_the_brevity_rule_does_not_contradict_the_sourcing_rule() -> None:
    """The two rules were incompatible and the model obeyed the one asking for brevity.

    Rule 3 says name the organisation; rule 8 says an emergency answer is "Call the emergency
    number now" plus two sentences. Thirteen of the fifteen drafts that named nobody were alarms:
    told to be telegraphic, the model dropped the attribution — not disobedience, contradictory
    orders. Measured over 99 answers, twice each: ~15.7% of drafts needed a second call before
    rule 8 said the two sentences still name the source, ~10.6% after.

    The fix that was NOT made, on purpose: exempting emergencies from naming a source. It would
    have removed the retries at a stroke and made those answers worse, in the moment a parent is
    most likely to act on them. They read perfectly well with it — "Lay the child on their side,
    according to the SEUP".
    """
    _, prompt = load_prompt()
    rule8 = next(line for line in prompt.splitlines() if line.startswith("8."))
    assert "two sentences" in rule8, "la regla 8 dejó de pedir brevedad"
    assert "name the organisation" in rule8, (
        "la regla 8 vuelve a contradecir a la 3: pide brevedad sin decir que la fuente se nombra"
    )
