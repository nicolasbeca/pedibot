"""Cuarenta preguntas de casa, en hindi y en árabe, contra el índice real (16-sep-2026).

La batería del 13-sep buscaba huecos raros —queroseno, agua hirviendo, pis en la cama—. Esta
pregunta lo más corriente que hay: fiebre, vómitos, llanto, qué darle de comer. Y ahí salieron
cinco huecos que no se veían, todos del mismo tipo: **la ficha existe en inglés y el padre no
llega a ella**, porque falta la palabra con que él lo dice.

    बच्चे को छह महीने में क्या खिलाएं   → ninguna fuente (existe nhs_en_babys_first_solid_foods)
    बच्चे के सिर में चोट लगी            → ninguna (existe nhs_en_head_injury_and_concussion)
    طفلي يبكي كثيرا في الليل            → ninguna (existen nhs_en_colic y soothing_a_crying_baby)
    وزن طفلي لا يزيد                    → ninguna (existe todo el material de crecimiento)
    بچ… उल्टी / يتقيأ                   → sólo hojas de la SEUP, en castellano

Se mide lo que importa para estos dos mercados y que ninguna otra prueba mide: que la pregunta
encuentre algo, y que **algo de lo que encuentre esté en una lengua que ese padre pueda abrir**
(la suya o el inglés — ver READABLE_FALLBACK). Una fuente que no puede abrir no es una fuente:
comprobar es lo único que este producto ofrece por encima de un buscador.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import ROOT

LEGIBLES = {"hi": {"hi", "en"}, "ar": {"ar", "en"}}


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    return Retriever(
        Index(ROOT / "index" / "pedibot.db"),
        Synonyms(ROOT / "config" / "synonyms.yaml", ROOT / "config" / "drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(ROOT / "config" / "taxonomia.yaml"),
    )


HINDI = [
    "मेरे बच्चे को बुखार है, क्या करूँ?",
    "बच्चे को दस्त हो रहे हैं",
    "बच्चे को खांसी और सांस लेने में दिक्कत",
    "बच्चे के कान में दर्द है",
    "बच्चा उल्टी कर रहा है",
    "बच्चे को पेट में दर्द है",
    "नवजात शिशु की देखभाल कैसे करें",
    "बच्चे को टीका कब लगवाएं",
    "स्तनपान कैसे कराएं",
    "बच्चे के शरीर पर दाने निकले हैं",
    "बच्चे का वजन नहीं बढ़ रहा",
    "बच्चे को कब्ज है",
    "बच्चे के दाँत निकल रहे हैं",
    "बच्चा रात को रोता है",
    "बच्चे को छह महीने में क्या खिलाएं",
    "बच्चे को निमोनिया के लक्षण",
    "बच्चे का मल पीला है",
    "बच्चे को बुखार के साथ झटके आए",
    "बच्चे की आँख लाल है",
    "बच्चे के सिर में चोट लगी",
]

ARABE = [
    "طفلي عنده حمى، ماذا أفعل؟",
    "طفلي يعاني من الإسهال",
    "طفلي يسعل ويجد صعوبة في التنفس",
    "طفلي يشكو من ألم في الأذن",
    "طفلي يتقيأ",
    "طفلي يشكو ألم في البطن",
    "كيف أعتني بالمولود الجديد",
    "متى يأخذ طفلي التطعيمات",
    "كيف أرضع طفلي رضاعة طبيعية",
    "ظهر طفح جلدي على جسم طفلي",
    "وزن طفلي لا يزيد",
    "طفلي يعاني من الإمساك",
    "طفلي يسنن",
    "طفلي يبكي كثيرا في الليل",
    "ماذا أطعم طفلي في عمر ستة أشهر",
    "أعراض الالتهاب الرئوي عند الأطفال",
    "براز طفلي أصفر",
    "طفلي أصيب بتشنج مع الحمى",
    "عين طفلي حمراء",
    "طفلي أصيب بضربة في الرأس",
]


@pytest.mark.parametrize("pregunta", HINDI)
def test_un_padre_indio_encuentra_algo(buscador: Retriever, pregunta: str) -> None:
    hits, extra = buscador.search(pregunta, "hi")
    assert hits, f"«{pregunta}» no encuentra ninguna ficha (expansión: {extra})"


@pytest.mark.parametrize("pregunta", ARABE)
def test_un_padre_del_golfo_encuentra_algo(buscador: Retriever, pregunta: str) -> None:
    hits, extra = buscador.search(pregunta, "ar")
    assert hits, f"«{pregunta}» no encuentra ninguna ficha (expansión: {extra})"


@pytest.mark.parametrize("pregunta", HINDI)
def test_y_puede_abrir_alguna_de_las_tres_primeras_hi(buscador: Retriever, pregunta: str) -> None:
    hits, _ = buscador.search(pregunta, "hi")
    idiomas = [h.chunk.lang for h in hits[:3]]
    assert set(idiomas) & LEGIBLES["hi"], f"«{pregunta}» se responde sólo con {idiomas}"


@pytest.mark.parametrize("pregunta", ARABE)
def test_y_puede_abrir_alguna_de_las_tres_primeras_ar(buscador: Retriever, pregunta: str) -> None:
    hits, _ = buscador.search(pregunta, "ar")
    idiomas = [h.chunk.lang for h in hits[:3]]
    assert set(idiomas) & LEGIBLES["ar"], f"«{pregunta}» se responde sólo con {idiomas}"


def test_la_mayoria_de_lo_citado_se_puede_leer(buscador: Retriever) -> None:
    """El suelo del conjunto, no de cada pregunta: medido el 16-sep en 77 % (hi) y 94 % (ar)."""
    for lang, preguntas in (("hi", HINDI), ("ar", ARABE)):
        total = buenos = 0
        for q in preguntas:
            hits, _ = buscador.search(q, lang)
            for h in hits[:3]:
                total += 1
                buenos += h.chunk.lang in LEGIBLES[lang]
        share = buenos / max(1, total)
        assert share >= 0.80, f"{lang}: sólo el {share:.0%} de lo citado se puede leer"
