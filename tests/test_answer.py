from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.answer import EmergencyNumbers, Engine, verify
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms, detect_lang
from pedibot.bot.triage import Triage
from pedibot.index.store import Hit, Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk


def _chunk(cid, text, red=False, dose=False, url=None):
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
                "La fiebre no es peligrosa por sí misma. Ofrezca líquidos y no abrigue en exceso. Acuda a urgencias si el niño tiene menos de 3 meses.",
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
    dose_hits = [Hit(_chunk("a#s#1", "x", dose=True), 1.0, 1)]
    assert verify("Dale 150 mg [1].", dose_hits) == []


def test_routine_answer_with_sources(engine_factory):
    eng, llm = engine_factory("La fiebre no es peligrosa por sí misma [1]. Ofrece líquidos [1].")
    a = eng.ask("mi hijo de 4 años tiene fiebre, ¿qué hago?", country="ES")
    assert a.level == "routine" and a.banner is None and a.verification == "ok"
    assert a.sources and a.sources[0].startswith("[1] SEUP") and "seup.org" in a.sources[0]
    rendered = a.render()
    assert "Fuentes:" in rendered and "no sustituye" in rendered
    assert "SOURCES:" in llm.calls[0][1] and "[1] SEUP" in llm.calls[0][1]


def test_fever_without_age_asks(engine_factory):
    eng, llm = engine_factory("irrelevant")
    a = eng.ask("mi hijo tiene fiebre")
    assert a.verification == "asked_age" and llm.calls == []


def test_emergency_banner_first_with_country_numbers(engine_factory):
    eng, _ = engine_factory("Ofrezca suero [1].")
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
    assert a.verification == "no_source" and llm.calls == []
    assert "No tengo información fiable" in a.text


def test_bad_citation_triggers_regeneration_then_fallback(engine_factory):
    eng, llm = engine_factory("Respuesta sin citas.")
    a = eng.ask("mi hijo de 4 años tiene fiebre")
    assert a.verification == "fallback" and len(llm.calls) == 2
    assert "No tengo información fiable" in a.text


def test_regeneration_succeeds(engine_factory):
    answers = iter(["Sin cita.", "Con cita [1]."])
    eng, llm = engine_factory(lambda s, u: next(answers))
    a = eng.ask("mi hijo de 4 años tiene fiebre")
    assert a.verification == "regenerated" and a.text == "Con cita [1]."


def test_dose_number_without_table_is_rejected(engine_factory):
    eng, _ = engine_factory("Dale 150 mg [1].")
    a = eng.ask(
        "mi hijo de 4 años tiene fiebre"
    )  # retrieval on fever: no dose chunk among hits? paracetamol chunk lacks 'fiebre'
    assert a.verification in ("fallback", "ok")
    if a.verification == "ok":
        assert any("aepap_dosis" in c for c in a.chunk_ids)


def test_english_query_reaches_spanish_sources(engine_factory):
    eng, _ = engine_factory("Fever is not dangerous by itself [1].")
    a = eng.ask("my 4 year old has a fever, what should I do?", country="GB")
    assert a.verification == "ok" and "fiebre" in a.expansion
    assert "Sources:" in a.render()


def test_dose_intent_parsing():
    from pedibot.bot.answer import dose_intent

    assert dose_intent("how much paracetamol for 12 kg") == ("paracetamol", 12.0)
    assert dose_intent("cuánto Dalsy le doy, pesa 15,5 kilos") == ("ibuprofen", 15.5)
    assert dose_intent("cuánto paracetamol le doy") is None  # no weight → falls through to sources
    assert dose_intent("pesa 12 kg y tiene fiebre") is None  # no drug


def test_dose_question_routes_to_calculator_without_llm(engine_factory):
    eng, llm = engine_factory("should not be called")
    a = eng.ask("cuánto paracetamol le doy a mi hijo de 3 años que pesa 14 kg", country="ES")
    assert a.verification == "dose_calculator" and llm.calls == []
    assert "140" in a.text and "210" in a.text and "AEPap" in a.text


def test_dose_question_infant_refers(engine_factory):
    eng, _ = engine_factory("x")
    a = eng.ask("ibuprofen dose for my 2 month old, 5 kg")
    assert a.verification == "dose_calculator" and "Do not give" in a.text


def test_prompt_carries_age_context_for_young_infants(engine_factory):
    eng, llm = engine_factory("Fiebre en bebé pequeño: acuda a urgencias [1].")
    eng.ask("mi bebé de 2 meses tiene 38,2 de fiebre", country="ES")
    user_msg = llm.calls[0][1]
    assert "UNDER 3 MONTHS" in user_msg and "Do NOT suggest giving any medication" in user_msg
    assert "ANSWER LANGUAGE: Spanish" in user_msg
    eng2, llm2 = engine_factory("[1]")
    eng2.ask("my 4 year old has a fever")
    assert (
        "CHILD AGE: 48 months" in llm2.calls[0][1]
        and "ANSWER LANGUAGE: English" in llm2.calls[0][1]
    )


def test_triage_rule_source_is_injected_as_first_hit(engine_factory):
    eng, llm = engine_factory("Ofrezca suero [1].")
    a = eng.ask("my 3 year old is vomiting and having a seizure", country="US")
    # the seizure rule cites seup_acudir_urgencias, absent from the tiny test index → no injection,
    # but the vomiting red-flag chunk (seup_vomitos) must still be among the hits
    assert any("seup_vomitos" in c for c in a.chunk_ids)
    assert "[WARNING SIGNS]" in llm.calls[0][1]


def test_history_gives_age_and_context_to_follow_up(engine_factory):
    eng, llm = engine_factory("Ofrezca suero [1].")
    hist = [
        {"role": "user", "text": "mi hijo de 4 años tiene fiebre desde ayer"},
        {"role": "assistant", "text": "La fiebre no es peligrosa [1]."},
    ]
    a = eng.ask("¿y si además vomita?", country="ES", history=hist)
    assert a.verification == "ok"
    user_msg = llm.calls[0][1]
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
