r"""Every published guide has the sections the prompt asks for (5-sep-2026).

The verifier read the draft for citations, doses, language and foreign emergency services, and
regenerated it when any of those failed. It never looked at the SHAPE of what came back, so a
draft that simply left a section out was published as it was.

Counted over the corpus afterwards: 8 Hindi guides with no FAQ section, 1 with no "when to see a
doctor" section at all, 2 Hindi comparison guides carrying Spanish headings, and 3 German guides
saying "du" where the rest of the site says "Sie". 13 of 483, all silent.

The corpus test is the one that matters — it reads what is actually published rather than what
the generator promises. The synthetic ones exist so a broken rule shows up as itself instead of
as 483 failures.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from pedibot.bot.answer import SUPPORTED_LANGS
from pedibot.publish.articles import DOCTOR_WORDS, FAQ_HEADING, _structure_problems

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "web" / "content"
SOURCES_H = re.compile(r"^## (?:Sources|Fuentes|Quellen|Источники|المصادر|Fontes|स्रोत)$", re.M)


def draft_of(path: pathlib.Path) -> tuple[str, bool]:
    """The body as the verifier saw it: no frontmatter, and no sources block — that is appended
    after generation, so checking it would be checking our own output."""
    text = path.read_text(encoding="utf-8")
    body = text.split("---\n", 2)[-1]
    return SOURCES_H.split(body, maxsplit=1)[0], "prompt_version: article_compare_v1" in text


def published() -> list[pathlib.Path]:
    return sorted(CONTENT.rglob("*.md")) if CONTENT.is_dir() else []


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_every_language_is_checkable(lang: str) -> None:
    """A language missing from either table stops being checked and nothing says so."""
    assert lang in FAQ_HEADING, f"[{lang}] sin encabezado de preguntas"
    assert lang in DOCTOR_WORDS, f"[{lang}] sin palabras de «ir al médico»"


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_the_python_and_the_web_agree_on_the_faq_heading(lang: str) -> None:
    """Two lists of the same thing drift. The site builds its FAQ structured data from the
    headings in guides.ts; the generator is told to write the one here. If they stop matching,
    every guide of that language quietly loses its structured data."""
    ts = (ROOT / "web" / "site" / "src" / "guides.ts").read_text(encoding="utf-8")
    block = ts[ts.index("FAQ_HEADINGS = [") : ts.index("];", ts.index("FAQ_HEADINGS = ["))]
    patterns = re.findall(r"'([^']+)'", block)
    assert any(re.fullmatch(p, FAQ_HEADING[lang]) for p in patterns), (
        f"[{lang}] guides.ts no reconoce «{FAQ_HEADING[lang]}»: {patterns}"
    )


def test_the_four_failures_are_caught() -> None:
    ok = "## यह क्या है\ntexto\n## घर पर\ntexto\n## डॉक्टर के पास कब जाएँ\ntexto\n## आम सवाल\ntexto"
    assert _structure_problems(ok, "hi", compare=False) == []

    missing_faq = ok.replace("## आम सवाल", "## कुछ और")
    assert any("no_faq" in p for p in _structure_problems(missing_faq, "hi", compare=False))
    # a comparison guide has no FAQ by design and must not be flagged for it
    assert not any("no_faq" in p for p in _structure_problems(missing_faq, "hi", compare=True))

    no_doctor = "## यह क्या है\ntexto\n## घर पर\ntexto\n## आम सवाल\ntexto"
    assert any("no_doctor" in p for p in _structure_problems(no_doctor, "hi", compare=False))

    alien = ok.replace("## आम सवाल", "## En qué coinciden")
    assert any("another_language" in p for p in _structure_problems(alien, "hi", compare=False))

    duzen = "## Was es ist\nDu solltest dein Kind zu dir nehmen.\n## Wann zum Arzt\nx\n## Häufige Fragen\nx"
    assert any("wrong_register" in p for p in _structure_problems(duzen, "de", compare=False))
    formal = duzen.replace("Du solltest dein Kind zu dir", "Sie sollten Ihr Kind zu sich")
    assert _structure_problems(formal, "de", compare=False) == []


def test_what_a_parent_should_say_to_the_child_may_be_informal() -> None:
    """The register rule is about the guide's own prose. A guide that gives a parent the words to
    use quotes them, and inside the quotes "du" is the correct German — telling a parent to say
    «Ich verstehe, dass Sie das beschäftigt» to their own child would be absurd.

    Counting quoted speech failed the two guides that do this best, on anxiety and on self-harm,
    twice each, so neither could be published; the German guide that really did address the
    reader as "du" from its first line sat next to them with the same complaint.
    """
    quoted = (
        "## Was es ist\nSagen Sie nicht „Beruhige dich“. Sagen Sie: „Ich verstehe, dass dich das "
        "beschäftigt. Möchtest du mehr darüber sprechen?“ und „Wenn du mich brauchst, bin ich da.“\n"
        "## Wann Sie zum Arzt sollten\nx\n## Häufige Fragen\nx"
    )
    assert _structure_problems(quoted, "de", compare=False) == []


@pytest.mark.skipif(not CONTENT.is_dir(), reason="no hay guías publicadas")
def test_no_published_guide_is_missing_a_section() -> None:
    bad = []
    for f in published():
        body, compare = draft_of(f)
        for problem in _structure_problems(body, f.parent.name, compare):
            bad.append(f"{f.parent.name}/{f.name}: {problem.split(':')[0]}")
    assert not bad, f"{len(bad)} guías con secciones mal:\n" + "\n".join(bad[:20])
