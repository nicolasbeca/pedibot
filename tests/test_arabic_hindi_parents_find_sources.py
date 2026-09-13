"""Lo que un padre de la India o del Golfo pregunta, y la ficha que lo contesta (13-sep-2026).

Batería de 71 preguntas de padre en árabe e hindi contra el índice real: 4 en hindi y 8 en árabe
no encontraban **nada**, y dos encontraban la ficha equivocada. En todos los casos la ficha
existía —en inglés o en su lengua—; faltaba la palabra con que lo dice un padre:

- hindi: nariz tapada («नाक बंद»), piojos («जूँ»), qué darle de comer a los seis meses
  («क्या खिलाना»), queroseno, dentición (salía la ficha de salud bucodental en castellano),
  desmayo (salía el síncope en castellano en vez del inglés que el padre puede abrir).
- árabe: dentición («يسنن»), anemia sin artículo («فقر دم» — la taxonomía sólo tenía «فقر الدم»),
  ojos rojos con legañas, pis en la cama («يبلل الفراش»), agua hirviendo, queroseno, pérdida de
  conciencia («فقد الوعي»), no habla todavía, pantallas.

Y un error de fondo en hindi: **«बच्चा» se expandía a «bebé / lactante / infant»**. Es la
palabra con que cualquier padre dice «mi hijo», tenga dos meses o doce años, así que toda
pregunta con ella se inclinaba hacia las fichas del lactante: «मेरा बच्चा मोबाइल बहुत देखता है»
(«mira mucho el móvil») acababa en la ficha de **cólicos del lactante**. «शिशु» sí es bebé, y se
queda.
"""

from __future__ import annotations

import re

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
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


#: (lengua, pregunta, las fichas que la contestan: una de ellas entre las tres primeras)
CASOS = [
    ("hi", "बच्चे की नाक बंद है और वह रात को सो नहीं पाता", r"commoncold|catarro"),
    ("hi", "बच्चे के सिर में जूँ हैं", r"lice|headlice"),
    ("hi", "छह महीने के बच्चे को क्या खिलाना शुरू करूँ?", r"solid|complementar|feeding|nutrition"),
    ("hi", "बच्चे ने मिट्टी का तेल पी लिया", r"poisoning|intoxicacion"),
    ("hi", "बच्चे के दाँत निकल रहे हैं और वह चिड़चिड़ा है", r"teething"),
    ("hi", "बच्चा बेहोश हो गया है", r"mlp_en_fainting"),
    ("hi", "मेरा बच्चा मोबाइल बहुत देखता है", r"physical_activity_under5"),
    ("hi", "मेरा बच्चा 2 साल का है और अभी तक बोलता नहीं", r"milestone|development"),
    # encontraba algo sólo gracias a «बच्चा → baby»: al quitarlo se quedó sin fuente
    ("hi", "बच्चा रात को बिस्तर गीला करता है", r"bedwetting"),
    # escozor al orinar: «حرقة» / «जलन» son ARDOR, no quemadura; iban a la ficha de quemaduras
    ("hi", "मेरे बच्चे को पेशाब में जलन होती है", r"urinary"),
    ("hi", "बच्चे को पेशाब करते समय दर्द होता है", r"urinary"),
    ("ar", "طفلي يشعر بحرقة عند التبول", r"urinary"),
    ("ar", "ابنتي تتألم عند التبول", r"urinary"),
    ("en", "it burns when my child pees", r"urinary"),
    ("ar", "طفلي يسنن وهو متضايق", r"teething"),
    ("ar", "طفلي عنده فقر دم", r"anaemia"),
    ("ar", "عيون طفلي حمراء وفيها إفرازات", r"conjunctivitis|pinkeye"),
    ("ar", "طفلي يبلل الفراش في الليل", r"bedwetting"),
    ("ar", "انسكب ماء مغلي على يد طفلي", r"burns"),
    ("ar", "احترقت يد ابني بالماء الساخن", r"burns"),
    ("ar", "طفلي عنده حرق في يده", r"burns"),
    ("ar", "شرب طفلي الكاز", r"poisoning|intoxicacion"),
    ("ar", "طفلي فقد الوعي", r"fainting|sincope"),
    ("ar", "طفلي عمره سنتان ولا يتكلم", r"milestone|development"),
    ("ar", "طفلي يقضي وقتا طويلا على الشاشة", r"physical_activity_under5"),
]


@pytest.mark.parametrize(
    ("lang", "q", "esperado"), CASOS, ids=[f"{c[0]}-{n}" for n, c in enumerate(CASOS)]
)
def test_la_pregunta_llega_a_su_ficha(buscador: Retriever, lang: str, q: str, esperado: str):
    hits, _ = buscador.search(q, lang)
    top = [h.chunk.doc_id for h in hits[:3]]
    assert any(re.search(esperado, d) for d in top), (
        f"«{q}» ({lang}) → {top}; esperaba /{esperado}/"
    )


def test_hijo_en_hindi_no_es_lactante(buscador: Retriever):
    """«बच्चा» es «niño» a cualquier edad; no puede arrastrar la pregunta a las fichas del bebé."""
    _, extra = buscador.search("मेरा बच्चा मोबाइल बहुत देखता है", "hi")
    assert not {"bebé", "lactante", "baby", "infant"} & set(extra), extra
    _, extra = buscador.search("मेरे शिशु को बुखार है", "hi")
    assert {"baby", "infant"} & set(extra), "«शिशु» sí es bebé y tiene que seguir expandiéndose"
