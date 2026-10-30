"""El pasaje del aviso, en la lengua del lector cuando lo hay (30-oct-2026).

Prueba en vivo antes de la decimocuarta tanda: «my 5 week old has a fever of 100.6» desde EE. UU.
daba bien el aviso, pero las tres fuentes eran de la SEUP, en castellano. La regla
`infant_fever_under_3_months` inyecta delante su pasaje comprobado (`source_chunk`), que es el de
la SEUP, y la búsqueda en inglés sólo traía un pasaje del NHS detrás: el redactor citó lo primero.
Un padre que no lee castellano no puede comprobar nada, que es lo que este producto ofrece.

Ahora una regla puede nombrar también su pasaje en inglés (`source_chunk_en`), comprobado igual que
el otro, y para el lector en inglés se inyecta ése. No hay ninguna ficha de EE. UU. en el índice
que diga el umbral (la de MedlinePlus sobre la fiebre no habla de bebés), así que es el NHS.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.index.store import Index
from pedibot.settings import get_settings

S = get_settings()
REGLAS = {r.id: r for r in Triage(S.config_dir / "red_flags.yaml").rules}
NHS_TEMPERATURA = (
    "nhs_en_how_to_take_your_babys_temperature#what_should_i_do_if_my_baby_has_a_high_t#1"
)


def test_la_fiebre_del_bebe_tiene_pasaje_en_ingles() -> None:
    assert REGLAS["infant_fever_under_3_months"].source_chunks.get("en") == NHS_TEMPERATURA


@pytest.mark.skipif(not S.index_db_path.exists(), reason="sin índice")
@pytest.mark.parametrize(
    "regla", [r for r in REGLAS.values() if r.source_chunks], ids=lambda r: r.id
)
def test_cada_pasaje_por_lengua_existe_y_es_de_esa_lengua(regla) -> None:  # noqa: ANN001
    for lang, cid in regla.source_chunks.items():
        c = Index(S.index_db_path).get(cid)
        assert c is not None, f"{regla.id}: {cid} no está en el índice"
        assert c.lang == lang, f"{regla.id}: {cid} está en {c.lang}, no en {lang}"


@pytest.mark.skipif(not S.index_db_path.exists(), reason="sin índice")
def test_el_pasaje_ingles_dice_lo_que_dice_el_aviso() -> None:
    t = Index(S.index_db_path).get(NHS_TEMPERATURA).text
    assert "38C or higher if they're under 3 months old" in t


@pytest.fixture(scope="module")
def motor():
    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.drugs import DrugCatalog
    from pedibot.bot.llm import FakeProvider
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.ingest.classify import Taxonomy

    llm = FakeProvider(lambda sys_, user: "Fake draft based on the sources [1].")
    return Engine(
        Retriever(
            Index(S.index_db_path),
            Synonyms(S.config_dir / "synonyms.yaml", S.config_dir / "drugs.yaml"),
            top_k=S.retrieval_top_k,
            taxonomy=Taxonomy(S.config_dir / "taxonomia.yaml"),
        ),
        Triage(S.config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(S.config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(S.config_dir / "drugs.yaml"),
    )


@pytest.mark.skipif(not S.index_db_path.exists(), reason="sin índice")
@pytest.mark.parametrize(
    ("pregunta", "pais"),
    [("my 5 week old has a fever of 100.6", "US"), ("My 6 week old has a temperature of 38.2", "GB")],
)
def test_al_lector_en_ingles_le_llega_el_nhs_delante(motor, pregunta: str, pais: str) -> None:
    a = motor.ask(pregunta, country=pais, lang="en")
    assert a.level == "urgent"
    assert a.chunk_ids[0] == NHS_TEMPERATURA
    assert REGLAS["infant_fever_under_3_months"].source_chunk not in a.chunk_ids


@pytest.mark.skipif(not S.index_db_path.exists(), reason="sin índice")
def test_en_castellano_sigue_la_seup(motor) -> None:
    a = motor.ask("Mi bebé de 5 semanas tiene 38,2 de fiebre", country="ES", lang="es")
    assert a.level == "urgent"
    assert a.chunk_ids[0] == REGLAS["infant_fever_under_3_months"].source_chunk
