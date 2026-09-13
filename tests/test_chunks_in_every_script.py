"""Un pasaje de 1.900 palabras no es un pasaje (13-sep-2026).

Metiendo en el corpus las preguntas de la OMS sobre percentiles, la versión rusa y la árabe
salieron en UN solo pasaje cada una (10.000 y 7.000 caracteres) mientras la francesa salía en
siete. Mirado el índice entero: **48 pasajes por encima del tope de 480 palabras en 23
documentos**, y los peores eran justo los del mercado que se está atacando — la ficha de dengue
de la OMS en árabe eran seis pasajes de unas 1.900 palabras cada uno, y la rusa igual.

La causa estaba en una línea: el separador de frases sólo cortaba delante de una MAYÚSCULA
LATINA (`[A-ZÁÉÍÓÚÑ¿¡•-]`). En cirílico no reconocía la mayúscula, el árabe no tiene mayúsculas y
el devanagari acaba la frase con «।», no con un punto. Sin frases, una sección larga se quedaba
entera: un pasaje que casa con cualquier cosa, que se lleva la puntuación de la búsqueda y que
llena la ventana del modelo de texto que no viene a cuento.
"""

from __future__ import annotations

import json

import pytest

from pedibot.ingest.chunk import MAX_WORDS, _sentences, chunk_section
from pedibot.ingest.extract import Line
from pedibot.ingest.sections import Section
from pedibot.settings import ROOT


@pytest.mark.parametrize(
    ("texto", "n"),
    [
        ("La fiebre no es mala. Ofrezca líquidos. ¿Tiene manchas? Consulte.", 4),
        ("Температура не опасна. Давайте пить. Есть ли сыпь? Обратитесь к врачу.", 4),
        ("الحمى ليست خطيرة. أعطه السوائل. هل لديه طفح؟ استشر الطبيب.", 4),
        ("बुखार खतरनाक नहीं है। पानी पिलाएँ। क्या दाने हैं? डॉक्टर को दिखाएँ।", 4),
    ],
)
def test_las_frases_se_separan_en_las_cuatro_escrituras(texto: str, n: int):
    assert len(_sentences(texto)) == n, _sentences(texto)


def _sec(texto: str, titulo: str = "t") -> Section:
    return Section(title=titulo, lines=[Line(text=texto, size=10.0, bold=False, page=1)])


def _seccion(frase: str, veces: int) -> Section:
    return _sec(" ".join([frase] * veces))


@pytest.mark.parametrize(
    "frase",
    [
        "Лихорадка денге передаётся комарами и чаще всего протекает легко у детей.",
        "تنتقل حمى الضنك عن طريق البعوض وتكون خفيفة غالباً عند الأطفال.",
        "डेंगू मच्छरों से फैलता है और बच्चों में ज़्यादातर हल्का होता है।",
        "Dengue is spread by mosquitoes and is usually mild in children.",
    ],
)
def test_una_seccion_larga_se_parte_en_cualquier_escritura(frase: str):
    trozos = chunk_section(_seccion(frase, 200))
    assert len(trozos) > 1
    assert all(len(c.text.split()) <= MAX_WORDS for c in trozos), [
        len(c.text.split()) for c in trozos
    ]


def test_sin_puntuacion_se_parte_por_palabras():
    """Una lista pegada sin un solo punto tampoco puede quedarse entera."""
    trozos = chunk_section(_sec(" ".join(["palabra"] * 1500)))
    assert len(trozos) > 1 and all(len(c.text.split()) <= MAX_WORDS for c in trozos)


def test_las_tablas_de_dosis_siguen_sin_partirse():
    texto = "Paracetamol 15 mg/kg cada 6 horas. " * 200
    trozos = chunk_section(_sec(texto, "dosis"))
    assert len(trozos) == 1 and trozos[0].is_dose_table


#: Lo que se busca aquí es el gigante, no el borde. Tras el arreglo quedan 9 pasajes entre 481 y
#: 522 palabras en castellano e inglés: la cola de solapamiento más la última frase caen un poco
#: por encima del tope. El fallo eran pasajes de 1.900; 600 lo caza con margen.
GIGANTE = 600


def test_en_el_indice_no_queda_ningun_pasaje_gigante():
    carpeta = ROOT / "index" / "chunks"
    if not carpeta.exists():
        pytest.skip("índice no construido en esta copia")
    grandes = []
    for f in carpeta.glob("*.jsonl"):
        for linea in f.read_text(encoding="utf-8").split("\n"):
            if not linea.strip():
                continue
            r = json.loads(linea)
            if not r.get("is_dose_table") and len(r["text"].split()) > GIGANTE:
                grandes.append((r["doc_id"], len(r["text"].split())))
    assert not grandes, f"{len(grandes)} pasajes por encima de {GIGANTE} palabras: {grandes[:5]}"
