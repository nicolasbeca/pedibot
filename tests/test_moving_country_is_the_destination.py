"""En una mudanza, el calendario que importa es el del país al que se va (29-sep-2026).

«¿Qué vacunas corresponden si nos mudamos de España a Chile?» devolvía el calendario español: con
dos países en la frase gana el nombre más largo —una regla pensada para que «Guinea Ecuatorial» no
se lea como «Guinea»—, y «España» es más largo que «Chile». La familia pregunta por Chile.

Sólo cambia cuando hay dos países y uno lleva delante una marca de destino. Con un país, o sin
marca, todo sigue como estaba.
"""

from __future__ import annotations

import pytest

from pedibot.bot.vaccines import country_in_question


@pytest.mark.parametrize(
    "texto,pais",
    [
        ("¿qué vacunas corresponden si nos mudamos de España a Chile?", "CL"),
        ("we are moving from Spain to Kenya, which vaccines?", "KE"),
        ("nos vamos de Francia a España, ¿qué vacunas le tocan?", "ES"),
        ("wir ziehen von Spanien nach Deutschland, welche Impfungen?", "DE"),
        ("on déménage de l'Espagne vers la France, quels vaccins ?", "FR"),
    ],
)
def test_gana_el_destino(texto, pais):
    assert country_in_question(texto) == pais, texto


@pytest.mark.parametrize(
    "texto,pais",
    [
        ("calendario de vacunas de España", "ES"),
        ("vaccines in Kenya for a baby", "KE"),
        ("vivimos en Guinea Ecuatorial", "GQ"),
    ],
)
def test_lo_de_siempre_no_cambia(texto, pais):
    assert country_in_question(texto) == pais, texto
