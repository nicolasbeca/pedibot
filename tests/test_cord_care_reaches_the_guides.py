"""«Should I put oil or ghee on the umbilical cord?» llega a cómo se cuida el cordón (12-nov-2026).

Visto el 9-nov al probar ganchos para los correos: la primera vez atribuía a la AEP lo que la AEP
no dice («the AEP advises against…»), y hoy contesta «no tengo información fiable». Las guías sí
dicen cómo se cuida: el NHS (lavar con agua tibia sólo si se ensucia y secar con toques), la Junta
de Andalucía (agua y jabón, seco y limpio, sin cubrirlo) y el BIÖG (agua hervida tibia, secar sin
frotar). La búsqueda en inglés se quedaba en el paritorio de la AEP y el compendio neonatal.
"""

from __future__ import annotations

import re

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

CUIDADO = re.compile(
    r"nhs_en_washing_and_bathing_your_baby#topping_and_tailing"
    r"|andalucia_cuidame_comienzo_vida#el_ombligo"
    r"|andalucia_cuidame_guia#2_2_sus_cuidados"
    r"|bioeg_de_babys_pflege_nabelpflege"
    # la guía de la AEP, apartado «d) Cuidado del cordón»: agua y jabón, y antiséptico
    r"|aep_cuidados_recien_nacido#cuidados_despues_del_parto#1"
)

PREGUNTAS = [
    ("Should I put oil or ghee on my newborn baby umbilical cord?", "en"),
    ("How do I clean my baby's cord stump?", "en"),
    ("¿Le pongo aceite en el ombligo a mi recién nacido?", "es"),
]


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    s = get_settings()
    return Retriever(
        Index(s.index_db_path),
        Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
        llm=None,
        top_k=s.retrieval_top_k,
        taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
    )


@pytest.mark.parametrize("pregunta,lang", PREGUNTAS)
def test_cord_care_comes_up(buscador: Retriever, pregunta: str, lang: str) -> None:
    hits, _ = buscador.search(pregunta, lang)
    ids = [h.chunk.chunk_id for h in hits]
    assert sum(bool(CUIDADO.search(i)) for i in ids) >= 2, ids
