"""Si el plan nombra la ficha en la lengua del lector, la guía de esa lengua la usa (29-sep-2026).

Medido: en **38 de 145** pares tema-lengua la guía no recogía la ficha de su propia lengua, aunque
el plan la nombraba como ancla. 21 eran árabes —dengue, rabia, tétanos, sepsis, cólera…—: la guía
árabe se escribía con fichas inglesas que su lector no puede abrir, con la de la OMS en árabe
dentro del índice desde el 3-sep.

El buscador es léxico y la consulta de cada tema está en castellano e inglés, así que una ficha
en árabe, en ruso o en francés sólo aparecía si alguna palabra coincidía por casualidad. Lo
destapó el publicador diciendo «no sources for topic tuberculosis»; la regla no dependía de ese
tema. Un ancla es una decisión tomada a mano: se usa, la encuentre o no la búsqueda.
"""

from __future__ import annotations

import sqlite3

import pytest

from pedibot.publish.articles import TOPIC_PLAN, gather_hits
from pedibot.settings import ROOT

INDEX = ROOT / "index" / "pedibot.db"


def _anclas_por_lengua() -> list[tuple[str, str, list[str]]]:
    con = sqlite3.connect(f"file:{INDEX}?mode=ro", uri=True)
    try:
        info = {
            d: (lang, uso)
            for d, lang, uso in con.execute(
                "SELECT DISTINCT doc_id, json_extract(data, '$.lang'), json_extract(data, '$.usage')"
                " FROM chunks"
            )
        }
    finally:
        con.close()
    out = []
    for tema, plan in TOPIC_PLAN.items():
        por_lengua: dict[str, list[str]] = {}
        for d in plan.get("docs") or []:  # type: ignore[union-attr]
            lang, uso = info.get(d, (None, None))
            if lang and uso == "publico":
                por_lengua.setdefault(lang, []).append(d)
        out += [(tema, lang, docs) for lang, docs in por_lengua.items()]
    return out


@pytest.fixture(scope="module")
def index():
    if not INDEX.exists():
        pytest.skip("sin índice en esta copia")
    from pedibot.index.store import Index

    return Index(INDEX)


def test_la_guia_arabe_del_dengue_usa_la_ficha_arabe(index):
    ids = {h.chunk.doc_id for h in gather_hits(index, "dengue", lang="ar")}
    assert "who_ar_dengue_and_severe_dengue" in ids


def test_cada_ancla_llega_a_la_guia_de_su_lengua(index):
    sin = []
    for tema, lang, docs in _anclas_por_lengua():
        ids = {h.chunk.doc_id for h in gather_hits(index, tema, lang=lang)}
        if not ids & set(docs):
            sin.append(f"{tema}/{lang}")
    assert not sin, f"guías que no usan la ficha de su propia lengua: {sin}"


def test_el_ancla_de_otra_lengua_no_se_cuela(index):
    """Traer la ficha árabe a la guía inglesa no ayuda a nadie: se trae la de la lengua del lector."""
    ids = {h.chunk.doc_id for h in gather_hits(index, "dengue", lang="en")}
    assert "who_ar_dengue_and_severe_dengue" not in ids
