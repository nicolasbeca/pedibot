"""Bajo un aviso, un texto sin prisa empieza por el aviso (7-oct-2026, bot/banner_lead.py)."""

from __future__ import annotations

import pytest

from pedibot.bot.banner_lead import PRIMERO_EL_AVISO, con_el_aviso_delante


@pytest.mark.parametrize(
    ("texto", "lang"),
    [
        ("Fewer wet nappies than usual is one of the signs of dehydration [5].", "en"),
        ("El asma se debe a una obstrucción de los bronquios [2].", "es"),
        ("La déshydratation se voit à la bouche sèche [1].", "fr"),
        ("Weniger nasse Windeln sind ein Zeichen von Austrocknung [1].", "de"),
    ],
)
def test_sin_prisa_lleva_el_aviso_delante(texto: str, lang: str) -> None:
    for level in ("urgent", "emergency"):
        assert con_el_aviso_delante(texto, level, lang) == f"{PRIMERO_EL_AVISO[lang]}\n\n{texto}"


@pytest.mark.parametrize(
    ("texto", "lang"),
    [
        ("Call 911 now and keep her on her side.", "en"),
        ("Hay que ir a urgencias hoy mismo.", "es"),
        ("Bringen Sie Ihr Kind sofort in die Notaufnahme.", "de"),
        ("Отвезите ребёнка в больницу сегодня.", "ru"),
    ],
)
def test_con_prisa_no_se_toca(texto: str, lang: str) -> None:
    assert con_el_aviso_delante(texto, "emergency", lang) == texto


def test_sin_aviso_no_se_toca() -> None:
    t = "Fewer wet nappies than usual is one of the signs of dehydration."
    assert con_el_aviso_delante(t, "routine", "en") == t


def test_no_se_pone_dos_veces() -> None:
    t = con_el_aviso_delante("A calm text.", "urgent", "en")
    assert con_el_aviso_delante(t, "urgent", "en") == t


def test_todas_las_lenguas_del_chat() -> None:
    assert set(PRIMERO_EL_AVISO) >= {"en", "es", "fr", "de", "pt", "ru", "ar", "hi"}
