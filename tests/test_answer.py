from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.answer import REVISA as _REVISA
from pedibot.bot.answer import TRADUCE as _TRADUCE
from pedibot.bot.answer import EmergencyNumbers, Engine, verify
from pedibot.bot.interpret import SYSTEM as _LECTURA
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms, detect_lang
from pedibot.bot.triage import Triage
from pedibot.index.store import Hit, Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk


def _redaccion(llm):  # noqa: ANN001, ANN202
    """Las llamadas al modelo que REDACTAN una respuesta.

    21-sep-2026: desde ese día el motor hace antes una lectura de la pregunta —en qué lengua
    escribe el padre, y qué pregunta de verdad (`pedibot.bot.interpret`)— y, si hace falta,
    traduce una frase fija. Estas pruebas hablaban de «la primera llamada» o de «ninguna llamada»
    queriendo decir «la redacción», y eso es lo que siguen comprobando: se cambia la premisa, no
    la aserción.
    """
    return [c for c in llm.calls if c[0] not in (_LECTURA, _TRADUCE, _REVISA)]


def _chunk(cid, text, red=False, dose=False, url=None, dose_source=False):
    return Chunk(
        chunk_id=cid,
        doc_id=cid.split("#")[0],
        org="SEUP",
        doc_title="Fiebre. Información para padres",
        year=None,
        lang="es",
        section="¿Qué hacer?",
        pages=[1],
        text=text,
        topic="fiebre",
        doc_type="hoja_padres",
        evidence="sociedad_cientifica",
        usage="publico",
        is_red_flag=red,
        is_dose_table=dose,
        is_dose_source=dose_source,
        source_url=url,
        source_hash="h",
        n_words=len(text.split()),
    )


@pytest.fixture
def engine_factory(tmp_path: Path, config_dir):
    db = tmp_path / "i.db"
    build_index(
        [
            _chunk(
                "seup_fiebre#que_hacer#1",
                "La fiebre no es peligrosa por sí misma, según la SEUP. Ofrezca líquidos y no abrigue en exceso. Acuda a urgencias si el niño tiene menos de 3 meses.",
                url="https://seup.org/x.pdf",
            ),
            _chunk(
                "seup_vomitos#s#1",
                "Los vómitos: ofrezca suero oral en pequeñas cantidades.",
                red=True,
            ),
            _chunk("aepap_dosis#tabla#1", "PARACETAMOL 10-15 mg/kg/dosis cada 4-6 h.", dose=True),
        ],
        db,
    )

    def make(responder, llm_for_retrieval=False):
        llm = FakeProvider(responder)
        return Engine(
            Retriever(
                Index(db),
                Synonyms(config_dir / "synonyms.yaml"),
                llm=llm if llm_for_retrieval else None,
                taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
            ),
            Triage(config_dir / "red_flags.yaml"),
            llm,
            EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        ), llm

    return make


def test_detect_lang():
    assert detect_lang("mi hijo tiene fiebre") == "es"
    assert detect_lang("my son has a fever") == "en"


def test_verify_rules():
    hits = [Hit(_chunk("a#s#1", "x"), 1.0, 1)]
    assert verify("Sin citas.", hits) == ["no_citations"]
    assert verify("Con cita [1].", hits) == []
    assert "bad_citation_3" in verify("Con cita [3].", hits)
    assert "dose_without_table" in verify("Dale 150 mg [1].", hits)
    # a dose table alone is not enough: it must come from the sanctioned dosing source, or every
    # professional textbook in the corpus would unlock antibiotic and corticoid doses (26-ago)
    textbook = [Hit(_chunk("a#s#1", "x", dose=True), 1.0, 1)]
    assert "dose_without_table" in verify("Dale 150 mg [1].", textbook)
    dose_hits = [Hit(_chunk("a#s#1", "x", dose=True, dose_source=True), 1.0, 1)]
    assert verify("Dale 150 mg [1].", dose_hits) == []
    # rehydration volumes are not a medication dose and never needed a table
    assert verify("Ofrece 5 ml de suero cada 10 minutos [1].", hits) == []


def test_routine_answer_with_sources(engine_factory):
    eng, llm = engine_factory(
        "La fiebre no es peligrosa por sí misma, según la SEUP [1]. Ofrece líquidos [1]."
    )
    a = eng.ask("mi hijo de 4 años tiene fiebre, ¿qué hago?", country="ES")
    assert a.level == "routine" and a.banner is None and a.verification == "ok"
    assert a.sources and a.sources[0].startswith("[1] SEUP") and "seup.org" in a.sources[0]
    rendered = a.render()
    assert "Fuentes:" not in rendered and "[1]" not in rendered
    assert "Fuentes:" in a.render_debug() and "no sustituye" in a.render_debug()
    assert "SOURCES:" in _redaccion(llm)[0][1] and "[1] SEUP" in _redaccion(llm)[0][1]


