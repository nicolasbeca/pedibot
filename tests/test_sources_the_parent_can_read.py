"""Una fuente que el padre no puede leer no es una fuente (11-sep-2026).

Lo único que este producto ofrece por encima de cualquier buscador es que **la respuesta se
puede comprobar**: cada frase lleva el número del pasaje del que sale y el pasaje está a un clic.
Si ese pasaje está en un idioma que el lector no lee, la comprobación no existe y la cita es
decorativa.

El hindi no tiene **ni un documento propio** —el único candidato con licencia abierta resultó
estar en Krutidev (L128)—, así que siempre hay que puentear a otra lengua, y eso está bien. Lo
que no da igual es **a cuál**. Medido sobre quince preguntas hindi corrientes:

- **47 % de los pasajes citados estaban en castellano**, y **cinco de las quince** se citaban
  entera y exclusivamente con hojas de la SEUP en castellano.
- En la India el inglés es lengua oficial y el segundo idioma de casi cualquier padre
  alfabetizado. El castellano no lo lee nadie allí.

La regla que se fija no prohíbe el castellano —si además de una fuente legible aparece una
española, no molesta—: exige que **al menos una de las fuentes esté en una lengua que ese lector
pueda leer**. Para el hindi y el árabe eso es su propio idioma o el inglés.

Arreglado con un empujón a la lengua puente (`READABLE_FALLBACK`, `FALLBACK_BOOST`), nunca con
un castigo a las demás: castigar al otro lado se midió en agosto y rompió la dirección
inglés→castellano de la que vive el corpus. Se probó 1,7 y se descartó — mejoraba el hindi de 31
a 27 % pero **le quitaba al árabe sus propias fuentes** (29 → 26 %), que es peor.

Dos avisos para quien lea esto dentro de un año:

- El fixture busca **sin expansión por modelo**, para que el candado sea determinista y no
  cueste dinero. En producción, con expansión, lo medido tras el arreglo fue **69 % legible en
  hindi** (antes 53 %) y **81 % en árabe** (antes 69 %). La garantía de verdad es la regla por
  pregunta, no el porcentaje agregado.
- Quedan tres preguntas hindi —tos, dificultad para respirar, neumonía— cuyas mejores fuentes
  del corpus siguen siendo hojas de la SEUP. No es un fallo de diseño: en esos temas el mejor
  documento para padres que hay **está en castellano**. Eso se arregla con corpus, no subiendo
  una constante.
"""

from __future__ import annotations

import pytest
import yaml

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import ROOT

#: Qué puede leer cada lector: su idioma y, si no hay, la lengua franca de su región.
#: No es una opinión sobre las lenguas: es dónde vive el lector.
LEGIBLES = {
    "hi": {"hi", "en"},
    "ar": {"ar", "en"},
    "ru": {"ru", "en"},
    "pt": {"pt", "es", "en"},
}

PREGUNTAS = {
    "hi": [
        "मेरे 2 साल के बच्चे को खाँसी है, क्या करूँ?",
        "मेरे बच्चे को बुखार है, घर पर क्या करूँ?",
        "मेरे बच्चे को कान में दर्द है",
        "मेरे बच्चे को उल्टी हो रही है",
        "मेरे बच्चे को साँस लेने में दिक्कत है",
        "मेरे बच्चे को कब्ज़ है",
        "मेरे बच्चे का टीकाकरण कब होना चाहिए?",
        "मेरे बच्चे को निमोनिया है क्या?",
        "मेरे बच्चे को दस्त हो रहे हैं",
        "मेरे बच्चे को दाने निकले हैं",
    ],
    "ar": [
        "طفلي لديه سعال، ماذا أفعل؟",
        "طفلي يتقيأ",
        "طفلي لديه إمساك",
        "طفلي يشكو من ألم في الأذن",
    ],
}


def _idioma_por_doc() -> dict[str, str]:
    fuera: dict[str, str] = {}
    for f in ("fuentes.yaml", "fuentes_web.yaml"):
        for d in yaml.safe_load((ROOT / "config" / f).read_text(encoding="utf-8"))["sources"]:
            fuera[d["doc_id"]] = d.get("lang", "?")
    return fuera


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    return Retriever(
        Index(ROOT / "index" / "pedibot.db"),
        Synonyms(ROOT / "config" / "synonyms.yaml", ROOT / "config" / "drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(ROOT / "config" / "taxonomia.yaml"),
    )


@pytest.mark.parametrize(
    ("lang", "pregunta"),
    [(lg, q) for lg, qs in PREGUNTAS.items() for q in qs],
)
def test_al_menos_una_fuente_se_puede_leer(buscador: Retriever, lang: str, pregunta: str):
    idiomas = _idioma_por_doc()
    hits, _ = buscador.search(pregunta, lang)
    if not hits:
        pytest.skip("sin resultados: eso lo miran los candados de alcance")
    salen = [idiomas.get(h.chunk.doc_id, "?") for h in hits]
    legibles = LEGIBLES[lang]
    assert any(lg in legibles for lg in salen), (
        f"«{pregunta}» se responde a un lector de {lang} citando sólo {sorted(set(salen))}; "
        f"ese padre no puede comprobar nada, que es lo único que ofrecemos"
    )


@pytest.mark.parametrize("lang", sorted(PREGUNTAS))
def test_y_el_grueso_de_las_citas_tambien(buscador: Retriever, lang: str):
    """Una legible entre seis ilegibles cumple la letra y no el fondo."""
    idiomas = _idioma_por_doc()
    legibles = LEGIBLES[lang]
    dentro = fuera = 0
    for q in PREGUNTAS[lang]:
        hits, _ = buscador.search(q, lang)
        for h in hits:
            lg = idiomas.get(h.chunk.doc_id, "?")
            if lg in legibles:
                dentro += 1
            else:
                fuera += 1
    total = dentro + fuera or 1
    assert dentro / total >= 0.75, (
        f"sólo el {100 * dentro / total:.0f} % de lo que se cita a un lector de {lang} está en "
        f"una lengua que pueda leer ({dentro} de {total})"
    )
