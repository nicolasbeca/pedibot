"""Respira mal y nadie ha dicho por qué: nada de los consejos de una enfermedad (22-oct-2026).

Batería alemana del 20-oct, con kindergesundheit-info.de en el índice: «mein Sohn bekommt
schlecht Luft und die Rippen ziehen sich beim Atmen ein» (aviso de emergencia, 112) recibía los
consejos del Pseudokrupp del BIÖG —incorporarlo, aire fresco, delante de la nevera abierta— y
«mein 3-jähriges kind atmet sehr schnell…» se contestaba como si fuera VRS. Los pasajes que traía
la búsqueda eran todos de una enfermedad concreta (VRS, catarro, bronquiolitis, crup, neumonía),
y bajo un aviso de emergencia el redactor escribe «lo que dicen las fuentes que se haga mientras
llega la ayuda» con lo que tiene delante: el consejo de otra situación.

El revisor con los pasajes delante se midió el 5-oct y salió peor (L del 5-oct), así que esto lo
decide el código: con la dificultad respiratoria grave y sin una causa nombrada por el padre, los
pasajes de tema respiratorio no llegan al redactor. Si el padre dice «crup», «asma» o «pitos»,
sí: entonces es su situación.
"""

from __future__ import annotations

import pytest

from pedibot.bot.breathing_cause import sin_otra_causa
from pedibot.index.store import Hit
from pedibot.ingest.schema import Chunk


def _hit(chunk_id: str, topic: str) -> Hit:
    c = Chunk(
        chunk_id=chunk_id,
        doc_id=chunk_id.split("#")[0],
        org="X",
        doc_title="t",
        year=None,
        lang="de",
        section="s",
        pages=[1],
        text="…",
        topic=topic,
        doc_type="hoja_padres",
        evidence="organismo_publico",
        usage="publico",
        source_hash="h",
    )
    return Hit(c, 10.0, 1)


HITS = [
    _hit("seup_acudir_urgencias#lead#1", "urgencias"),
    _hit("bioeg_de_erkrankungen_rs_virus_infektion_84d23e#rs_virus_infektion#1", "respiratorio"),
    _hit("bioeg_de_erkrankungen_pseudokrupp_kruppsyndrom_133851#was_tun_bei_einem_anfall#1", "respiratorio"),
    _hit("seup_bronquiolitis#cuales_son_los_sintomas#1", "respiratorio"),
]


@pytest.mark.parametrize(
    "pregunta",
    [
        "mein Sohn bekommt schlecht Luft und die Rippen ziehen sich beim Atmen ein",
        "mein 3-jähriges kind atmet sehr schnell und die rippen ziehen sich ein",
        "my son is struggling to breathe and his ribs are pulling in",
        "a mi hijo le cuesta mucho respirar y se le marcan las costillas",
    ],
)
def test_no_disease_advice_when_no_cause_was_named(pregunta: str) -> None:
    quedan = [h.chunk.chunk_id for h in sin_otra_causa(HITS, pregunta, {"severe_breathing"})]
    assert quedan == ["seup_acudir_urgencias#lead#1"], quedan


@pytest.mark.parametrize(
    "pregunta",
    [
        "mein Kind hat Pseudokrupp und bekommt schlecht Luft",
        "bellender Husten und die Rippen ziehen sich ein",
        "my asthmatic son can't breathe, the inhaler isn't working",
        "tiene bronquiolitis y se le marcan las costillas",
        "my baby has RSV and is struggling to breathe",
        "tiene pitos y le cuesta respirar",
    ],
)
def test_the_named_cause_keeps_its_passages(pregunta: str) -> None:
    assert sin_otra_causa(HITS, pregunta, {"severe_breathing"}) == HITS


def test_other_rules_are_untouched() -> None:
    q = "mein Sohn bekommt schlecht Luft"
    assert sin_otra_causa(HITS, q, {"fever_infant"}) == HITS


def test_never_leaves_the_writer_with_nothing() -> None:
    solo_enfermedad = HITS[1:]
    q = "my son is struggling to breathe and his ribs are pulling in"
    assert sin_otra_causa(solo_enfermedad, q, {"severe_breathing"}) == solo_enfermedad


def test_the_engine_applies_it() -> None:
    """Con el índice de verdad: la pregunta de la batería ya no lleva el Pseudokrupp al redactor."""
    from pedibot.eval import FakeProvider, fake_engine_from_settings

    eng = fake_engine_from_settings()
    eng.llm = FakeProvider("Bleiben Sie bei Ihrem Kind, so die SEUP [1].")
    a = eng.ask(
        "mein Sohn bekommt schlecht Luft und die Rippen ziehen sich beim Atmen ein",
        country="DE",
        lang="de",
    )
    assert a.level == "emergency"
    assert a.chunk_ids, "sin pasajes"
    assert not any("pseudokrupp" in c or "rs_virus" in c for c in a.chunk_ids), a.chunk_ids


def test_the_writer_is_told_not_to_invent_what_to_do() -> None:
    """Sin los pasajes de enfermedad no queda ninguno que diga qué hacer mientras llega la ayuda
    (la hoja de la SEUP es una lista de cuándo llamar al 112), y el redactor se lo inventaba con
    su cita: «keep your son upright… do not give him anything to eat or drink [1]» (22-oct)."""
    from pedibot.eval import FakeProvider, fake_engine_from_settings

    from pedibot.bot.breathing_cause import NOTA_SIN_CAUSA

    eng = fake_engine_from_settings()
    eng.llm = FakeProvider("Severe difficulty breathing needs emergency care, says the SEUP [1].")
    eng.ask("my son is struggling to breathe and his ribs are pulling in", country="US", lang="en")
    assert any(NOTA_SIN_CAUSA in user for _, user in eng.llm.calls)

    eng.llm = FakeProvider("Croup causes a barking cough, says the NHS [1].")
    eng.ask("my son has croup and is struggling to breathe", country="US", lang="en")
    assert not any(NOTA_SIN_CAUSA in user for _, user in eng.llm.calls)
