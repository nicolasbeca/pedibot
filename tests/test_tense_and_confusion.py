"""El tiempo verbal y la confusión, en las ocho lenguas (9-sep-2026).

Tres familias que quedaban después de barrer respiración, hinchazón y sangrado.

**«Pierde el conocimiento», en presente, fallaba hasta en castellano y en inglés.** La regla
tenía el participio —«ha perdido el conocimiento»— y el sustantivo francés —«perte de
connaissance»— y no el presente, que es como lo escribe una guía al enumerar signos: «Ребёнок
теряет сознание», «das Kind verliert das Bewusstsein». Cinco ciegos de seis.

Hay aquí una cautela que el proyecto ya había pagado (ver `test_a_plain_faint_is_not_an_emergency`):
meter el desmayo en `not_responding` bajó la precisión de las alarmas de 1,0 a 0,978, porque un
niño que se desmayó y se recuperó no es un niño que no responde. Por eso se añade el **presente**,
que describe lo que está pasando, y no se toca «se desmayó», que describe algo que ya terminó.

**La confusión y la desorientación** saltaban en castellano, inglés y portugués y no en las otras
cinco. Al añadirlas metí el adjetivo suelto —`confus`, `verwirrt`— y aparecieron dos falsos
positivos que valen por toda la lección: «je suis confuse sur la dose à donner» y «ich bin
verwirrt, welche Dosis soll ich geben» daban EMERGENCIA por déficit neurológico. **El adjetivo
suelto describe igual de bien al padre que pregunta que al niño.** El proyecto ya lo sabía: sus
patrones piden un verbo de observación («seems confused», «wirkt verwirrt») o una frase que sólo
se dice de un niño («no sabe dónde está»). Se quedan el sustantivo clínico y la desorientación.

**No poder tragar**, las últimas formas: el alemán manda el verbo al final en subordinada («Nicht
schlucken kann»), el francés dice «impossibilité» donde yo había puesto «incapacité», el
portugués usa el infinitivo personal («não conseguir engolir»), y ni el portugués ni el hindi
tenían «la garganta apretada», que sí tenían las otras seis.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]

_ORDEN = {"routine": 0, "mental_health": 1, "urgent": 2, "emergency": 3}


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: El presente: está pasando ahora.
PIERDE_EL_CONOCIMIENTO = [
    ("es", "el niño pierde el conocimiento"),
    ("en", "the child loses consciousness"),
    ("fr", "l'enfant perd connaissance"),
    ("de", "das Kind verliert das Bewusstsein"),
    ("pt", "a criança perde a consciência"),
    ("ru", "Ребёнок теряет сознание"),
]

#: El desmayo que ya terminó no es lo mismo, y esta distinción costó 0,022 de precisión el
#: 6-sep-2026. Se comprueba aquí además de en `test_triage_holes.py` porque es la frontera que
#: el añadido del presente podría haber borrado sin que nadie lo notara.
EL_DESMAYO_QUE_YA_PASO = [
    ("es", "se ha desmayado en el colegio, tiene 12 años"),
    ("es", "mi hija se desmayó al levantarse de golpe"),
    ("en", "he fainted during assembly at school"),
]

#: Confusión y desorientación, en las ocho.
CONFUSO = [
    ("es", "está confuso y desorientado"),
    ("en", "he is confused and disoriented"),
    ("pt", "está confuso e desorientado"),
    ("fr", "il est confus et désorienté"),
    ("de", "Desorientierung oder Verwirrtheit"),
    ("ru", "Спутанность сознания или необычное поведение"),
    ("ar", "تشوش أو ارتباك"),
    ("hi", "भ्रम की स्थिति है"),
]

#: El padre confundido con la dosis. Ésta es la mitad que decide si la familia de arriba se
#: puede tener: quien escribe la pregunta también se confunde, y lo dice con el mismo adjetivo.
EL_QUE_PREGUNTA_TAMBIEN_SE_CONFUNDE = [
    ("es", "estoy confusa con las dosis, no sé cuál darle"),
    ("en", "I am confused about the dose"),
    ("fr", "je suis confuse sur la dose à donner"),
    ("de", "ich bin verwirrt, welche Dosis soll ich geben"),
    ("ar", "أنا مرتبك بشأن الجرعة"),
    ("hi", "मुझे खुराक को लेकर भ्रम है"),
]

#: Las últimas formas de no poder tragar y de la garganta apretada.
TRAGAR_Y_GARGANTA = [
    ("de", "Nicht schlucken kann oder stark sabbert"),
    ("de", "Sie nicht schlucken können"),
    ("fr", "Une impossibilité à avaler"),
    ("fr", "sa gorge semble serrée ou il a du mal à avaler"),
    ("pt", "Você não conseguir engolir"),
    ("pt", "Garganta apertada ou dificuldade para engolir"),
    ("hi", "निगल न पाना या बहुत अधिक लार टपकना"),
    ("hi", "गला तंग महसूस हो या निगलने में कठिनाई हो"),
]


@pytest.mark.parametrize(("lang", "texto"), PIERDE_EL_CONOCIMIENTO)
def test_perder_el_conocimiento_en_presente_es_emergencia(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "emergency", f"[{lang}] «{texto}» → {nivel}"


@pytest.mark.parametrize(("lang", "texto"), EL_DESMAYO_QUE_YA_PASO)
def test_el_desmayo_que_ya_paso_sigue_sin_ser_emergencia(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert _ORDEN[nivel] < _ORDEN["emergency"], f"[{lang}] «{texto}» → {nivel}"


@pytest.mark.parametrize(("lang", "texto"), CONFUSO)
def test_la_confusion_del_nino_es_un_signo_neurologico(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "emergency", f"[{lang}] «{texto}» → {nivel}"


@pytest.mark.parametrize(("lang", "texto"), EL_QUE_PREGUNTA_TAMBIEN_SE_CONFUNDE)
def test_el_padre_confundido_con_la_dosis_no_es_un_signo_neurologico(
    triage: Triage, lang: str, texto: str
) -> None:
    resultado = triage.assess(texto)
    assert resultado.level == "routine", (
        f"[{lang}] «{texto}» → {resultado.level} por {[r.id for r in resultado.matched]}"
    )


@pytest.mark.parametrize(("lang", "texto"), TRAGAR_Y_GARGANTA)
def test_las_ultimas_formas_de_no_poder_tragar(triage: Triage, lang: str, texto: str) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "emergency", f"[{lang}] «{texto}» → {nivel}"
