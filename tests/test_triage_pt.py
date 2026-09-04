"""The safety layer must read Portuguese (4-sep-2026).

This is the rule-based check that runs before anything else and decides whether an answer starts
with "go now". It had 630 patterns and not one of them Portuguese, while /pt was already live and
taking questions. Portuguese resembles Spanish closely enough that a few would have fired by
accident, and accident is not a safety layer.

The cases below are the ones that must never be missed, in the words a Brazilian parent would
actually type at three in the morning.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.retrieval import detect_lang
from pedibot.bot.triage import Triage

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


@pytest.mark.parametrize(
    "question,level",
    [
        ("Meu bebê não responde e está muito pálido", "emergency"),
        ("Minha filha teve uma convulsão agora", "emergency"),
        ("Ele engasgou e não consegue respirar", "emergency"),
        ("Meu filho bateu a cabeça e desmaiou", "emergency"),
        ("Tem manchas que não somem quando aperto", "emergency"),
        ("O nariz dele está arroxeado", "emergency"),
        ("Bebê de 2 meses com febre", "urgent"),
        ("Engoliu uma pilha", "urgent"),
        ("Está com chiado no peito", "urgent"),
        ("Ele não faz xixi e tem olhos fundos", "urgent"),
        ("Meu filho disse que quer se matar", "mental_health"),
        ("Meu filho tem tosse leve há dois dias", "routine"),
    ],
)
def test_the_portuguese_warning_signs_fire(triage: Triage, question: str, level: str) -> None:
    assert triage.assess(question).level == level


def test_every_rule_can_explain_itself_in_portuguese(triage: Triage) -> None:
    """A rule that fires without a Portuguese reason answers a Brazilian parent in English at the
    exact moment they are least able to read it."""
    missing = [r.id for r in triage.rules if not r.reason_pt]
    assert not missing, f"reglas sin razón en portugués: {missing}"


def test_a_written_accent_is_not_required(triage: Triage) -> None:
    """Nobody reaches for the accent key while their child is convulsing."""
    assert triage.assess("meu filho teve uma convulsao").level == "emergency"
    assert triage.assess("a crianca nao responde").level == "emergency"


@pytest.mark.parametrize(
    "text,lang",
    [
        ("Meu filho de 4 anos está com 38,8 de febre", "pt"),
        ("A criança bateu a cabeça e vomitou duas vezes", "pt"),
        ("Minha bebê não para de chorar", "pt"),
        # and it must not steal from the neighbour it most resembles
        ("Mi hijo de 4 años tiene 38,8 de fiebre", "es"),
        ("Mi bebé no para de llorar", "es"),
        ("Ça fait mal quand il avale", "fr"),
    ],
)
def test_the_detector_tells_portuguese_from_spanish(text: str, lang: str) -> None:
    assert detect_lang(text) == lang
