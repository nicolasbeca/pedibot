"""La hinchazón: la anafilaxia sin «boca», y la mastoiditis sin regla (9-sep-2026).

Barrer la hinchazón contra las advertencias de las 483 guías dejó dos cosas.

**La anafilaxia no veía la boca.** Su lista de partes del cuerpo era labios, lengua, párpados,
cara y garganta — y las guías dicen «hinchazón dentro de la boca y la garganta». Falla por dos
motivos a la vez: falta «boca», y el patrón pedía «hinchazón DE» mientras que la guía escribe
«hinchazón DENTRO DE». Y hay tres órdenes distintos para la misma idea, que aparecieron de uno
en uno según se iba arreglando:

    «los labios se hinchan»              las partes delante del verbo
    «hinchazón dentro de la boca»        el sustantivo, con preposición
    «hinchazón súbita de los labios»     el sustantivo, con una palabra en medio

Los tres salen en guías distintas de la misma lengua. Cubrir uno y dar el trabajo por hecho es
lo que llevaba pasando.

**La mastoiditis no tenía regla.** «Enrojecimiento, dolor o hinchazón detrás de la oreja, o si
la oreja está desplazada hacia delante» sale en las guías de otitis de las ocho lenguas y el
triaje lo leía como rutina. Es la complicación de la otitis que hay que ver el mismo día, y la
oreja desplazada hacia delante es lo que la distingue de un ganglio.

Lo de abajo es lo que hace que las dos reglas se puedan tener: un dolor de oído y una barriga
que duele al tocarla son lo más corriente que hay, y no pueden dar aviso.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: Los tres órdenes, en las ocho lenguas. Las frases vienen de las guías publicadas.
BOCA_HINCHADA = [
    ("es", "Los labios, la boca, la garganta o la lengua se hinchan de repente ."),
    ("es", "Hinchazón dentro de la boca y la garganta."),
    ("en", "Lips, mouth, throat, or tongue suddenly become swollen ."),
    ("en", "Swelling inside the mouth and throat"),
    ("en", "Sudden swelling of their lips, mouth, throat, or tongue"),
    ("fr", "Un gonflement dans la bouche et la gorge ."),
    ("fr", "un gonflement soudain des lèvres, de la bouche, de la gorge ou de la langue"),
    ("de", "Schwellungen im Mund und Rachen auftreten"),
    ("de", "Plötzliche Schwellung von Lippen, Mund, Rachen oder Zunge"),
    ("pt", "Houver inchaço dentro da boca e da garganta."),
    ("pt", "Inchaço súbito dos lábios, boca, garganta ou língua ."),
    ("ru", "есть отёк внутри рта и горла"),
    ("ru", "внезапно опухли губы, рот, горло или язык"),
    ("ar", "تورم داخل الفم والحلق"),
    ("ar", "تورم مفاجئ في الشفاه أو الفم أو الحلق أو اللسان"),
    ("hi", "मुँह और गले के अंदर सूजन हो"),
    ("hi", "होंठ, मुंह, गले या जीभ में अचानक सूजन"),
]

#: La mastoiditis, en las ocho. El signo propio es la oreja desplazada hacia delante.
DETRAS_DE_LA_OREJA = [
    ("es", "tiene hinchazón y dolor detrás de la oreja"),
    ("en", "Have swelling around the ear"),
    ("en", "his ear is pushed forward and red behind"),
    ("fr", "un gonflement derrière l'oreille"),
    ("de", "Schwellung hinter dem Ohr"),
    ("pt", "inchaço atrás da orelha"),
    ("ru", "отёк за ухом"),
    ("ar", "احمرار أو ألم أو تورم خلف الأذن"),
    ("hi", "कान के पीछे सूजन है"),
]

#: El abdomen tenso, duro o distendido: signo de obstrucción, y urgente, no emergencia.
ABDOMEN_DURO = [
    ("es", "El abdomen está tenso, duro o hinchado ."),
    ("en", "Has a swollen or tender tummy."),
    ("de", "der Bauch ist hart und gespannt"),
    ("pt", "Abdômen tenso, duro ou inchado ."),
]

#: Lo más corriente que hay. Si esto avisa, las tres reglas de arriba dejan de significar nada.
#: «Sensible» y «tender» se dejaron fuera de los patrones del abdomen por esta línea: una
#: barriga que duele al tocarla es una gastroenteritis.
LO_CORRIENTE = [
    ("es", "le duele el oído"),
    ("es", "le duele la barriga al tocarla"),
    ("en", "he has an earache"),
    ("en", "his tummy is a bit tender"),
    ("es", "le ha picado un mosquito y se le ha hinchado la pierna"),
]


@pytest.mark.parametrize(("lang", "texto"), BOCA_HINCHADA)
def test_la_boca_y_la_garganta_hinchadas_son_anafilaxia(
    triage: Triage, lang: str, texto: str
) -> None:
    resultado = triage.assess(texto)
    assert resultado.level == "emergency", f"[{lang}] «{texto}» → {resultado.level}"


@pytest.mark.parametrize(("lang", "texto"), DETRAS_DE_LA_OREJA)
def test_la_hinchazon_detras_de_la_oreja_se_ve_hoy(triage: Triage, lang: str, texto: str) -> None:
    resultado = triage.assess(texto)
    assert resultado.level != "routine", f"[{lang}] «{texto}» → rutina"


@pytest.mark.parametrize(("lang", "texto"), ABDOMEN_DURO)
def test_el_abdomen_duro_o_distendido_no_es_rutina(triage: Triage, lang: str, texto: str) -> None:
    resultado = triage.assess(texto)
    assert resultado.level != "routine", f"[{lang}] «{texto}» → rutina"


@pytest.mark.parametrize(("lang", "texto"), LO_CORRIENTE)
def test_el_dolor_de_oido_y_la_barriga_sensible_no_avisan(
    triage: Triage, lang: str, texto: str
) -> None:
    resultado = triage.assess(texto)
    assert resultado.level == "routine", (
        f"[{lang}] «{texto}» → {resultado.level} por {[r.id for r in resultado.matched]}"
    )
