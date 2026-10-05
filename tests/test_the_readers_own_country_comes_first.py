"""Las guías del país del lector delante, cuando dicen lo mismo (5-oct-2026).

Desde que el inglés pasa delante del castellano, a un padre de EE. UU. le llegaba primero el NHS
británico: el juez lo marcaba 71 veces de 415 («cita al NHS en lugar de las guías de EE. UU.»).
No es información errónea, pero si los CDC o MedlinePlus dicen lo mismo, son los suyos. Y al
revés, en el Reino Unido, el NHS. Mismo criterio que la lengua: mismo tema que el primero y al
menos el 60 % de su puntuación; el orden de lo demás no se toca.
"""

from __future__ import annotations

from pedibot.bot.answer import country_sources_first
from pedibot.index.store import Hit
from pedibot.ingest.schema import Chunk


def _h(doc: str, org: str, score: float, topic: str = "fiebre") -> Hit:
    c = Chunk(
        chunk_id=f"{doc}#s#1", doc_id=doc, org=org, doc_title=doc, year=None, lang="en",
        section="S", pages=[1], text="x", topic=topic, doc_type="hoja_padres",
        evidence="organismo_publico", usage="publico", source_hash="h", n_words=1,
    )
    return Hit(c, score, 1)


def test_en_ee_uu_los_cdc_delante_del_nhs() -> None:
    hits = [_h("nhs_fever", "NHS", 10), _h("mlp_fever", "MedlinePlus", 8), _h("seup", "SEUP", 7)]
    assert [h.chunk.org for h in country_sources_first(hits, "US")] == ["MedlinePlus", "NHS", "SEUP"]


def test_en_el_reino_unido_el_nhs_delante() -> None:
    hits = [_h("mlp_fever", "MedlinePlus", 10), _h("nhs_fever", "NHS", 9)]
    assert [h.chunk.org for h in country_sources_first(hits, "GB")] == ["NHS", "MedlinePlus"]


def test_no_sube_lo_que_vale_mucho_menos_o_es_de_otro_tema() -> None:
    hits = [_h("nhs_fever", "NHS", 10), _h("cdc_x", "CDC", 5), _h("mlp_rash", "MedlinePlus", 9, "piel")]
    assert country_sources_first(hits, "US") == hits


def test_otros_paises_no_se_tocan() -> None:
    hits = [_h("nhs_fever", "NHS", 10), _h("mlp_fever", "MedlinePlus", 9)]
    assert country_sources_first(hits, "ES") == hits
    assert country_sources_first(hits, None) == hits
