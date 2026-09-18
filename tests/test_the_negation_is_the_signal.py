"""«Er kann nicht atmen» daba RUTINA (18-sep-2026).

L173 lo dejó escrito en su día: **la negación puede SER la señal**. «No puede respirar» no es la
ausencia de un problema respiratorio: es el problema. Los patrones castellano, inglés y francés
lo tenían resuelto porque EMPIEZAN por la negación —«no puede respirar», «cannot breathe», «ne
peut pas respirer»— y el guardián respeta eso a propósito.

En alemán el verbo se va al final y la negación queda en medio: «er kann NICHT atmen». El patrón
casaba «atmen», el guardián veía el «nicht» delante y callaba la regla. La frase más urgente que
un padre alemán puede escribir daba rutina, y con ella «er kann nicht atmen und wird blau».

Se encontró barriendo esa familia —la negación como señal— en las cuatro lenguas que colocan la
negación de otra manera. De 18 frases, 3 estaban calladas: el alemán del que no respira, el
alemán del que no toma nada, el árabe del que no se despierta y el árabe de la sangre que no para.

Esta prueba las fija. Y las de abajo son el control: las mismas palabras sin la urgencia siguen
siendo rutina, porque un patrón que lleva la negación dentro es justo el que puede empezar a
saltar de más.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: (idioma, frase, regla que tiene que saltar). La negación es parte de la señal.
NEGACION_ES_SENAL = [
    ("de", "er kann nicht atmen", "severe_breathing"),
    ("de", "er kann nicht atmen und wird blau", "severe_breathing"),
    ("de", "sie kann kaum atmen", "severe_breathing"),
    ("de", "das baby atmet nicht mehr", "severe_breathing"),
    ("de", "er hört auf zu atmen", "severe_breathing"),
    ("de", "er kriegt keine luft", "severe_breathing"),
    ("de", "sie trinkt nichts mehr", "unable_to_drink_or_feed"),
    ("de", "er isst und trinkt nichts", "unable_to_drink_or_feed"),
    ("de", "er kann den arm nicht bewegen", "neuro_deficit"),
    ("de", "er wacht nicht auf", "not_responding"),
    ("de", "die blutung hört nicht auf", "severe_bleeding"),
    ("de", "er kann den kopf nicht beugen", "neck_stiffness"),
    ("ru", "он не может дышать", "severe_breathing"),
    ("ru", "он не просыпается", "not_responding"),
    ("ru", "кровь не останавливается", "severe_bleeding"),
    ("ru", "он не может пить", "unable_to_drink_or_feed"),
    ("ar", "لا يستطيع التنفس", "severe_breathing"),
    ("ar", "لا يستيقظ", "not_responding"),
    ("ar", "الدم لا يتوقف", "severe_bleeding"),
    ("ar", "لا يستطيع الشرب", "unable_to_drink_or_feed"),
    ("hi", "वह साँस नहीं ले पा रहा", "severe_breathing"),
    ("hi", "वह जाग नहीं रहा", "not_responding"),
    ("hi", "खून नहीं रुक रहा", "severe_bleeding"),
    ("es", "no puede respirar", "severe_breathing"),
    ("en", "he cannot breathe", "severe_breathing"),
    ("fr", "il ne peut pas respirer", "severe_breathing"),
    ("pt", "não consegue respirar", "severe_breathing"),
    ("sw", "hawezi kupumua", "severe_breathing"),
]

#: Y el control: las mismas palabras cuando NO son una urgencia.
NO_ES_SENAL = [
    ("de", "er atmet ruhig und schläft"),
    ("de", "er kann nicht schlafen"),
    ("de", "er trinkt gut und isst"),
    ("de", "kann mein kind mit fieber baden"),
    ("ar", "الدم توقف"),
    ("ru", "он хорошо пьёт и ест"),
    ("es", "respira bien y no tiene fiebre"),
    ("en", "he is breathing normally"),
]


@pytest.mark.parametrize("lang,texto,regla", NEGACION_ES_SENAL, ids=lambda x: str(x)[:30])
def test_the_negation_carries_the_alarm(triaje: Triage, lang: str, texto: str, regla: str) -> None:
    ids = [m.id for m in triaje.assess(texto).matched]
    assert regla in ids, (
        f"[{lang}] «{texto}» → {ids or 'nada'}. La negación es la señal, no su contrario (L173)."
    )


@pytest.mark.parametrize("lang,texto", NO_ES_SENAL, ids=lambda x: str(x)[:30])
def test_the_same_words_without_the_emergency_stay_quiet(
    triaje: Triage, lang: str, texto: str
) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", f"[{lang}] «{texto}» → {r.level} por {[m.id for m in r.matched]}"