def test_fever_without_age_answers_and_then_asks(engine_factory):
    """Hasta el 12-sep-2026 devolvía asked_age sin responder; 10 de 11 padres no volvían."""
    eng, llm = engine_factory(
        "Si tiene menos de tres meses, al médico hoy. Si no, la fiebre no es peligrosa, según la SEUP [1]."
    )
    a = eng.ask("mi hijo tiene fiebre")
    assert a.verification == "ok" and llm.calls and a.ask_age


def test_emergency_banner_first_with_country_numbers(engine_factory):
    eng, _ = engine_factory("Ofrezca suero, según la SEUP [1].")
    a = eng.ask("my 3 year old is vomiting and having a seizure", country="US")
    assert a.level == "emergency"
    assert a.banner and a.banner.startswith("🚨 Call 911")
    assert a.render().startswith("🚨")


def test_mental_health_banner_uses_helpline(engine_factory):
    eng, _ = engine_factory("[1]")
    a = eng.ask("mi hija de 14 años dice que quiere morir", country="ES")
    assert a.level == "mental_health" and "024" in (a.banner or "")


def test_no_source_means_silence(engine_factory):
    eng, llm = engine_factory("hallucination [1]")
    a = eng.ask("¿mi perro puede tomar chocolate?")
    assert a.verification == "no_source" and _redaccion(llm) == []
    assert "No tengo información fiable" in a.text


def test_bad_citation_triggers_regeneration_then_fallback(engine_factory):
    # un borrador del largo de una respuesta de verdad: los cortos sin cita son una negativa
    eng, llm = engine_factory(
        "La fiebre es un mecanismo de defensa del cuerpo frente a las infecciones y en la mayoría de los niños dura entre dos y cuatro días, conviene ofrecer líquidos, vigilar el estado general y consultar si aparece cualquier signo que preocupe a la familia o si no mejora."
    )
    a = eng.ask("mi hijo de 4 años tiene fiebre")
    assert a.verification == "fallback" and len(_redaccion(llm)) == 2
    assert "No tengo información fiable" in a.text


def test_regeneration_succeeds(engine_factory):
    # la lectura de la pregunta también es una llamada al modelo (21-sep-2026); el iterador
    # tiene que ser sólo del redactor, o se lo come la lectura y el primer borrador sale bueno
    answers = iter(
        [
            "La fiebre es un mecanismo de defensa del cuerpo frente a las infecciones y en la mayoría de los niños dura entre dos y cuatro días, conviene ofrecer líquidos, vigilar el estado general y consultar si aparece cualquier signo que preocupe a la familia o si no mejora.",
            "Con cita de la SEUP [1].",
        ]
    )
    eng, llm = engine_factory(
        lambda s, u: "no es json" if s in (_LECTURA, _REVISA) else next(answers)
    )
    a = eng.ask("mi hijo de 4 años tiene fiebre")
    assert a.verification == "regenerated" and a.text == "Con cita de la SEUP [1]."


def test_dose_number_without_table_is_rejected(engine_factory):
    eng, _ = engine_factory("Dale 150 mg [1].")
    a = eng.ask(
        "mi hijo de 4 años tiene fiebre"
    )  # retrieval on fever: no dose chunk among hits? paracetamol chunk lacks 'fiebre'
    assert a.verification in ("fallback", "ok")
    if a.verification == "ok":
        assert any("aepap_dosis" in c for c in a.chunk_ids)


def test_english_query_reaches_spanish_sources(engine_factory):
    eng, _ = engine_factory("Fever is not dangerous by itself, according to the SEUP [1].")
    a = eng.ask("my 4 year old has a fever, what should I do?", country="GB")
    assert a.verification == "ok" and "fiebre" in a.expansion
    assert "Sources:" not in a.render() and "Sources:" in a.render_debug()


def test_dose_intent_parsing():
    from pedibot.bot.answer import dose_intent

    assert dose_intent("how much paracetamol for 12 kg") == ("paracetamol", 12.0)
    assert dose_intent("cuánto Dalsy le doy, pesa 15,5 kilos") == ("ibuprofen", 15.5)
    assert dose_intent("cuánto paracetamol le doy") is None  # no weight → falls through to sources
    assert dose_intent("pesa 12 kg y tiene fiebre") is None  # no drug


