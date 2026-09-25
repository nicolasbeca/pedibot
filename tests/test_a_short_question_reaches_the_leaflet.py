"""Una pregunta de dos palabras tiene que llegar a la hoja que la contesta (25-sep-2026).

Buscar «rotavirus» devolvía **cero**, teniendo la hoja del CDC sobre el rotavirus y el VIS de
MedlinePlus dentro del índice. No es un fallo del buscador: es una regla deliberada del
recuperador —«fuente o silencio»— que exige **tres** términos coincidentes cuando la pregunta no
cae en ningún tema de la taxonomía, para que «mi perro comió chocolate» no traiga la hoja de la
laringitis por la palabra «perro».

La consecuencia, que nadie había medido: **una enfermedad que no esté en la taxonomía es
inalcanzable si se pregunta con pocas palabras**. Eran 148 documentos de 632 —uno de cada
cuatro— y entre ellos el rotavirus, el norovirus, el VRS, la conmoción, la celulitis, la roséola,
el chalazión, la vulvovaginitis. Y también `bronchiolitis`, que en castellano sí estaba: faltaba
la palabra inglesa.

Aquí van los casos concretos. Si mañana alguien recorta la taxonomía, esto lo dice.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.ingest.classify import Taxonomy
from pedibot.settings import ROOT

TAX = Taxonomy(ROOT / "config" / "taxonomia.yaml")

#: (lo que escribe el padre, el tema al que tiene que llevar)
CASOS = [
    ("rotavirus", "digestivo"),
    ("norovirus", "digestivo"),
    ("celiaquía", "digestivo"),
    ("bronchiolitis", "respiratorio"),
    ("stridor", "respiratorio"),
    ("flu", "respiratorio"),
    ("RSV", "respiratorio"),
    ("concussion", "accidentes"),
    ("conmoción cerebral", "accidentes"),
    ("cellulitis", "piel"),
    ("roseola", "piel"),
    ("ringworm", "piel"),
    ("chalazion", "ojos"),
    ("stye", "ojos"),
    ("night terrors", "desarrollo"),
    ("escoliosis", "desarrollo"),
    ("vulvovaginitis", "urinario"),
    ("tongue-tie", "lactante"),
    ("plagiocefalia", "lactante"),
]


@pytest.mark.parametrize(("pregunta", "tema"), CASOS, ids=lambda x: x[:20])
def test_the_word_a_parent_types_has_a_topic(pregunta: str, tema: str) -> None:
    assert TAX.topic_for(pregunta) == tema, (
        f"«{pregunta}» no cae en ningún tema, así que el recuperador le exigirá tres términos"
        f" y una pregunta corta se quedará sin respuesta (esperado: {tema})"
    )


def test_a_common_word_still_has_no_topic() -> None:
    """La otra mitad de la regla: ampliar la taxonomía no puede convertir cualquier cosa en
    pediátrica, o «fuente o silencio» deja de filtrar nada."""
    for palabra in ("perro", "coche", "hipoteca", "dog", "car", "mortgage"):
        assert TAX.topic_for(palabra) is None, palabra


def test_the_index_can_actually_answer_them() -> None:
    """Y que la hoja exista: un tema nuevo sin documento detrás no sirve de nada."""
    import sqlite3

    bd = ROOT / "index" / "pedibot.db"
    if not pathlib.Path(bd).exists():
        pytest.skip("sin índice construido")
    con = sqlite3.connect(bd)
    for termino in ("rotavirus", "norovirus", "concussion", "stridor", "vulvovaginitis"):
        n = con.execute(
            "SELECT count(*) FROM chunks WHERE lower(data) LIKE ?", (f"%{termino}%",)
        ).fetchone()[0]
        assert n > 0, f"«{termino}» tiene tema pero ningún documento que lo trate"
