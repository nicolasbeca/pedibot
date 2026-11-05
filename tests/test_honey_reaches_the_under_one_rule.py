"""La miel para la tos de un bebé llega a «nada de miel antes del año» (5-nov-2026).

Probando en vivo un gancho para un correo: «Posso dar mel para a tosse do meu bebê de 8 meses?»
contestaba «Não, não dê mel» sin ninguna fuente que lo dijera y luego hablaba de la tos ferina
del Ministério da Saúde. El corpus tiene la regla —CDC, MedlinePlus y NHS: nada de miel antes de
los 12 meses, por el botulismo— pero «mel» no tendía ningún puente al inglés: no había ni una
entrada de miel en config/synonyms.yaml. En inglés llegaba porque «honey» está en los pasajes.

«mel» va con `$` (palabra entera): sin él, «melhor» y «melhora» también serían miel.
"""

from __future__ import annotations

import re

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

#: los pasajes que dicen que no se da miel antes del año
SIN_MIEL = re.compile(
    r"cdc_en_treatment#children"
    r"|mlp_en_infantandnewbornnutrition#lead"
    r"|nhs_en_chest_infection#don_t"
    r"|nhs_en_cough#cough"
    r"|nhs_en_foods_to_avoid_giving_babies_and_young_children#honey"
)

PREGUNTAS = [
    ("Posso dar mel para a tosse do meu bebê de 8 meses?", "pt"),
    ("¿Puedo darle miel a mi bebé de 8 meses para la tos?", "es"),
    ("Est-ce que je peux donner du miel à mon bébé de 8 mois pour la toux ?", "fr"),
    ("Darf ich meinem 8 Monate alten Baby Honig gegen Husten geben?", "de"),
    ("Можно ли дать мёд 8-месячному ребёнку от кашля?", "ru"),
    ("هل يمكنني إعطاء العسل لطفلي عمره 8 أشهر للسعال؟", "ar"),
    ("क्या मैं अपने 8 महीने के बच्चे को खांसी के लिए शहद दे सकती हूँ?", "hi"),
    ("kya 8 mahine ke bachche ko khansi ke liye shahad de sakte hain", "hi"),
    ("Naweza kumpa mtoto wangu wa miezi 8 asali kwa kikohozi?", "sw"),
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


@pytest.mark.parametrize(("pregunta", "lang"), PREGUNTAS)
def test_the_no_honey_before_one_rule_comes_up(
    buscador: Retriever, pregunta: str, lang: str
) -> None:
    hits, _ = buscador.search(pregunta, lang)
    ids = [h.chunk.chunk_id for h in hits]
    assert any(SIN_MIEL.search(i) for i in ids), ids


def test_better_in_portuguese_is_not_honey() -> None:
    s = get_settings()
    syn = Synonyms(s.config_dir / "synonyms.yaml")
    assert "honey" not in " ".join(syn.expand("o meu bebê está melhor da tosse", "pt")).lower()
