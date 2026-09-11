"""El árabe no llegaba a sus propios documentos (11-sep-2026).

El índice tiene **38 fichas de la OMS en árabe** —malaria, diarrea, rabia, tifoidea,
desnutrición, sarampión, neumonía, lactancia, mordedura de serpiente, tétanos—. Medidas diez
preguntas escritas como las escribe un padre árabe: **sólo dos llegaban a un documento en árabe**,
y **cuatro no devolvían absolutamente nada**. «عض كلب ابني» —«un perro ha mordido a mi hijo»—
devolvía cero resultados teniendo `who_ar_rabies` indexado.

La causa es la morfología, no el corpus. En árabe el artículo y las preposiciones se **pegan** a
la palabra: la ficha de la OMS escribe «الملاريا» 55 veces, «بالملاريا» 19 y «للملاريا» 16, y la
forma desnuda «ملاريا» **una sola vez**. El índice casa por prefijo, así que una pregunta que
escribe la palabra desnuda no alcanza ninguna de esas 90 apariciones, y una que la escribe con
artículo no alcanza la desnuda. **El 32 % de las palabras árabes del corpus empiezan por «ال».**

Esto fija que cada pregunta llegue a SU ficha. Es el mercado que el proyecto ha decidido atacar:
si el árabe no encuentra lo que ya está indexado en árabe, no hay producto que ofrecer.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

#: pregunta → el documento que tiene que salir
PREGUNTAS: dict[str, str] = {
    "ابني مصاب بالحمى والقشعريرة، هل هي ملاريا؟": "who_ar_malaria",
    "طفلي لديه إسهال شديد وجفاف": "who_ar_diarrhoeal_disease",
    "عض كلب ابني، ماذا أفعل؟": "who_ar_rabies",
    "هل يمكن أن يكون طفلي مصابا بالتيفوئيد؟": "who_ar_typhoid",
    "طفلي نحيف جدا ولا يزداد وزنه": "who_ar_malnutrition",
    "ابني لديه طفح جلدي وحمى، هل هي الحصبة؟": "who_ar_measles",
    "طفلي يتنفس بسرعة وسعال، هل هو التهاب رئوي؟": "who_ar_pneumonia",
    "هل يمكن أن يكون طفلي مصابا بحمى الضنك؟": "who_ar_dengue_and_severe_dengue",
    "كم من الوقت يجب أن أرضع طفلي؟": "who_ar_infant_and_young_child_feeding",
    "لدغت أفعى ابني": "who_ar_snakebite_envenoming",
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
def test_la_pregunta_arabe_llega_a_su_ficha(buscador: Retriever, pregunta: str):
    esperado = PREGUNTAS[pregunta]
    hits, _ = buscador.search(pregunta, "ar")
    docs = [h.chunk.doc_id for h in hits[:4]]
    assert docs, f"«{pregunta}» no devuelve NADA, y {esperado} está indexado"
    assert esperado in docs, f"«{pregunta}» no alcanza {esperado}; devuelve {docs}"
