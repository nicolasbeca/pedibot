"""The dose calculator does paracetamol and ibuprofen, and nothing else (12-oct-2026).

On 22-sep-2026 a parent asked the chat about salbutamol, was sent to the calculator, found it did
not cover it and came back to say so. The chat's prompt learnt the rule that day; the prompt that
writes the guides kept "point readers to the dose calculator instead", and the server went on
writing it into guides for three weeks: the Arabic asthma guide sends the reader to the calculator
for the inhaler, the Russian pinworm one for mebendazole, the Hindi one for the oral rehydration
solution, the Spanish polio and Portuguese late-vaccines ones for VACCINE doses.

A mention is fine when the same line names one of the two medicines, or when the whole guide is
about one of them (its title says which).
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.publish.articles import calculator_problem, load_prompt

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "web" / "content"


def _title(text: str) -> str:
    for line in text.splitlines()[1:]:
        if line.startswith("title:"):
            return line
        if line.strip() == "---":
            break
    return ""


def test_no_published_guide_sends_another_medicine_to_the_calculator() -> None:
    offenders = []
    for f in sorted(CONTENT.glob("*/*.md")):
        text = f.read_text(encoding="utf-8")
        body = text.split("\n---", 2)[-1]
        found = calculator_problem(body, _title(text))
        if found:
            offenders.append(f"{f.parent.name}/{f.name}: {found[:90]}")
    assert not offenders, offenders


def test_a_draft_that_sends_mebendazole_to_the_calculator_is_refused() -> None:
    body = "Дозировку мебендазола уточняйте у фармацевта или используйте калькулятор доз."
    assert calculator_problem(body, "Острицы у ребёнка")


def test_vaccine_doses_are_not_for_the_calculator() -> None:
    body = "- No intentes calcular dosis de vacunas: usa la calculadora de dosis."
    assert calculator_problem(body, "¿Qué es la polio?")


def test_the_calculator_next_to_paracetamol_is_fine() -> None:
    body = "Puedes darle paracetamol si está molesto. Usa la calculadora de dosis para saber cuánto."
    assert calculator_problem(body, "Fiebre en niños") is None


def test_a_guide_about_ibuprofen_may_point_to_it_anywhere() -> None:
    body = "للجرعة المناسبة لطفلك، استخدم حاسبة الجرعات."
    assert calculator_problem(body, "متى يمكن إعطاء شراب الإيبوبروفين للطفل") is None


# 14-oct-2026, guía de dengue: «Non-steroidal anti-inflammatory medicines such as ibuprofen and
# aspirin should be avoided, because they can increase the risk of bleeding» y, en el mismo
# párrafo, «For paracetamol and ibuprofen you can use our dose calculator». La guía que prohíbe un
# medicamento no puede mandar a calcular su dosis.
def test_a_guide_that_says_avoid_ibuprofen_does_not_send_it_to_the_calculator() -> None:
    body = (
        "Pain can be managed with paracetamol. Non-steroidal anti-inflammatory medicines such as"
        " ibuprofen and aspirin should be avoided, because they can increase the risk of bleeding."
        " For paracetamol and ibuprofen you can use our dose calculator."
    )
    assert calculator_problem(body, "Dengue: what parents need to know")


@pytest.mark.parametrize(
    "body",
    [
        "Evita el ibuprofeno en la varicela. Para el paracetamol y el ibuprofeno, usa la calculadora de dosis.",
        "N'utilisez pas d'ibuprofène. Pour le paracétamol et l'ibuprofène, utilisez le calculateur de doses.",
        "Не давайте ибупрофен. Для парацетамола и ибупрофена есть калькулятор доз.",
    ],
)
def test_avoid_ibuprofen_and_its_calculator_in_other_languages(body: str) -> None:
    assert calculator_problem(body, "Varicela")


def test_avoid_ibuprofen_and_the_calculator_for_paracetamol_only_is_fine() -> None:
    body = (
        "Avoid ibuprofen, because it can increase the risk of bleeding."
        " For paracetamol you can use our dose calculator."
    )
    assert calculator_problem(body, "Dengue: what parents need to know") is None


def test_the_ibuprofen_guide_may_say_when_to_avoid_it() -> None:
    body = "Do not give ibuprofen if your child has chickenpox. Use our dose calculator for ibuprofen."
    assert calculator_problem(body, "Can I give my child ibuprofen?") is None


def test_the_guides_prompt_says_which_two() -> None:
    prompt = load_prompt("article_v1")
    assert "ONLY for paracetamol and ibuprofen" in prompt
    assert "Point readers to the dose calculator instead" not in prompt
