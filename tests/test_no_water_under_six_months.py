"""Agua a un bebé de dos semanas (4-nov-2026).

Probado en vivo antes de escribir a la Doris Mollel Foundation: «mtoto wangu njiti wa wiki mbili
hanyonyi vizuri na ana homa» (mi prematuro de dos semanas no mama bien y tiene fiebre) daba ya el
aviso en suajili, y debajo «Endelea kumnyonyesha mara kwa mara na mpe maji mengi» — sigue dándole
el pecho y dale mucha agua. Al NHS de la fiebre («Do give them plenty of fluids – if your baby is
breastfed, continue to breastfeed») el redactor lo había vuelto «agua». En español, al bebé de
tres semanas con fiebre: «procura que tome líquidos». Antes de los seis meses, sólo pecho o
fórmula: el agua puede hacerle daño y le quita sitio a la leche.

Aquí decide el código: con menos de seis meses, una frase que da agua o líquidos sin decir pecho,
leche o fórmula y sin negarlo pide un reintento con la nota.
"""

from __future__ import annotations

import pytest

from pedibot.bot.water_under_six_months import da_agua_al_lactante


@pytest.mark.parametrize(
    "texto",
    [
        # las dos de verdad; la primera, tal cual: el pecho en la misma frase no la salva, porque
        # el agua va además de él
        "Endelea kumnyonyesha mara kwa mara na mpe maji mengi ili kuepuka upungufu wa maji mwilini.",
        "Mpe maji mengi ili kuepuka upungufu wa maji mwilini.",
        "No lo fuerces a comer si no tiene apetito, pero procura que tome líquidos.",
        "Give them plenty of fluids and keep them cool.",
        "Ofrécele agua a menudo.",
        "Donnez-lui de l'eau régulièrement.",
        "Geben Sie ihm viel Wasser.",
        "Ofereça bastante água.",
        "उसे खूब पानी पिलाएँ।",
        # «ni» es «es» en suajili, «usiku» es «de noche», y «toma» no es siempre la del pecho
        "Ni muhimu kumpa maji mengi.",
        "Usiku mpe maji mengi.",
        "Asegúrate de que toma líquidos.",
    ],
)
def test_water_for_a_young_baby_is_flagged(texto: str) -> None:
    assert da_agua_al_lactante(texto, 0.5) is not None, texto


@pytest.mark.parametrize(
    "texto",
    [
        # con la leche en la misma frase, como lo dice el NHS
        "Give them plenty of fluids – if your baby is breastfed, continue to breastfeed as normal.",
        "Ofrécele el pecho más a menudo para que tome más líquido.",
        "Mpe maziwa ya mama mara kwa mara.",
        # negada
        "No le des agua ni infusiones.",
        "Don't give water to a baby under 6 months.",
        "Usimpe maji wala chai.",
        # el agua que no se bebe
        "No lo bañes en agua fría.",
        "Lávate las manos con agua y jabón.",
        "Usa suero salino, nunca agua del grifo, para los lavados nasales.",
        "Signs of dehydration: fewer wet nappies.",
        # los dos falsos avisos de la medida sobre 115 lactantes (4-nov): «ni lo enfríes pasándole
        # agua» y «falta de agua», que es la deshidratación
        "बच्चे को ज़्यादा कपड़ों में न लपेटें और न ही पानी से पोंछकर ठंडा करने की कोशिश करें ।",
        "अगर दस्त न रुके, या पानी की कमी के लक्षण दिखें, तो तुरंत चिकित्सक से संपर्क करें ।",
        "Usimsugue kwa sifongo na maji ya baridi.",
        # el suero oral no es agua (bot/strings.py, «ors_after_vomit»)
        "Baada ya kutapika, mpe maji ya ORS kidogo sana.",
        "Dale suero oral a cucharaditas.",
        "Angalia dalili za upungufu wa maji mwilini.",
    ],
)
def test_milk_or_a_no_is_not_flagged(texto: str) -> None:
    assert da_agua_al_lactante(texto, 0.5) is None, texto


def test_from_six_months_water_is_fine() -> None:
    assert da_agua_al_lactante("Ofrécele agua a menudo.", 8) is None
    assert da_agua_al_lactante("Ofrécele agua a menudo.", None) is None


def test_the_note_says_what_to_say_instead() -> None:
    nota = da_agua_al_lactante("Mpe maji mengi.", 0.5)
    assert nota is not None
    assert "breast milk" in nota and "formula" in nota


# --- en el motor ---------------------------------------------------------------------------

from test_answer_says_when_to_get_help import _numero, _redaccion, motor  # noqa: E402, F401

from pedibot.bot.answer import REVISA as _REVISA  # noqa: E402
from pedibot.bot.interpret import SYSTEM as _LECTURA  # noqa: E402


def test_the_engine_rewrites_it_once_with_the_note(motor):  # noqa: F811
    def responde(system: str, user: str) -> str:
        if system in (_LECTURA, _REVISA):
            return "no es json"
        lead = _numero(user, "very common in young children")
        lista = _numero(user, "Urgent advice")
        cuando = f" Call for advice if it has lasted 5 days or more [{lista}]."
        if "water_under_6_months" not in system:
            return f"A fever is very common, according to the NHS [{lead}]. Give her water often." + cuando
        return f"A fever is very common, according to the NHS [{lead}]. Keep breastfeeding." + cuando

    eng, llm = motor(responde)
    a = eng.ask("my 4 month old has a fever of 38.5, what should I do?", country="GB")
    assert a.verification == "regenerated"
    assert "water" not in a.text
    assert len(_redaccion(llm)) == 2


def test_an_older_child_is_left_alone(motor):  # noqa: F811
    def responde(system: str, user: str) -> str:
        if system in (_LECTURA, _REVISA):
            return "no es json"
        lead = _numero(user, "very common in young children")
        lista = _numero(user, "Urgent advice")
        return (
            f"A fever is very common, according to the NHS [{lead}]. Give her water often."
            f" Call for advice if it has lasted 5 days or more [{lista}]."
        )

    eng, llm = motor(responde)
    a = eng.ask("my 2 year old has a fever of 38.5, what should I do?", country="GB")
    assert a.verification == "ok"
    assert len(_redaccion(llm)) == 1


def test_the_reviewers_rewrite_cannot_bring_the_water_back(motor):  # noqa: F811
    """1151, en vivo tras desplegar (4-nov): el reintento quitó el agua y la reescritura del
    revisor («el NHS no vale para Tanzania»), que nada miraba, la volvió a poner."""

    def responde(system: str, user: str) -> str:
        if system == _LECTURA:
            return "no es json"
        if system == _REVISA:
            return '{"answers_question": true, "padding": true, "note": "Cut the padding."}'
        lead = _numero(user, "very common in young children")
        lista = _numero(user, "Urgent advice")
        cuando = f" Call for advice if it has lasted 5 days or more [{lista}]."
        if "A reviewer read your draft" in system:
            return f"A fever is common, says the NHS [{lead}]. Give her water often." + cuando
        return f"A fever is very common, according to the NHS [{lead}]. Keep breastfeeding." + cuando

    eng, _ = motor(responde)
    a = eng.ask("my 4 month old has a fever of 38.5, what should I do?", country="GB")
    assert "water" not in a.text
    assert "Keep breastfeeding" in a.text
