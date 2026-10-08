"""Manos frías con fiebre: las guías no coinciden, y se dice (8-oct-2026).

- SEUP, hoja de fiebre: «Cuando la fiebre está subiendo es normal que el niño o niña tenga frío,
  incluso escalofríos y un color de la piel reticular (cutis marmorata) especialmente en manos y
  pies» (seup_fiebre#cuales_son_los_sintomas#1).
- NHS, fiebre en niños, «Call 999 if your child: … has unusually cold hands and feet»
  (nhs_en_fever_in_children); y en meningitis, «very cold hands and feet» entre los síntomas.

Decisión del operador, la de siempre: no elegir por el padre, decir las dos. El aviso de que lo
vean hoy se queda (está entre «es normal» y «llame al 999»); debajo va la nota con lo que dice
cada una, también cuando la respuesta acabó en el texto fijo, que era lo que le pasaba a este
padre: el redactor citaba la SEUP, contradecía el aviso y se quedaba sin nada.
"""

from __future__ import annotations

import pytest

from pedibot.bot.guides_differ import notas


@pytest.mark.parametrize(
    "lang",
    ["en", "es", "fr", "de", "pt", "ru", "ar", "hi"],
)
def test_the_note_names_both_guides_in_every_language(lang):
    n = notas(["cold_extremities_with_fever"], "", "", lang)
    assert len(n) == 1
    assert "SEUP" in n[0] and "NHS" in n[0]


def test_no_note_without_the_rule():
    assert notas(["burn"], "", "", "es") == []


def test_steam_lives_in_the_same_register():
    assert notas([], "le pongo la ducha caliente para el vapor", "", "es")
    assert notas([], "", "", "es") == []


def test_the_parent_gets_both_views_even_when_the_answer_falls_back():
    from pedibot.eval import fake_engine_from_settings

    e = fake_engine_from_settings()
    a = e.ask("mi hijo tiene fiebre y las manos muy frías, ¿es normal?", country="ES")
    assert a.level in ("urgent", "emergency")
    assert "SEUP" in a.text and "NHS" in a.text
