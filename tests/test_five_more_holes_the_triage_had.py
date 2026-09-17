"""Cinco signos graves que el triaje veía como rutina (17-sep-2026).

Salieron de repasar el chat entero después de que el operador encontrara el de la cojera. El
método: sacar del índice los pasajes que ENUMERAN motivos de consulta —la guía de primeros
auxilios del Niño Jesús, la ficha IMNCI de India, las páginas del NHS, el manual de la Católica y
Pediatría. Diagnóstico y tratamiento—, partirlos en frases y pasárselas al triaje como si las
escribiera un padre. De 5.123 frases, 153 sonaban graves y salían rutina; leídas a mano, cinco
eran huecos de verdad:

    «mi bebé tiene la fontanela abombada»              rutina · signo de alarma del IMNCI
    «el testículo le duele mucho y está hinchado»      rutina · torsión: seis horas de margen
    «le cuesta mucho tragar y babea»                   rutina · la regla existía y no casaba así
    «se ha puesto pálido de repente»                   rutina · palidez súbita
    «su llanto es distinto, agudo, y no para»          rutina · el NHS manda llamar al 999

Las tres primeras son emergencia y las dos últimas, urgente. La diferencia no es de gravedad
teórica sino de qué hace el padre al leerlo: llamar ahora, o ir hoy.

Y lo que NO puede pasar, que es la mitad del trabajo: un bebé que llora mucho es un bebé que
llora mucho —el cólico es lo más común de la consulta— y un niño pálido después de vomitar no es
una emergencia. Un aviso que salta siempre deja de leerse.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


AHORA = [
    # fontanela abombada: presión dentro de la cabeza (IMNCI la lista entre los signos de peligro)
    ("es", "mi bebé tiene la fontanela abombada", "bulging_fontanelle"),
    ("es", "la mollera la tiene hinchada y dura", "bulging_fontanelle"),
    ("en", "my baby has a bulging fontanelle", "bulging_fontanelle"),
    ("en", "the soft spot on his head is bulging", "bulging_fontanelle"),
    ("fr", "la fontanelle de mon bébé est bombée", "bulging_fontanelle"),
    ("de", "die fontanelle meines babys ist vorgewölbt", "bulging_fontanelle"),
    ("ru", "у малыша выбухает родничок", "bulging_fontanelle"),
    ("ar", "يافوخ طفلي منتفخ", "bulging_fontanelle"),
    ("pt", "a fontanela do meu bebé está abaulada", "bulging_fontanelle"),
    ("hi", "मेरे बच्चे का तालू उभरा हुआ है", "bulging_fontanelle"),
    # testículo: la torsión se opera en horas
    ("es", "a mi hijo le duele mucho un testículo", "testicular_pain"),
    ("es", "tiene el escroto hinchado y le duele", "testicular_pain"),
    ("en", "my son has severe pain in one testicle", "testicular_pain"),
    ("en", "his scrotum is swollen and very painful", "testicular_pain"),
    ("fr", "mon fils a très mal à un testicule", "testicular_pain"),
    ("de", "mein sohn hat starke schmerzen am hoden", "testicular_pain"),
    ("ru", "у сына сильно болит яичко", "testicular_pain"),
    ("ar", "ابني عنده ألم شديد في الخصية", "testicular_pain"),
    ("pt", "o meu filho tem muita dor num testículo", "testicular_pain"),
    ("hi", "मेरे बेटे के अंडकोष में तेज़ दर्द है", "testicular_pain"),
    # tragar y babear: la regla existía, pero no con las palabras de un padre
    ("es", "le cuesta mucho tragar y babea", "cannot_swallow_drooling"),
    ("es", "no puede tragar la saliva", "cannot_swallow_drooling"),
    ("en", "he is drooling and cannot swallow", "cannot_swallow_drooling"),
]

HOY = [
    # palidez súbita
    ("es", "se ha puesto pálido de repente", "sudden_pallor"),
    ("es", "se quedó blanco de golpe y muy flojo", "sudden_pallor"),
    ("en", "he suddenly went very pale and floppy", "sudden_pallor"),
    ("fr", "il est devenu tout pâle d'un coup", "sudden_pallor"),
    ("de", "er ist plötzlich ganz blass geworden", "sudden_pallor"),
    ("ru", "он вдруг сильно побледнел", "sudden_pallor"),
    ("ar", "شحب لونه فجأة", "sudden_pallor"),
    ("pt", "ficou pálido de repente", "sudden_pallor"),
    ("hi", "वह अचानक बिल्कुल पीला पड़ गया", "sudden_pallor"),
    # el llanto que no es el suyo
    ("es", "su llanto es distinto, muy agudo, y no para", "unusual_cry"),
    ("es", "tiene un llanto débil, como un quejido", "unusual_cry"),
    ("en", "she has a weak, high-pitched cry that is not like her normal cry", "unusual_cry"),
    ("fr", "il a un cri aigu, différent de d'habitude", "unusual_cry"),
    ("de", "sie hat einen schrillen schrei, ganz anders als sonst", "unusual_cry"),
    ("ru", "у неё пронзительный крик, не такой как обычно", "unusual_cry"),
    ("ar", "بكاؤه حاد وضعيف وغير معتاد", "unusual_cry"),
    ("pt", "tem um choro agudo, diferente do normal", "unusual_cry"),
    ("hi", "उसका रोना तीखा और कमज़ोर है, हमेशा जैसा नहीं", "unusual_cry"),
]

#: Lo que tiene que seguir siendo rutina. El cólico es el motivo de consulta más común del
#: lactante: si «llora mucho» dispara una alarma, la alarma deja de significar nada.
NO = [
    ("es", "mi bebé llora mucho por las tardes, creo que son cólicos"),
    ("es", "no para de llorar desde hace una hora"),
    ("en", "my baby cries a lot in the evenings"),
    ("es", "está un poco pálido desde que vomitó"),
    ("es", "tiene la mollera blandita"),
    ("en", "he is a bit pale today"),
    ("es", "le ha salido un bultito en la ingle"),
]


@pytest.mark.parametrize("lang,texto,regla", AHORA)
def test_these_mean_call_now(triaje: Triage, lang: str, texto: str, regla: str) -> None:
    r = triaje.assess(texto)
    ids = [m.id for m in r.matched]
    assert regla in ids, f"[{lang}] «{texto}» → {r.level} {ids}"
    assert r.level == "emergency", f"[{lang}] «{texto}» sale {r.level}"


@pytest.mark.parametrize("lang,texto,regla", HOY)
def test_these_mean_go_today(triaje: Triage, lang: str, texto: str, regla: str) -> None:
    r = triaje.assess(texto)
    ids = [m.id for m in r.matched]
    assert regla in ids, f"[{lang}] «{texto}» → {r.level} {ids}"
    assert r.level in ("urgent", "emergency"), f"[{lang}] «{texto}» sale {r.level}"


@pytest.mark.parametrize("lang,texto", NO)
def test_and_these_stay_routine(triaje: Triage, lang: str, texto: str) -> None:
    r = triaje.assess(texto)
    nuevas = {"bulging_fontanelle", "testicular_pain", "sudden_pallor", "unusual_cry"}
    saltaron = nuevas.intersection(m.id for m in r.matched)
    assert not saltaron, f"[{lang}] «{texto}» dispara {saltaron}"


def test_every_new_rule_explains_itself_in_the_eight_languages(triaje: Triage) -> None:
    for rid in ("bulging_fontanelle", "testicular_pain", "sudden_pallor", "unusual_cry"):
        regla = next(r for r in triaje.rules if r.id == rid)
        assert regla.reason_es and regla.reason_en, f"{rid}: sin motivo"
        for lg in ("fr", "de", "ru", "ar", "pt", "hi"):
            assert regla.reasons_by_lang.get(lg), f"{rid}: sin motivo en {lg}"
