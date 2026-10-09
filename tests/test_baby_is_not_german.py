"""«baby» es inglés y alemán; en un empate, gana el inglés (9-oct-2026).

Pendiente del 5-oct: «baby wont sleep» y «baby cough» se detectaban como alemán, y con ellos la
respuesta y el triaje iban en alemán. «baby» y «was» están en las dos listas; un mensaje alemán de
verdad trae siempre algo más («hat», «mein», «ist», una ü).
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import detect_lang


@pytest.mark.parametrize(
    "texto",
    ["baby wont sleep", "baby cough", "my baby was sick", "baby has rash", "newborn baby crying"],
)
def test_english_with_baby(texto: str) -> None:
    assert detect_lang(texto) == "en", texto


@pytest.mark.parametrize(
    "texto",
    ["Baby hat Fieber", "mein Baby schläft nicht", "das Baby ist krank", "Baby weint was soll ich tun"],
)
def test_german_with_baby(texto: str) -> None:
    assert detect_lang(texto) == "de", texto
