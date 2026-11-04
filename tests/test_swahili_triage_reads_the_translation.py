"""En suajili, el triaje lee también la traducción al inglés (4-nov-2026).

Probado antes de escribir a la Doris Mollel Foundation (Tanzania): «mtoto wangu njiti wa wiki
mbili hanyonyi vizuri na ana homa» salía como rutina, y buscando más, «mtoto wangu ana upele
mwekundu usiopotea nikibonyeza» (manchas rojas que no se van al apretar) y «amechomwa na maji ya
moto kifuani» (quemado con agua hirviendo) también. En inglés, las tres dan el aviso.

Desde el 21-sep, a una lengua que el triaje no lee se le suma la frase traducida por la IA. El
suajili no la llevaba porque el triaje «lo lee» (TRIAGE_LANGS), pero sus reglas se escribieron en
una fase, a mano, y tienen huecos que en inglés no hay. Sumar la traducción sólo puede añadir
avisos, nunca quitarlos; y la lectura ya se hace para buscar, así que no cuesta nada.
"""

from __future__ import annotations

import json

from pedibot.bot.llm import FakeProvider
from pedibot.eval import fake_engine_from_settings

MANCHAS_SW = "mtoto wangu ana upele mwekundu usiopotea nikibonyeza"
MANCHAS_EN = "My child has a red rash that does not fade when I press it"


def _lector(lang: str, query_en: str) -> FakeProvider:
    def responder(system: str, user: str) -> str:
        if not system.startswith("You read a parent's message"):
            return "Grounded draft [1]."
        return json.dumps(
            {
                "lang": lang,
                "lang_name": "Swahili" if lang == "sw" else "English",
                "intent": "health",
                "requested_lang": None,
                "requested_name": None,
                "query_en": query_en,
                "query_es": "",
                "keywords": [],
                "new_topic": None,
                "vague": False,
                "alarms": None,
            }
        )

    return FakeProvider(responder)


def test_the_swahili_rules_alone_miss_it():
    """El hueco que lo motiva: si un día las reglas en suajili lo cubren, este test lo dirá."""
    eng = fake_engine_from_settings()
    assert eng.triage.assess(MANCHAS_SW).level == "routine"


def test_the_translation_gives_the_warning_in_swahili():
    eng = fake_engine_from_settings()
    eng.llm = _lector("sw", MANCHAS_EN)
    a = eng.ask(MANCHAS_SW, country="TZ", lang="en")
    assert a.level == "emergency"
    assert a.banner is not None


def test_a_harmless_swahili_question_stays_routine():
    eng = fake_engine_from_settings()
    eng.llm = _lector("sw", "My child has a runny nose, what can I do at home?")
    a = eng.ask("mtoto wangu ana mafua, nifanye nini nyumbani?", country="TZ", lang="en")
    assert a.level == "routine"
