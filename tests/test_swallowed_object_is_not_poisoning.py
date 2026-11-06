"""Un objeto tragado no es una intoxicación (6-nov-2026).

«My 2 year old swallowed a coin» (pruebas 1195 y 1198, India) salía bien de triaje y, debajo,
con la hoja de intoxicaciones de la SEUP: «do not give water, milk, oil», «try to work out how much
was swallowed», «separate the child from whatever is left of the object». Es la regla c) del
prompt, consejo de otra situación, y como en la dificultad respiratoria lo decide el código: con
la regla de objeto tragado o pila de botón, y sin la de intoxicación, los pasajes de tema
`intoxicacion` no llegan al redactor. Si además hay un tóxico (la regla `poisoning`), se quedan.
"""

from __future__ import annotations

from pedibot.bot.swallowed_object import NOTA_OBJETO, sin_hoja_de_toxicos
from pedibot.index.store import Hit
from pedibot.ingest.schema import Chunk


def _hit(chunk_id: str, topic: str) -> Hit:
    c = Chunk(
        chunk_id=chunk_id,
        doc_id=chunk_id.split("#")[0],
        org="X",
        doc_title="t",
        year=None,
        lang="es",
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


URGENCIAS = _hit("seup_acudir_urgencias#comporta_miento#1", "urgencias")
HOJA = _hit("seup_intoxicaciones#que_son#1", "intoxicacion")
OCHO_NO = _hit("seup_toxicos_8_no#transcurridas_8_horas_desde_la_ingesta#1", "intoxicacion")
NHS = _hit("nhs_en_poisoning#poisoning#1", "intoxicacion")
HITS = [URGENCIAS, HOJA, OCHO_NO, NHS]


def _ids(hits: list[Hit]) -> list[str]:
    return [h.chunk.chunk_id for h in hits]


def test_a_swallowed_coin_loses_the_poisoning_sheets() -> None:
    assert _ids(sin_hoja_de_toxicos(HITS, {"foreign_body_ingestion"})) == _ids([URGENCIAS])


def test_a_button_battery_too() -> None:
    assert _ids(sin_hoja_de_toxicos(HITS, {"button_battery", "foreign_body_ingestion"})) == _ids(
        [URGENCIAS]
    )


def test_with_a_real_poison_they_stay() -> None:
    """«проглотил таблетки» salta en las dos: ahí la hoja es la situación del padre."""
    assert sin_hoja_de_toxicos(HITS, {"foreign_body_ingestion", "poisoning"}) == HITS


def test_other_rules_are_left_alone() -> None:
    assert sin_hoja_de_toxicos(HITS, {"severe_breathing"}) == HITS
    assert sin_hoja_de_toxicos(HITS, set()) == HITS


def test_it_never_leaves_the_list_empty() -> None:
    assert sin_hoja_de_toxicos([HOJA, NHS], {"foreign_body_ingestion"}) == [HOJA, NHS]


def test_the_note_forbids_inventing_what_the_sheet_said() -> None:
    nota = NOTA_OBJETO.lower()
    assert "not a poison" in nota
    assert "at home" in nota and "stools" in nota


def test_the_engine_does_not_show_the_sheet_for_a_coin() -> None:
    from pedibot.bot.llm import FakeProvider
    from pedibot.eval import fake_engine_from_settings

    eng = fake_engine_from_settings()
    eng.llm = FakeProvider("Take him to the emergency department today [1].")
    eng.ask("My 2 year old swallowed a coin, what do I do?", country="IN", lang="en")
    borradores = [u for _s, u in eng.llm.calls if "PARENT MESSAGE" in u]
    assert borradores, "el redactor no llegó a escribir"
    assert "not a poison" in borradores[0]
    assert "Separe al niño" not in borradores[0]
