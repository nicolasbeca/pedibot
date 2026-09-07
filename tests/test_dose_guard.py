"""The dose guard must not block rehydration volumes (26-ago-2026).

`verify()` refuses any text with a mg/ml figure unless a dose table is among the sources. That is
what stops the model inventing paracetamol doses — but it also blocked the vómitos and
gastroenteritis guides, whose sources give oral rehydration volumes ("5-10 ml cada 10 minutos",
SEUP). Fluids are exempt ONLY when the surrounding words say fluid; anything unclear still counts
as a dose, because a false alarm costs an article and a miss costs a wrong medicine dose.
"""

from __future__ import annotations

import pytest

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


# --- el guardia estaba ciego fuera del alfabeto latino (7-sep-2026) ----------------------------
#
# `looks_like_medication_dose` es el único guardia que hay contra una dosis inventada: si la
# respuesta trae miligramos —o mililitros sin que el contexto diga claramente que es un líquido— y
# entre las fuentes no hay una tabla autorizada, la respuesta se rechaza. Falla del lado seguro a
# propósito: «un 5 ml sin explicar cuenta como dosis».
#
# Pero solo puede fallar del lado seguro si **primero ve la cifra**, y el patrón era `(mg|ml)`:
#
#     es/en/fr/de/pt  «dale 250 mg de paracetamol»    → se rechazaba, bien
#     ru              «дайте 250 мг парацетамола»     → NO lo veía
#     ar              «أعطه 250 ملغ من الباراسيتامول»  → NO lo veía
#     hi              «250 मिग्रा पैरासिटामोल»          → NO lo veía


@pytest.mark.parametrize(
    ("lang", "texto"),
    [
        ("es", "dale 250 mg de paracetamol cada 6 horas"),
        ("en", "give 250 mg of paracetamol every 6 hours"),
        ("fr", "donnez 250 mg de paracétamol toutes les 6 heures"),
        ("de", "geben Sie 250 mg Paracetamol alle 6 Stunden"),
        ("pt", "dê 250 mg de paracetamol a cada 6 horas"),
        ("ru", "дайте 250 мг парацетамола каждые 6 часов"),
        ("ar", "أعطه 250 ملغ من الباراسيتامول كل 6 ساعات"),
        ("hi", "250 मिग्रा पैरासिटामोल हर 6 घंटे में दें"),
    ],
)
def test_a_milligram_figure_is_caught_in_every_script(lang: str, texto: str) -> None:
    """Los miligramos son SIEMPRE una dosis, se escriban en el alfabeto que se escriban."""
    assert dose(texto), (
        f"[{lang}] el guardia no ve la dosis: «{texto}». Una cifra inventada llegaría al padre."
    )


@pytest.mark.parametrize(
    ("lang", "texto"),
    [
        ("es", "ofrece 5 ml de suero cada 10 minutos"),
        ("en", "give 5 ml of water every 10 minutes"),
        ("ru", "давайте по 5 мл воды каждые 10 минут"),
        ("ar", "أعطه 5 مل من الماء كل 10 دقائق"),
        ("hi", "हर 10 मिनट में 5 मिली पानी दें"),
    ],
)
def test_a_rehydration_volume_is_not_a_dose_in_any_script(lang: str, texto: str) -> None:
    """La otra mitad, y la razón de la L21: los volúmenes de suero oral de las hojas del SEUP no
    son dosis, y tomarlos por tales rechazaría respuestas buenas. Al ensanchar el guardia a tres
    escrituras hubo que ensanchar también las palabras de líquido, o el ruso habría empezado a
    perder las respuestas de gastroenteritis."""
    assert not dose(texto), f"[{lang}] toma un líquido por dosis: «{texto}»"
