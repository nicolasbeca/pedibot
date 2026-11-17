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


# 17-nov-2026: «Depois que o coto cair, entre 7 e 15 dias» bajo «pronto-socorro hoje» (ombligo
# rojo y con mal olor, en portugués): el 15 de «15 dias» contaba como el número de urgencias de
# Francia y Malí, y el texto salía sin la frase del aviso diciendo «consultar o profissional».
import pytest  # noqa: E402

from pedibot.bot.banner_lead import PRIMERO_EL_AVISO, con_el_aviso_delante  # noqa: E402


@pytest.mark.parametrize(
    ("texto", "lang"),
    [
        ("Depois que o coto cair, entre 7 e 15 dias, continue limpando.", "pt"),
        ("The stump falls off in 5 to 15 days.", "en"),
        ("Dale 15 ml cada 8 horas.", "es"),
        ("Il pèse 15 kg.", "fr"),
        ("Si dura más de 15 minutos, consulta.", "es"),
    ],
)
def test_a_number_with_a_unit_is_not_a_phone_number(texto: str, lang: str) -> None:
    assert con_el_aviso_delante(texto, "urgent", lang).startswith(PRIMERO_EL_AVISO[lang])


@pytest.mark.parametrize(
    ("texto", "lang"),
    [
        ("Appelez le 15.", "fr"),
        ("Call 999 if he is not breathing.", "en"),
        ("Llama al 112 si no respira.", "es"),
    ],
)
def test_the_emergency_number_still_counts_as_hurry(texto: str, lang: str) -> None:
    assert con_el_aviso_delante(texto, "urgent", lang) == texto
