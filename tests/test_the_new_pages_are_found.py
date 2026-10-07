"""Las páginas que el juez echó en falta se encuentran (7-oct-2026).

El juez contra las guías marcó huecos: acné, cuánta agua bebe un bebé, un tobillo torcido, el
tétanos tras un corte. Se bajaron las páginas del NHS, y aun así la búsqueda volvía vacía: sin un
tema del catálogo la pregunta tiene que casar tres palabras, y «acne», «ankle» o «drinks» no eran
palabra de ningún tema. Con ellas, de 3.829 preguntas de las baterías cambian siete, todas a mejor.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.ingest.classify import Taxonomy

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("pregunta", "tema"),
    [
        ("my 15 year old has acne that is getting worse", "piel"),
        ("mi hijo tiene mucho acne con 10 años", "piel"),
        ("how much water can a 9 month old drink", "alimentacion"),
        ("my 12 year old twisted his ankle playing soccer", "accidentes"),
        ("does he need a tetanus shot after a cut", "accidentes"),
    ],
)
def test_la_pregunta_cae_en_su_tema(pregunta: str, tema: str) -> None:
    tax = Taxonomy(RAIZ / "config" / "taxonomia.yaml")
    assert tax.topic_for(pregunta) == tema
