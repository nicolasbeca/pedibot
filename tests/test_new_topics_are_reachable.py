"""Los temas nuevos se pueden ALCANZAR, no sólo están indexados (11-sep-2026).

Al traer 115 fichas de la OMS —malaria, dengue, tifoidea, anemia, mordedura de serpiente,
lombrices, sarna…— el índice pasó de 291 a 405 documentos y todo parecía hecho. Medido de
verdad, **20 de 35 preguntas no llegaban a su propio documento**.

Dos causas, y las dos ya tenían lección escrita:

1. **Sin categoría en la taxonomía, la puerta del «fuente o silencio» exige tres términos en vez
   de uno** (L76, L112). Ninguno de los temas nuevos estaba clasificado, así que «my child has
   scabies» —que casa una sola palabra— se quedaba fuera *teniendo la ficha delante*.
2. **El hindi no tiene ni un documento propio**, así que toda pregunta hindi tiene que puentear
   al inglés o al castellano, y los puentes no conocían estas enfermedades.

Arreglado lo uno y lo otro: 35 de 35. Esto lo fija, porque un documento que no se alcanza es un
documento que no existe, y desde fuera las dos cosas se leen igual.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms, Taxonomy
from pedibot.index.store import Index
from pedibot.settings import ROOT, get_settings

#: tema → (trozo del doc_id que debería salir, pregunta por idioma)
CASOS: dict[str, tuple[str, dict[str, str]]] = {
    "malaria": (
        "malaria",
        {
            "en": "my child has a fever and we live in a malaria area",
            "es": "mi hijo tiene fiebre y vivimos en zona de malaria",
            "ar": "ابني مصاب بالحمى ونعيش في منطقة بها ملاريا",
            "hi": "मेरे बच्चे को बुखार है और हम मलेरिया वाले इलाके में रहते हैं",
            "fr": "mon enfant a de la fièvre et nous vivons en zone de paludisme",
        },
    ),
    "dengue": (
        "dengue",
        {
            "en": "is this dengue in my child",
            "es": "puede ser dengue en mi hijo",
            "ar": "هل هذه حمى الضنك عند طفلي",
            "hi": "क्या मेरे बच्चे को डेंगू है",
            "fr": "est-ce la dengue chez mon enfant",
        },
    ),
    "typhoid": (
        "typhoid",
        {
            "en": "typhoid fever in children",
            "es": "fiebre tifoidea en niños",
            "ar": "حمى التيفوئيد عند الأطفال",
            "hi": "बच्चों में टाइफाइड बुखार",
            "fr": "fièvre typhoïde chez l'enfant",
        },
    ),
    "anaemia": (
        "anaemia",
        {
            "en": "my child is anaemic",
            "es": "mi hijo tiene anemia",
            "ar": "طفلي مصاب بفقر الدم",
            "hi": "मेरे बच्चे को एनीमिया है",
            "fr": "mon enfant est anémique",
        },
    ),
    "snakebite": (
        "snakebite",
        {
            "en": "my child was bitten by a snake",
            "es": "a mi hijo le ha mordido una serpiente",
            "ar": "لدغت أفعى ابني",
            "hi": "मेरे बच्चे को साँप ने काट लिया",
            "fr": "mon enfant a été mordu par un serpent",
        },
    ),
    "helminths": (
        "helminth",
        {
            "en": "intestinal worms in my child",
            "es": "lombrices intestinales en mi hijo",
            "ar": "ديدان معوية عند طفلي",
            "hi": "मेरे बच्चे के पेट में कीड़े",
            "fr": "vers intestinaux chez mon enfant",
        },
    ),
    "scabies": (
        "scabies",
        {
            "en": "my child has scabies",
            "es": "mi hijo tiene sarna",
            "ar": "طفلي مصاب بالجرب",
            "hi": "मेरे बच्चे को खुजली की बीमारी है",
            "fr": "mon enfant a la gale",
        },
    ),
}


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    s = get_settings()
    if not s.index_db_path.exists():
        pytest.skip("sin índice en esta copia")
    return Retriever(
        Index(s.index_db_path),
        Synonyms(ROOT / "config" / "synonyms.yaml", ROOT / "config" / "drugs.yaml"),
        taxonomy=Taxonomy(ROOT / "config" / "taxonomia.yaml"),
    )


@pytest.mark.parametrize(
    ("tema", "lang"),
    [(tema, lang) for tema, (_, preguntas) in CASOS.items() for lang in preguntas],
)
def test_la_pregunta_llega_a_su_documento(buscador: Retriever, tema: str, lang: str):
    pista, preguntas = CASOS[tema]
    hits, _ = buscador.search(preguntas[lang], lang=lang)
    salieron = [h.chunk.doc_id for h in hits]
    assert any(pista in d for d in salieron), (
        f"«{preguntas[lang]}» ({lang}) no alcanza ninguna ficha de {tema}; salió: {salieron[:4]}"
    )
