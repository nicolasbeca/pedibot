"""El vapor: las guías no coinciden, y se dice cuáles y qué dice cada una (7-oct-2026).

Los CDC proponen el baño con el vapor de la ducha; el NHS dice que no, con crup y con el bol de
agua caliente. Decisión del operador: no elegir por el padre, contarlo (bot/steam.py).
"""

from __future__ import annotations

import pytest

from pedibot.bot.steam import NOTA_VAPOR, nota_vapor


@pytest.mark.parametrize(
    ("pregunta", "respuesta", "lang"),
    [
        ("my son has a barking cough at night", "A steamy bathroom can help.", "en"),
        ("can I use steam for croup?", "Croup is a viral infection.", "en"),
        ("mein Kind hat bellenden Husten", "Eine heiße Dusche kann helfen.", "de"),
        ("tos de perro por la noche", "Puede ayudar el vapor de la ducha.", "es"),
        ("toux aboyante", "La vapeur de la douche peut aider.", "fr"),
        ("ребенок лает кашлем", "Можно подышать горячим паром.", "ru"),
        ("بنتي عندها كحة", "يمكن أن يساعد البخار.", "ar"),
        ("बच्चे को खाँसी है", "भाप लेने से आराम मिल सकता है।", "hi"),
    ],
)
def test_si_se_habla_del_vapor_se_dicen_las_dos(pregunta: str, respuesta: str, lang: str) -> None:
    nota = nota_vapor(pregunta, respuesta, lang)
    assert nota == NOTA_VAPOR[lang]
    assert "CDC" in nota and "NHS" in nota


@pytest.mark.parametrize(
    ("pregunta", "respuesta", "lang"),
    [
        ("my baby has a cold", "Use a clean humidifier or cool mist vaporizer.", "en"),
        ("mi bebé tiene mocos", "Use un humidificador o un vaporizador de vapor frío.", "es"),
        ("кашель уже пару дней", "Давайте больше пить.", "ru"),
        ("my child has a fever", "Give plenty of fluids.", "en"),
    ],
)
def test_sin_vapor_caliente_no_hay_nota(pregunta: str, respuesta: str, lang: str) -> None:
    assert nota_vapor(pregunta, respuesta, lang) is None


def test_todas_las_lenguas_del_chat() -> None:
    assert set(NOTA_VAPOR) >= {"en", "es", "fr", "de", "pt", "ru", "ar", "hi"}
