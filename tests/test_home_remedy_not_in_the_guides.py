"""Un remedio casero que ninguna guía nombra: ni sí ni no (17-nov-2026).

«Should I put oil or ghee on my newborn baby umbilical cord?» abría con «No, do not put oil or
ghee on the cord», y ningún pasaje habla de aceite ni de ghee (bot/home_remedy.py).
"""

from __future__ import annotations

from test_the_ai_reads_the_question_first import _json, _motor

from pedibot.bot.home_remedy import nota_remedio
from pedibot.index.store import Hit
from pedibot.ingest.schema import Chunk


def _hit(texto: str) -> Hit:
    c = Chunk(
        chunk_id="x#1", doc_id="x", org="AEP", doc_title="Cordón", year=2024, lang="es",
        section="s", pages=[1], text=texto, topic="recien_nacido", doc_type="hoja_padres",
        evidence="sociedad_cientifica", usage="publico", source_hash="h",
    )
    return Hit(chunk=c, score=1.0, matched_terms=[])


CORDON = [_hit("Se recomienda aplicar clorhexidina al 4 % o alcohol de 70° tras lavar con agua.")]
GHEE = "Should I put oil or ghee on my newborn baby umbilical cord?"


def test_oil_and_ghee_not_in_the_passages_get_the_note() -> None:
    nota = nota_remedio(GHEE, CORDON)
    assert "oil or ghee" in nota and "Do NOT say yes or no" in nota


def test_a_passage_that_names_it_answers_and_there_is_no_note() -> None:
    con_aceite = [_hit("No apliques aceite ni polvos de talco en el ombligo.")]
    assert nota_remedio("¿Le puedo poner aceite en el ombligo?", con_aceite) == ""


def test_only_the_missing_one_is_named() -> None:
    con_aceite = [_hit("No apliques aceite en el ombligo.")]
    nota = nota_remedio("¿Le pongo aceite o cúrcuma en el ombligo?", con_aceite)
    assert "turmeric" in nota and "oil" not in nota


def test_asking_about_food_is_not_a_remedy_on_the_skin() -> None:
    assert nota_remedio("Can my 8 month old eat butter?", CORDON) == ""


def test_hindi_and_spanish_questions() -> None:
    assert "ghee" in nota_remedio("क्या बच्चे की नाभि पर घी लगा सकते हैं?", CORDON)
    assert "oil" in nota_remedio("¿Le puedo untar aceite en el ombligo al recién nacido?", CORDON)


def test_the_note_reaches_the_writer() -> None:
    motor, visto = _motor(_json(lang="en", lang_name="English", query_en=GHEE, query_es=GHEE))
    motor.ask(GHEE, lang="en")
    assert any("oil or ghee" in r for r in visto["redactor"]), visto["redactor"][-1][:400]
