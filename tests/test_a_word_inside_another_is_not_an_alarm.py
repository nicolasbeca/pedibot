"""Una palabra dentro de otra no es una alarma (2-oct-2026).

Consulta real, Reino Unido, 2-oct 09:28: «what are the side effects of HPV vaccine to females.
Tell me the risks as well as benefits from research data» recibió «🚨 Call 999 now —
Abnormal movements / seizure». La regla de convulsión buscaba «fits», y «bene-FITS» la lleva.
Las reglas del triaje casan como trozo de texto, no como palabra.

Al pasar todas las reglas por el vocabulario de las 529 guías salieron 23 patrones que casan en
mitad de una palabra. La mayoría están bien —el árabe pega el artículo y las preposiciones
(«الجفاف»), y en alemán «Fieberkrampf» sí es una convulsión—; siete eran falsas alarmas como
la de hoy. Se arreglan con el patrón, y el candado de abajo obliga a revisar cualquier patrón
nuevo que case dentro de otra palabra del corpus.
"""

from __future__ import annotations

import collections
import re

import pytest

from pedibot.bot.triage import Triage, aplana
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


FALSAS = [
    (
        "what are the side effects of HPV vaccine to females. Tell me the risks as well as "
        "benefits from research data",
        "seizure",
    ),
    ("mein Kind hat einen Asthmaanfall, was soll ich tun?", "seizure"),
    ("er hat nachts einen Hustenanfall", "seizure"),
    ("sie hat einen Muskelkrampf in der Wade", "seizure"),
    ("tiene broncoespasmos con el catarro", "seizure"),
    ("tiene broncoespasmos con el catarro", "lockjaw_spasms"),
    ("у ребёнка охриплость голоса после простуды", "severe_breathing"),
    ("where can my teen get psychiatric help?", "moderate_breathing"),
    ("er ist am Rücken sonnenverbrannt", "burn"),
    ("Lebensmittelvergiftung nach dem Grillen?", "poisoning"),
    ("je mets du gel hydroalcoolique sur ses mains", "poisoning"),
]

VERDADERAS = [
    ("my son is having fits", "seizure"),
    ("he had a fit and now he is sleepy", "seizure"),
    ("er hat einen Krampfanfall", "seizure"),
    ("er hatte einen Fieberkrampf", "seizure"),
    ("er hat einen Anfall", "seizure"),
    ("tiene espasmos y no responde", "seizure"),
    ("у него хрип при дыхании и губы синие", "severe_breathing"),
    ("er hat sich an der Herdplatte verbrannt", "burn"),
    ("Vergiftung: er hat Tabletten geschluckt", "poisoning"),
    ("bebeu álcool da garrafa", "poisoning"),
]


@pytest.mark.parametrize("texto,regla", FALSAS)
def test_a_word_inside_another_does_not_fire(triage: Triage, texto: str, regla: str) -> None:
    assert regla not in {r.id for r in triage.assess(texto).matched}


@pytest.mark.parametrize("texto,regla", VERDADERAS)
def test_the_real_alarm_still_fires(triage: Triage, texto: str, regla: str) -> None:
    assert regla in {r.id for r in triage.assess(texto).matched}


#: Patrones que casan dentro de otra palabra del corpus y se han revisado uno a uno: son la
#: misma palabra con un prefijo de su lengua (artículo árabe, compuesto alemán de la misma cosa).
REVISADOS = {
    "جفاف", "حرق(?!ه|ان)|حروق", "krampf", "anfall", "تسمم", "انتحار", "اختناق", "تشنج",
    "ازرقاق", "تشوش", "شرق", "يرقان", "scald", "stridor", "vergiftung", "verbrannt", "espasmos", "хрип",
    # «وازيزا», «y sibilancias», en la guía de asma árabe del 3-oct-2026: la conjunción pegada
    "ازيز",
}


def test_no_new_pattern_fires_inside_another_word(triage: Triage) -> None:
    vocab: collections.Counter[str] = collections.Counter()
    for md in (ROOT / "web" / "content").rglob("*.md"):
        vocab.update(re.findall(r"\w+", aplana(md.read_text(encoding="utf-8")).lower()))
    nuevos = []
    for rule in triage.rules:
        for rx in rule.patterns:
            if any(p in rx.pattern for p in REVISADOS):
                continue
            for w in vocab:
                m = rx.search(w)
                if m and m.start() > 0 and w[m.start() - 1].isalpha():
                    nuevos.append((rule.id, rx.pattern[:40], w))
                    break
    # los que casan por la palabra que le sigue, no por su arranque, se miran aparte
    assert not nuevos, f"patrones que casan dentro de otra palabra; revísalos: {nuevos}"
