"""El hindi no tiene corpus propio: todo depende del puente (11-sep-2026).

De los 419 documentos del índice, **cero están en hindi** —el único candidato con licencia
abierta, el manual de ASHA, resultó estar compuesto en Krutidev y no contiene ni un carácter
devanagari (L128)—. Así que toda pregunta en hindi tiene que cruzar a la ficha inglesa por la
tabla `hi_en`, y lo que no esté en esa tabla **no existe** para un padre indio.

Medidas diez preguntas por las enfermedades que pesan en la India: llegaban **siete**. Las tres
que no: «मेरे बच्चे को कुत्ते ने काट लिया» —«a mi hijo le ha mordido un perro»— devolvía
**cero resultados** teniendo la ficha de rabia de la OMS indexada, que en la India es la urgencia
de horas; la desnutrición devolvía la guía de **obesidad** de la AAP; y el perro, la delgadez y
el sarampión no estaban en el puente.

Esto fija que cada pregunta llegue a su ficha. Es el otro mercado que el proyecto ataca, y el
más frágil de los dos, porque aquí no hay documento propio que sirva de red.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

#: pregunta → trozo del identificador del documento que tiene que salir
PREGUNTAS: dict[str, str] = {
    "क्या मेरे बच्चे को मलेरिया हो सकता है?": "malaria",
    "क्या मेरे बच्चे को डेंगू है?": "dengue",
    "मेरे बच्चे को दस्त और निर्जलीकरण है": "diarrho",
    "मेरे बच्चे को बुखार और दाने हैं, क्या यह खसरा है?": "measles",
    "मेरा बच्चा तेज़ साँस ले रहा है, क्या यह निमोनिया है?": "pneumonia",
    "मेरे बच्चे को कुत्ते ने काट लिया, क्या करूँ?": "rabies",
    "क्या मेरे बच्चे को टाइफाइड है?": "typhoid",
    "मेरा बच्चा बहुत दुबला है और वजन नहीं बढ़ रहा": "malnutrition",
    "मुझे अपने बच्चे को कब तक स्तनपान कराना चाहिए?": "feeding",
    "मेरे बच्चे को साँप ने काट लिया": "snakebite",
}


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    s = get_settings()
    return Retriever(
        Index(s.index_db_path),
        Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
    )


@pytest.mark.parametrize("pregunta", sorted(PREGUNTAS))
def test_la_pregunta_hindi_llega_a_su_ficha(buscador: Retriever, pregunta: str):
    esperado = PREGUNTAS[pregunta]
    hits, _ = buscador.search(pregunta, "hi")
    docs = [h.chunk.doc_id for h in hits[:4]]
    assert docs, f"«{pregunta}» no devuelve NADA, y hay ficha de «{esperado}» indexada"
    assert any(esperado in d for d in docs), (
        f"«{pregunta}» no alcanza ninguna ficha de «{esperado}»; devuelve {docs}"
    )
