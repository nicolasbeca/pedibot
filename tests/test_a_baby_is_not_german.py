"""«baby» no hace alemana una pregunta inglesa (5-oct-2026).

«how many ml of Tylenol for a 22 pound baby» se detectaba como alemán: «baby» está en las dos
listas y no había otra marca inglesa, y el empate lo ganaba el alemán. En producción lo tapa la
lectura del modelo, pero sin modelo (un fallo, el tope de gasto) el padre recibía alemán. Medido en
las 3.701 preguntas de las baterías: 8 cambian, las 8 de alemán a inglés, ninguna a peor.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import detect_lang


@pytest.mark.parametrize(
    "frase",
    [
        "how many ml of Tylenol for a 22 pound baby",
        "how much Calpol for 9kg baby",
        "my baby was born early and I am not sure when to start solids",
    ],
)
def test_ingles(frase: str) -> None:
    assert detect_lang(frase) == "en"


@pytest.mark.parametrize(
    "frase",
    ["mein Baby hat Fieber", "mein Baby erbricht seit heute Morgen zweimal"],
)
def test_aleman_sigue_siendo_aleman(frase: str) -> None:
    assert detect_lang(frase) == "de"