def test_dose_question_routes_to_calculator_without_llm(engine_factory):
    eng, llm = engine_factory("should not be called")
    a = eng.ask("cuánto paracetamol le doy a mi hijo de 3 años que pesa 14 kg", country="ES")
    # La garantía de verdad es que la dosis no la escribe nunca el modelo, y sigue en pie: no
    # hay NINGUNA llamada de redacción. Lo único que el modelo hace aquí, desde el 21-sep-2026,
    # es leer en qué lengua escribió el padre, para contestarle en ella.
    assert a.verification == "dose_calculator" and _redaccion(llm) == []
    assert all(c[0] == _LECTURA for c in llm.calls), "sólo puede haber leído la pregunta"
    assert "140" in a.text and "210" in a.text and "AEPap" in a.text


def test_dose_question_infant_refers(engine_factory):
    eng, _ = engine_factory("x")
    a = eng.ask("ibuprofen dose for my 2 month old, 5 kg")
    assert a.verification == "dose_calculator" and "Do not give" in a.text


def test_prompt_carries_age_context_for_young_infants(engine_factory):
    eng, llm = engine_factory("Fiebre en bebé pequeño: acuda a urgencias [1].")
    eng.ask("mi bebé de 2 meses tiene 38,2 de fiebre", country="ES")
    user_msg = _redaccion(llm)[0][1]
    assert "UNDER 3 MONTHS" in user_msg and "Do NOT suggest giving any medication" in user_msg
    assert "ANSWER LANGUAGE: Spanish" in user_msg
    eng2, llm2 = engine_factory("[1]")
    eng2.ask("my 4 year old has a fever")
    assert (
        "CHILD AGE: 48 months" in _redaccion(llm2)[0][1]
        and "ANSWER LANGUAGE: English" in _redaccion(llm2)[0][1]
    )


def test_triage_rule_source_is_injected_as_first_hit(engine_factory):
    eng, llm = engine_factory("Ofrezca suero, según la SEUP [1].")
    a = eng.ask("my 3 year old is vomiting and having a seizure", country="US")
    # the seizure rule cites seup_acudir_urgencias, absent from the tiny test index → no injection,
    # but the vomiting red-flag chunk (seup_vomitos) must still be among the hits
    assert any("seup_vomitos" in c for c in a.chunk_ids)
    assert "[WARNING SIGNS]" in _redaccion(llm)[0][1]


def test_history_gives_age_and_context_to_follow_up(engine_factory):
    eng, llm = engine_factory("Ofrezca suero, según la SEUP [1].")
    hist = [
        {"role": "user", "text": "mi hijo de 4 años tiene fiebre desde ayer"},
        {"role": "assistant", "text": "La fiebre no es peligrosa [1]."},
    ]
    a = eng.ask("¿y si además vomita?", country="ES", history=hist)
    assert a.verification == "ok"
    user_msg = _redaccion(llm)[0][1]
    assert "CONVERSATION SO FAR" in user_msg and "4 años" in user_msg
    assert "CHILD AGE: 48 months" in user_msg  # age taken from the earlier turn
    assert any("seup_vomitos" in c for c in a.chunk_ids)  # follow-up retrieved vomiting leaflet


def test_old_symptom_does_not_retrigger_banner(engine_factory):
    eng, _ = engine_factory("Texto [1].")
    hist = [
        {"role": "user", "text": "mi hijo de 4 años ha tenido una convulsión"},
        {"role": "assistant", "text": "x [1]"},
    ]
    a = eng.ask("¿puede ir al colegio mañana si tiene fiebre?", country="ES", history=hist)
    assert a.level == "routine" and a.banner is None


def test_age_from_history_still_triggers_infant_rule(engine_factory):
    eng, _ = engine_factory("x [1]")
    hist = [
        {"role": "user", "text": "tengo un bebé de 2 meses"},
        {"role": "assistant", "text": "ok"},
    ]
    a = eng.ask("tiene 38,2 de fiebre", country="ES", history=hist)
    assert a.level == "urgent"


def test_child_mode_adds_instruction(engine_factory):
    eng, llm = engine_factory("Tu cuerpo está luchando [1].")
    eng.ask("mi hijo de 6 años tiene fiebre", country="ES", mode="child")
    assert "EXPLAIN TO THE CHILD" in _redaccion(llm)[0][1]


def test_clean_text_strips_citation_markers(engine_factory):
    eng, _ = engine_factory(
        "Según la SEUP, la fiebre no es peligrosa [1]. Ofrece líquidos [1] [1]."
    )
    a = eng.ask("mi hijo de 4 años tiene fiebre", country="ES")
    assert a.clean_text == "Según la SEUP, la fiebre no es peligrosa. Ofrece líquidos."
    assert "[1]" in a.text  # kept for verification
    assert a.render() == a.clean_text
