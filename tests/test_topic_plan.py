"""El plan de temas se agotó y nadie se enteró (11-sep-2026).

Buscando por qué Bluesky llevaba una semana callado apareció que la última guía era del 5 de
septiembre. La primera explicación fue que no había ningún timer que publicara — cierto —, pero
debajo estaba la de verdad: **`pending_topics` devolvía cero en los ocho idiomas**. Aunque el
timer hubiera existido, habría corrido cada día sin escribir nada y sin decirlo.

Y al mirar el plan se vio de qué está hecho: fiebre, otitis, dentición, pantallas, piojos. Es
pediatría española y británica. No tenía **desnutrición, ahogamientos, tuberculosis, malaria,
hepatitis ni poliomielitis**, que son los temas que matan y preocupan donde el operador quiere
llevar esto —India y los países árabes— y que el corpus ya sostiene: las fichas de la OMS están
indexadas en cinco lenguas desde el 3 de septiembre.

Tres cosas se fijan aquí:

1. **La cola no puede estar vacía.** Es la condición que hace que publicar a diario signifique
   algo; sin ella el timer es decorativo.
2. **Todo anclaje tiene que existir en el índice**, o el tema no se puede escribir con fuente.
3. **Los temas que el corpus sostiene en varias lenguas tienen que estar en el plan**, porque un
   documento indexado del que no se escribe no lo lee nadie.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from pedibot.publish.articles import TOPIC_PLAN, pending_topics
from pedibot.settings import ROOT

LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")
CONTENT = ROOT / "web" / "content"
INDEX = ROOT / "index" / "pedibot.db"


def _doc_ids() -> set[str]:
    con = sqlite3.connect(f"file:{INDEX}?mode=ro", uri=True)
    try:
        return {r[0] for r in con.execute("SELECT DISTINCT doc_id FROM chunks")}
    finally:
        con.close()


def _titles() -> dict[str, str]:
    con = sqlite3.connect(f"file:{INDEX}?mode=ro", uri=True)
    try:
        out = {}
        for doc_id, data in con.execute("SELECT doc_id, data FROM chunks"):
            out.setdefault(doc_id, json.loads(data).get("doc_title") or "")
        return out
    finally:
        con.close()


def test_todo_anclaje_del_plan_existe_en_el_indice():
    if not INDEX.exists():
        pytest.skip("sin índice en esta copia")
    hay = _doc_ids()
    faltan = {
        t: [d for d in (p.get("docs") or []) if d not in hay]  # type: ignore[union-attr]
        for t, p in TOPIC_PLAN.items()
    }
    faltan = {t: v for t, v in faltan.items() if v}
    assert not faltan, f"temas que no se pueden escribir con fuente: {faltan}"


@pytest.mark.parametrize("lang", LANGS)
def test_siempre_queda_algo_que_publicar(lang: str):
    """Una cola vacía es un timer que corre y no hace nada, y no se nota hasta contar las fechas."""
    if not CONTENT.exists():
        pytest.skip("sin contenido en esta copia")
    quedan = pending_topics(CONTENT, lang)
    assert quedan, (
        f"no queda ni un tema por escribir en {lang}: publicar a diario no produciría nada"
    )


#: Asuntos que el corpus sostiene en varias lenguas y que pesan donde el proyecto quiere llegar.
#: La clave es un trozo del identificador del documento; el valor, en cuántas lenguas está.
ASUNTOS_DEL_CORPUS = ("malnutrition", "drowning", "tuberculosis", "malaria", "hepatitis", "polio")


def test_el_plan_cubre_lo_que_el_corpus_sostiene_en_varias_lenguas():
    if not INDEX.exists():
        pytest.skip("sin índice en esta copia")
    hay = _doc_ids()
    anclados = {d for p in TOPIC_PLAN.values() for d in (p.get("docs") or [])}  # type: ignore[union-attr]
    sin_guia = []
    for asunto in ASUNTOS_DEL_CORPUS:
        docs = {d for d in hay if asunto in d.lower()}
        if docs and not (docs & anclados):
            sin_guia.append((asunto, len(docs)))
    assert not sin_guia, (
        "el corpus tiene estos asuntos indexados y ninguna guía los escribe, así que no los lee "
        f"nadie: {sin_guia}"
    )
