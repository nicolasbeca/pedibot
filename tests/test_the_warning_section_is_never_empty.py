"""El apartado «cuándo ir al médico» nunca dice que las fuentes no lo cubren (14-oct-2026).

La guía hindi de paracetamol e ibuprofeno en la fiebre (comparativa, 5-sep) tenía como apartado
de avisos: «las fuentes dadas no incluyen cuándo ir al médico o a urgencias con fiebre… esta
pregunta no se puede contestar con estas fuentes», y después un consejo «general» que confesaba
no venir de ninguna. Una guía de FIEBRE sin señales de alarma, cuando la hoja del NHS de fiebre
está en el índice. Se rehízo con esa hoja; tres guías alemanas abrían el apartado igual («Die
Quellen nennen keine einzelnen Warnzeichen») y perdieron la frase, que no decía nada.

Fuera del apartado de avisos la frase puede ser honesta («las fuentes no mencionan el hielo» en
una quemadura es verdad), así que el candado mira sólo ese apartado.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.publish.articles import warning_section_problem

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_no_published_guide_has_an_empty_warning_section() -> None:
    offenders = []
    for f in sorted((ROOT / "web" / "content").glob("*/*.md")):
        found = warning_section_problem(f.read_text(encoding="utf-8"))
        if found:
            offenders.append(f"{f.parent.name}/{f.name}: {found[:100]}")
    assert not offenders, offenders


@pytest.mark.parametrize(
    "section",
    [
        "## डॉक्टर के पास या इमरजेंसी कब जाएँ\n\nदिए गए स्रोतों में यह जानकारी शामिल नहीं है कि बुखार में डॉक्टर या आपातकालीन विभाग कब जाना चाहिए।",
        "## Wann Sie zur Ärztin oder in die Notaufnahme sollten\n\nDie Quellen nennen keine einzelnen Warnzeichen.",
        "## When to see a doctor or go to the emergency department\n\nThe sources do not give specific warning signs.",
        "## Cuándo acudir al médico o a urgencias\n\nLas fuentes no indican cuándo hay que ir a urgencias.",
        "## Quand voir un médecin ou aller aux urgences\n\nLes sources ne précisent pas les signes d'alerte.",
    ],
)
def test_a_draft_whose_warning_section_says_the_sources_do_not_cover_it_is_refused(section: str) -> None:
    assert warning_section_problem(f"Intro.\n\n{section}\n\n## Sources\n")


def test_saying_it_outside_the_warning_section_is_fine() -> None:
    body = (
        "## What you can do at home\n\nThe sources do not mention ice. Use cool running water.\n\n"
        "## When to see a doctor or go to the emergency department\n\n- Large burns [1]\n"
    )
    assert warning_section_problem(body) is None
