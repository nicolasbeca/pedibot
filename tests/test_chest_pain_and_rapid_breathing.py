"""Dos avisos de las guías nuevas que el triaje no veía (14-oct-2026).

Al entrar las guías de dengue y tuberculosis, `test_guides_agree_with_triage` encontró dos
viñetas de «cuándo consultar» que el chat trataba como rutina:

    inglés  «Rapid breathing»                                       (dengue)
    hindi   «सांस लेने या खांसने पर सीने में दर्द बढ़े»  (tuberculosis)

La primera era una forma que faltaba dentro de una regla que ya existía: «fast breathing» y
«breathing fast» saltaban, el sustantivo con «rapid» no, y lo mismo «respiración rápida» y
«быстрое дыхание». La segunda no tenía regla en ninguna lengua: el NHS, hoja de neumonía, pide
cita urgente si hay «chest pain that comes and goes, or happens when breathing or coughing».

El dolor de pecho SOLO sigue siendo rutina, como se decidió el 9-oct con las palpitaciones.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


@pytest.mark.parametrize(
    "texto",
    [
        "Rapid breathing",
        "my son has rapid breathing and a fever",
        "rapid breathing and vomiting",
        "respiración rápida",
        "tiene la respiración muy rápida",
        "быстрое дыхание",
        "у ребёнка быстрое дыхание",
    ],
)
def test_la_respiracion_rapida_dicha_como_sustantivo_salta(triage: Triage, texto: str) -> None:
    assert triage.assess(texto).level != "routine", texto


@pytest.mark.parametrize(
    "texto",
    [
        "सांस लेने या खांसने पर सीने में दर्द बढ़े",
        "सांस लेते समय सीने में दर्द",
        "खांसने पर छाती में दर्द होता है",
        "chest pain when breathing",
        "she has chest pain when she coughs",
        "his chest hurts when he breathes in",
        "it hurts his chest to breathe",
        "dolor en el pecho al respirar",
        "le duele el pecho al toser",
        "le duele el pecho cuando respira",
        "douleur thoracique en respirant",
        "il a mal à la poitrine quand il tousse",
        "Brustschmerzen beim Atmen",
        "die Brust tut beim Husten weh",
        "боль в груди при дыхании",
        "болит грудь когда кашляет",
        "ألم في الصدر عند التنفس",
        "يؤلمه صدره عند السعال",
        "dor no peito ao respirar",
        "dói o peito quando tosse",
    ],
)
def test_el_dolor_de_pecho_al_respirar_o_toser_salta(triage: Triage, texto: str) -> None:
    assert triage.assess(texto).level != "routine", texto


@pytest.mark.parametrize(
    "texto",
    [
        "my son has chest pain",
        "le duele el pecho",
        "il a mal à la poitrine",
        "बच्चे के सीने में दर्द है",
        "chest pain after he fell off his bike",
    ],
)
def test_el_dolor_de_pecho_solo_sigue_siendo_rutina(triage: Triage, texto: str) -> None:
    assert triage.assess(texto).level == "routine", texto
