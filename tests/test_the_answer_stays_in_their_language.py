"""La pregunta en suajili, el aviso en suajili y la respuesta en inglés (4-nov-2026).

«mtoto wangu ana upele mwekundu usiopotea nikibonyeza» (manchas rojas que no se van al apretar),
preguntado tres veces en vivo con la web en inglés: una de las tres respuestas salía en inglés
bajo el aviso en suajili. La lectura de la IA acertaba la lengua las cinco veces que se miró, y al
redactor le llegaba «ANSWER LANGUAGE: Swahili»; escribía en inglés igual, arrastrado por los
pasajes, que son del NHS. Y salía como «ok»: nada lo miraba.

Aquí decide el código, y sólo en un sentido: si se pidió otra lengua y el texto sale en inglés, un
reintento con la nota. Entre otras dos lenguas el detector se equivoca más, y ahí no se toca.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer_language import se_pasa_al_ingles

#: la 1147, recortada
LA_1147 = (
    "Red spots that do not fade when you press them are one of the warning signs listed by the"
    " SEUP for a child with fever [1], together with being listless, hardly reacting or very"
    " irritable, and difficulty breathing. While you get help, do not give any medicine [2]."
)

#: la 1148, recortada: suajili, con las organizaciones en inglés dentro
LA_1148 = (
    "Mtoto aliye na upele unaobaki bila kupotea unapobonyezwa anahitaji kuonwa na daktari haraka,"
    " na hilo ni ishara ya hatari inayotajwa na SEUP [1]. Wakati mnapata msaada, usimpe dawa yoyote"
    " ya kupunguza homa, kulingana na NHS [2]."
)


def test_english_when_swahili_was_asked_is_sent_back() -> None:
    nota = se_pasa_al_ingles(LA_1147, "sw", "Swahili")
    assert nota is not None
    assert "Swahili" in nota


def test_swahili_with_english_names_inside_is_fine() -> None:
    assert se_pasa_al_ingles(LA_1148, "sw", "Swahili") is None


@pytest.mark.parametrize("codigo", ["en", None])
def test_english_asked_or_unknown_is_left_alone(codigo: str | None) -> None:
    assert se_pasa_al_ingles(LA_1147, codigo, "English") is None


def test_hindi_full_of_brand_names_is_still_hindi() -> None:
    """La 1107: más letras latinas que devanagari, por las marcas, y el detector decía inglés."""
    texto = (
        "9 किलो के लिए Paracetamol (acetaminophen): खुराक 135 मिग्रा, हर 4–6 घंटे में। Crocin"
        " drops 100 mg/ml: 1.35 ml. Calpol syrup 120 mg/5 ml: 5.6 ml [1]."
    )
    assert se_pasa_al_ingles(texto, "hi", "Hindi") is None


def test_between_two_other_languages_nothing_is_decided() -> None:
    assert se_pasa_al_ingles("Mi hijo tiene fiebre desde ayer por la tarde.", "pt", "Portuguese") is None


# --- en el motor ---------------------------------------------------------------------------

from test_the_ai_reads_the_question_first import _json, _motor  # noqa: E402

from pedibot.bot.answer import REVISA, TRADUCE  # noqa: E402
from pedibot.bot.interpret import SYSTEM as LECTURA  # noqa: E402
from pedibot.bot.llm import LLMResult  # noqa: E402

SUAJILI = "Homa nyingi hupona baada ya siku chache, kulingana na NHS [1]."
INGLES = "Most fevers get better in a few days, according to the NHS [1]."


def _con_modelo(primero: str):  # noqa: ANN202
    motor, _ = _motor(None)
    lectura = _json(lang="sw", lang_name="Swahili", query_en="My 2 year old has a fever.")
    notas: list[str] = []

    class Modelo:
        def complete(self, system, user, temperature=0.2, max_tokens=1500):  # noqa: ANN001, ANN202
            if system == LECTURA:
                return LLMResult(lectura, 5, 5, 0.0, "fake")
            if system == REVISA:
                return LLMResult('{"answers_question": true}', 5, 5, 0.0, "fake")
            if system == TRADUCE:
                return LLMResult("", 5, 5, 0.0, "fake")
            if "wrong_language" in system:
                notas.append(system)
                return LLMResult(SUAJILI, 5, 5, 0.0, "fake")
            return LLMResult(primero, 5, 5, 0.0, "fake")

    motor.llm = Modelo()
    return motor, notas


def test_the_engine_rewrites_an_english_answer_in_swahili() -> None:
    motor, notas = _con_modelo(INGLES)
    a = motor.ask("mtoto wangu wa miaka miwili ana homa", lang="en", country="TZ")
    assert a.verification == "regenerated"
    assert "Homa nyingi" in a.text
    assert len(notas) == 1


def test_a_swahili_answer_goes_out_as_it_is() -> None:
    motor, notas = _con_modelo(SUAJILI)
    a = motor.ask("mtoto wangu wa miaka miwili ana homa", lang="en", country="TZ")
    assert a.verification == "ok"
    assert notas == []


def test_the_reviewers_rewrite_cannot_go_back_to_english() -> None:
    motor, _ = _con_modelo(SUAJILI)
    base = motor.llm

    class ConRevisor:
        def complete(self, system, user, temperature=0.2, max_tokens=1500):  # noqa: ANN001, ANN202
            if system == REVISA:
                return LLMResult('{"padding": true, "note": "Cut the padding."}', 5, 5, 0.0, "f")
            if "A reviewer read your draft" in system:
                return LLMResult(INGLES, 5, 5, 0.0, "fake")
            return base.complete(system, user, temperature, max_tokens)

    motor.llm = ConRevisor()
    a = motor.ask("mtoto wangu wa miaka miwili ana homa", lang="en", country="TZ")
    assert "Homa nyingi" in a.text
