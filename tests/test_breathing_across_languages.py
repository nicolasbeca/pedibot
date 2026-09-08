"""Costarle respirar, dicho como se dice en cada lengua (8-sep-2026).

Salió de un barrido de las mismas seis situaciones en los ocho idiomas: la dificultad
respiratoria —el signo de alarma más grave que reconoce el triaje, nivel **emergencia**— se
quedaba en rutina en alemán, portugués e hindi.

Ninguna por falta de regla: `severe_breathing` tiene noventa y tantos patrones. Es la avería de
siempre en este proyecto — la regla se tradujo y cada lengua recibió una red más estrecha:

    castellano:  dificultad (grave |seria )?para respirar   ← el cualificador es OPCIONAL
    portugués:   dificuldade grave para respirar            ← aquí era OBLIGATORIO

Un padre portugués no escribe «dificuldade grave»; escribe «dificuldade para respirar». En
alemán faltaba «bekommt schlecht Luft» (estaban «keine» y «kaum», no «schlecht») y en hindi
«साँस लेने में दिक्कत», que es la forma corriente frente a «no puede respirar», que sí estaba.

La mitad de abajo importa igual: una respiración normal no puede disparar una emergencia, o el
padre aprende a ignorar el aviso.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: «Le cuesta respirar», en las ocho lenguas y como lo escribiría un padre.
CUESTA_RESPIRAR = [
    ("en", "my child is struggling to breathe"),
    ("en", "my son has difficulty breathing"),
    ("es", "a mi hijo le cuesta mucho respirar"),
    ("es", "tiene dificultad para respirar"),
    ("fr", "mon enfant a du mal à respirer"),
    ("de", "mein Kind bekommt schlecht Luft"),
    ("de", "mein Kind bekommt keine Luft"),
    ("de", "mein Kind schnappt nach Luft"),
    ("de", "mein Kind hat Probleme beim Atmen"),
    ("ru", "ребёнку тяжело дышать"),
    ("ar", "طفلي يجد صعوبة في التنفس"),
    ("pt", "meu filho está com dificuldade para respirar"),
    ("pt", "meu filho tem dificuldade de respirar"),
    ("pt", "ele não está conseguindo respirar"),
    ("hi", "मेरे बच्चे को साँस लेने में दिक्कत है"),
    ("hi", "बच्चे को सांस लेने में तकलीफ है"),
    ("hi", "bacche ko saans lene mein dikkat hai"),
]


@pytest.mark.parametrize(("lang", "pregunta"), CUESTA_RESPIRAR)
def test_trouble_breathing_is_an_emergency_in_every_language(
    triage: Triage, lang: str, pregunta: str
) -> None:
    assert triage.assess(pregunta).level == "emergency", f"[{lang}] «{pregunta}»"


RESPIRA_BIEN = [
    ("de", "mein Kind atmet normal"),
    ("de", "mein Kind hat Schnupfen"),
    ("pt", "meu filho está sem dificuldade para respirar"),
    ("pt", "meu filho respira bem"),
    ("pt", "meu filho está com tosse leve"),
    ("hi", "बच्चे को हल्की खाँसी है"),
    ("es", "mi hijo respira bien, solo tiene mocos"),
    ("en", "my child has a runny nose and is breathing fine"),
]


@pytest.mark.parametrize(("lang", "pregunta"), RESPIRA_BIEN)
def test_ordinary_breathing_raises_no_alarm(triage: Triage, lang: str, pregunta: str) -> None:
    """Una regla ensanchada que salta con unos mocos no protege a nadie: enseña a ignorar la
    alarma, que es peor que no tenerla."""
    assert triage.assess(pregunta).level == "routine", f"[{lang}] «{pregunta}» da la alarma"
