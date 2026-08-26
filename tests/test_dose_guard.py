"""The dose guard must not block rehydration volumes (26-ago-2026).

`verify()` refuses any text with a mg/ml figure unless a dose table is among the sources. That is
what stops the model inventing paracetamol doses — but it also blocked the vómitos and
gastroenteritis guides, whose sources give oral rehydration volumes ("5-10 ml cada 10 minutos",
SEUP). Fluids are exempt ONLY when the surrounding words say fluid; anything unclear still counts
as a dose, because a false alarm costs an article and a miss costs a wrong medicine dose.
"""

from __future__ import annotations

from pedibot.bot.answer import looks_like_medication_dose as dose


def test_a_medicine_with_millilitres_is_a_dose():
    assert dose("dale 5 ml de ibuprofeno cada 8 horas")
    assert dose("give 2.5 ml of paracetamol")


def test_milligrams_are_always_a_dose():
    assert dose("250 mg cada 8 horas")
    assert dose("the tablet contains 200 mg")


def test_rehydration_volumes_are_not_a_dose():
    assert not dose("ofrece 5-10 ml de suero de rehidratación oral cada 10 minutos")
    assert not dose("offer 5 ml of oral rehydration solution every 10 minutes")
    assert not dose("unos 200 ml de suero por cada deposición")


def test_milk_and_water_are_not_a_dose():
    assert not dose("continúa con la leche materna, unas tomas de 60 ml")
    assert not dose("offer 30 ml of water after each feed")


def test_an_unexplained_volume_still_counts_as_a_dose():
    """Unknown context is treated as medication: the guard fails closed."""
    assert dose("dale 5 ml cada 10 minutos")


def test_text_without_numbers_is_never_a_dose():
    assert not dose("ofrece líquidos a menudo y en pequeñas cantidades")
