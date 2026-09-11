"""La tilde no puede decidir si hay respuesta o no (11-sep-2026).

De las 345 respuestas de producción, seis acabaron en «no tengo información fiable», **las seis
en castellano**. Una era «le duele el oido desde ayer», con cinco fichas de oído en el corpus.
Mirando qué devolvía el índice antes de la puerta del «fuente o silencio»:

    24.77  matched=0  mlp_es_earinfections  [hoja_padres]
    20.24  matched=0  seup_otitis           [hoja_padres]

**Los documentos correctos estaban ahí y la puerta los tiraba todos.** El índice FTS está creado
con `remove_diacritics 2`, así que guarda «oído» como «oido» y por eso los encontró; el recuento
de términos que decide si un pasaje vale se hace en Python **sobre el texto crudo**, donde la
palabra sigue llevando tilde, y `"oído".startswith("oido")` es falso. Dos alfabetos distintos
para buscar y para contar.

Medido en el índice, escritura por escritura, antes de tocar nada:

| escrito | pasajes | escrito | pasajes |
|---|---|---|---|
| `oído` | 47 | `oido` | 47 |
| `ребёнок` | **0** | `ребенок` | 8 |
| `الحمى` | 20 | `الحمي` | 1 |

O sea: el índice funde la tilde latina **y la ё rusa**, y **no** funde la ى árabe. De ahí salen
las dos reglas de este fichero: lo que se busca y lo que se cuenta tienen que fundir igual, y
fundir **sólo** donde el índice funde — tocar el árabe o el devanagari rompería las dos lenguas
del mercado que el proyecto ataca (las matras de «बुखार» no son adorno: sin ellas es otra
palabra).
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index, query_terms
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    return Retriever(
        Index(ROOT / "index" / "pedibot.db"),
        Synonyms(ROOT / "config" / "synonyms.yaml", ROOT / "config" / "drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(ROOT / "config" / "taxonomia.yaml"),
    )


#: cómo lo escribe un padre con prisa y cómo lo escribe el libro
IGUALES = [
    ("es", "le duele el oido", "le duele el oído"),
    ("es", "tiene diarrea y esta decaido", "tiene diarrea y está decaído"),
    ("ru", "у ребенка температура", "у ребёнка температура"),
    ("fr", "il a de la fievre", "il a de la fièvre"),
    ("pt", "tem febre e nao come", "tem febre e não come"),
]


@pytest.mark.parametrize(("lang", "sin", "con"), IGUALES)
def test_con_tilde_y_sin_tilde_es_la_misma_pregunta(lang: str, sin: str, con: str):
    a, b = query_terms(sin), query_terms(con)
    assert a == b, f"en {lang}, «{sin}» y «{con}» producen consultas distintas: {a} vs {b}"


@pytest.mark.parametrize(("lang", "sin", "con"), IGUALES)
def test_y_las_dos_encuentran_lo_mismo(buscador: Retriever, lang: str, sin: str, con: str):
    x = [h.chunk.doc_id for h in buscador.search(sin, lang)[0]]
    y = [h.chunk.doc_id for h in buscador.search(con, lang)[0]]
    assert x == y, f"en {lang}, la tilde cambia los resultados:\n  sin: {x}\n  con: {y}"


PREGUNTAS_REALES = [
    ("le duele el oido desde ayer", "ear"),
    ("le duele el oído desde ayer", "ear"),
]


@pytest.mark.parametrize(("pregunta", "asunto"), PREGUNTAS_REALES)
def test_la_pregunta_real_del_registro_ya_se_responde(
    buscador: Retriever, pregunta: str, asunto: str
):
    """Del registro de producción, 9-sep-2026 15:40. Se quedó sin respuesta teniendo cinco fichas."""
    hits, _ = buscador.search(pregunta, "es")
    assert hits, f"«{pregunta}» sigue sin devolver nada"
    docs = [h.chunk.doc_id for h in hits]
    assert any("otitis" in d or "ear" in d for d in docs), (
        f"«{pregunta}» devuelve {docs[:3]}, y ninguno es de oído"
    )


#: Lo que NO se puede fundir. El árabe y el devanagari no llevan «tildes»: llevan letras.
NO_SE_TOCAN = [
    ("ar", "الحمى"),  # la ى final no es una ي: el índice las distingue (20 pasajes contra 1)
    ("hi", "बुखार"),  # las matras no son adorno; sin ellas «बखर» es otra cosa
    ("ar", "طفلي مصاب بالحمى"),
    ("hi", "मेरे बच्चे को बुखार है"),
]


@pytest.mark.parametrize(("lang", "texto"), NO_SE_TOCAN)
def test_al_arabe_y_al_hindi_no_se_les_quita_nada(lang: str, texto: str):
    for t in query_terms(texto):
        assert t in texto.lower(), (
            f"en {lang}, «{t}» no aparece tal cual en «{texto}»: se le ha quitado algo a la palabra"
        )


#: Las seis preguntas reales del registro de producción que acabaron en «no tengo información
#: fiable sobre esto». Tres eran fallos y tres negativas correctas — y ésas también hay que
#: fijarlas, porque un buscador que responde a todo es peor que uno que calla.
DEL_REGISTRO = [
    ("Cuando dalsy le doy a mi hijo?", True, "Dalsy es ibuprofeno y hay calculadora"),
    ("le duele el oido desde ayer", True, "cinco fichas de oído en el corpus"),
    ("le sangro la nariz un momento y ya ha parado", True, "nhs_en_nosebleed está indexado"),
    ("le molesta la luz cuando lee", False, "oftalmología: fuera de alcance"),
    ("tiene los pies frios porque va descalzo por casa", False, "no es una consulta"),
    ("mi perro se ha comido una tableta de chocolate", False, "es un perro"),
]


@pytest.mark.parametrize(("pregunta", "debe_responder", "porque"), DEL_REGISTRO)
def test_las_seis_del_registro(
    buscador: Retriever, pregunta: str, debe_responder: bool, porque: str
):
    hits, _ = buscador.search(pregunta, "es")
    if debe_responder:
        assert hits, f"«{pregunta}» sigue sin devolver nada, y {porque}"
    else:
        assert not hits, (
            f"«{pregunta}» devuelve {[h.chunk.doc_id for h in hits[:3]]} y no debería: {porque}"
        )
