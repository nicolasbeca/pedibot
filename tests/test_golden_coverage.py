r"""The golden set has to cover every language the engine speaks (5-sep-2026).

`pedibot eval` returned 1.0 on all six metrics for weeks. That reads like a healthy system and it
was a measurement that had stopped measuring: its cases were en, es and fr, and the site serves
eight languages.

So when the Hindi safety layer could not read "my two-month-old has a fever" — the one rule the
whole thing is built around — nothing said a word. Adding the five missing languages to the set
immediately found four more, in three languages:

    Mein Sohn bekommt kaum Luft, die Rippen ziehen sich ein   → routine
    Mein Sohn sagt, er will sich das Leben nehmen             → routine
    Сын говорит, что хочет умереть                            → routine
    मेरी बेटी ने बटन सेल निगल ली                                  → routine

Four emergencies, read as nothing worth mentioning, in languages that were live.

The lock is on the two things that made it possible: a language with no cases at all, and a
language with cases that never test an emergency. A set of only routine questions in a new
language would pass the first check and teach us nothing.
"""

from __future__ import annotations

import collections
import json
import pathlib

import pytest

from pedibot.bot.answer import SUPPORTED_LANGS

ROOT = pathlib.Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "eval" / "golden.jsonl"


def cases() -> list[dict]:
    return [
        json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_every_language_is_evaluated(lang: str) -> None:
    by_lang = collections.Counter(c.get("lang") for c in cases())
    assert by_lang[lang] >= 5, (
        f"[{lang}] solo {by_lang[lang]} casos en el conjunto de prueba. Un idioma sin casos no se"
        " mide, y el evaluador seguirá dando 1.0 mientras esté roto."
    )


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_every_language_is_tested_on_something_that_must_fire(lang: str) -> None:
    """Routine questions alone would satisfy the count above and prove nothing. What has to work
    in every language is the part that puts a red banner over the answer."""
    levels = {c["level"] for c in cases() if c.get("lang") == lang}
    assert levels - {"routine"}, f"[{lang}] solo casos rutinarios: no se prueba ninguna alarma"
    assert "emergency" in levels or "urgent" in levels, f"[{lang}] sin urgencias ni emergencias"


def test_the_rule_ids_in_the_set_exist() -> None:
    """A case naming a rule that was renamed passes `rules_hit` for ever without checking it."""
    import yaml

    known = {
        r["id"]
        for r in yaml.safe_load((ROOT / "config" / "red_flags.yaml").read_text(encoding="utf-8"))[
            "rules"
        ]
    }
    used = {r for c in cases() for r in c.get("rules", [])}
    assert not used - known, f"reglas que ya no existen: {sorted(used - known)}"


def test_the_ids_are_unique() -> None:
    ids = [c["id"] for c in cases()]
    dupes = [i for i, n in collections.Counter(ids).items() if n > 1]
    assert not dupes, f"ids repetidos: {dupes}"
