"""Hindi escrito con letras latinas, que es como teclea media India (16-sep-2026).

Un padre indio con un teclado del móvil escribe «bachche ko bukhar hai», no «बच्चे को बुखार है».
La tabla hindi ya tenía 76 claves romanizadas —alguien lo vio venir— y aun así **6 de 15
preguntas corrientes no encontraban NADA**, por dos motivos que no son el vocabulario:

1. **La ortografía varía y nadie la fija**: la clave era «kaan dard» y el padre escribe «kan me
   dard»; «daant nikal» contra «dant nikal rahe hain»; «daane» contra «dane». En la
   transliteración, la vocal larga se escribe doblada o no según quien teclee.
2. **Una frase de dos palabras se parte**: entre las dos se cuela «me», «par» o «ka», y la clave,
   que casa como frase literal, deja de casar.

Se arregla en el emparejador y no con doscientas variantes: para el hindi, las vocales dobladas
se pliegan (kaan ≡ kan, daant ≡ dant) y una clave de dos palabras admite una palabra corta en
medio. Lo que NO se toca es el resto de lenguas: esto sólo corre con la tabla hindi.
"""

from __future__ import annotations

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


#: (pregunta tal y como se teclea, expresión que debe aparecer en alguna de las tres primeras)
CASOS = [
    ("bachche ko bukhar hai kya karu", r"fever|fiebre"),
    ("bachche ko dast ho rahe hain", r"diarrh|gastroenteritis"),
    ("bachche ko khansi aur saans lene me dikkat", r"croup|rsv|bronchiolitis|asma|asthma"),
    ("bachche ke kan me dard hai", r"ear|otitis"),
    ("bachcha ulti kar raha hai", r"vomit|norovirus|gastroenteritis"),
    ("bachche ke pet me dard hai", r"abdominal|stomach|dolor_abdominal|constipation|estrenimiento"),
    ("navjat shishu ki dekhbhal kaise kare", r"newborn|recien_nacido|infant"),
    ("bachche ko teeka kab lagwaye", r"vaccin|immunis|immuniz"),
    ("bachche ke sharir par dane nikle hain", r"rash|urticaria|chickenpox|piel"),
    ("bachche ka vajan nahi badh raha", r"growth|weight|nutrition|malnutrition|feeding"),
    ("bachche ko kabz hai", r"constipation|estrenimiento"),
    ("bachche ke dant nikal rahe hain", r"teething|dent"),
    ("bachcha raat ko rota hai", r"colic|crying|soothing"),
    ("chhah mahine ke bachche ko kya khilaye", r"solid|feeding|complementar|weaning"),
    ("bachche ko sir me dard hai", r"headache|cefalea|migraine"),
]


@pytest.mark.parametrize(("pregunta", "esperado"), CASOS)
def test_se_entiende_el_hindi_en_letras_latinas(
    buscador: Retriever, pregunta: str, esperado: str
) -> None:
    import re

    hits, extra = buscador.search(pregunta, "hi")
    assert hits, f"«{pregunta}» no encuentra nada (expansión: {extra})"
    ids = [h.chunk.chunk_id for h in hits[:3]]
    assert any(re.search(esperado, i, re.I) for i in ids), f"«{pregunta}» → {ids}"


def test_las_vocales_dobladas_dan_igual(buscador: Retriever) -> None:
    """«kaan» y «kan» son la misma palabra escrita por dos personas distintas."""
    for a, b in (("kaan dard", "kan dard"), ("daant nikal", "dant nikal"), ("daane", "dane")):
        assert buscador.expand(a, "hi"), a
        assert set(buscador.expand(a, "hi")) == set(buscador.expand(b, "hi")), f"{a} ≠ {b}"


def test_una_palabra_en_medio_no_rompe_la_frase(buscador: Retriever) -> None:
    assert set(buscador.expand("kaan dard", "hi")) <= set(buscador.expand("kaan me dard", "hi"))
    assert set(buscador.expand("pet dard", "hi")) <= set(buscador.expand("pet me dard", "hi"))


def test_y_las_otras_lenguas_no_se_tocan(buscador: Retriever) -> None:
    """El plegado de vocales es del hindi: en castellano «masa» y «maasa» no son lo mismo, y
    una frase inglesa de dos palabras no admite comodines."""
    assert buscador.expand("cool the burn", "en") == buscador.expand("cool the burn", "en")
    assert not buscador.expand("maasa", "es")
    # «stomach bug» es frase literal en inglés: no puede casar con una palabra en medio
    assert set(buscador.expand("stomach bug", "en")) != set()
    assert not set(buscador.expand("stomach the bug", "en")) >= set(
        buscador.expand("stomach bug", "en")
    )
