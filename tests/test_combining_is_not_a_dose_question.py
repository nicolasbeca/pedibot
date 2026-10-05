"""«¿Puedo darle los dos?» no es una pregunta de dosis (5-oct-2026).

Batería con el reparto de las consultas reales: «how much Motrin for 24 lbs» → «can I give him
both Tylenol and Motrin at the same time» devolvía otra vez la tabla, de paracetamol, sin
contestar si se pueden juntar. Igual «cuánto Apiretal para 12 kilos» → «y si no le baja la fiebre
le puedo dar Dalsy». El enrutador cogía el primer medicamento que veía y el peso del turno
anterior. Juntar o alternar lo contestan las guías (el NHS dice cuándo se puede cambiar de uno a
otro); la calculadora sólo sabe cuánto.

Y las marcas que un padre escribe y el catálogo no conocía: Dolex (Colombia), Termofren
(Argentina) y Biogesic (Filipinas) son paracetamol.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.answer import dose_intent, pregunta_combinar
from pedibot.bot.drugs import DrugCatalog

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def catalogo() -> DrugCatalog:
    return DrugCatalog(RAIZ / "config" / "drugs.yaml")


@pytest.mark.parametrize(
    "frase",
    [
        "can I give him both Tylenol and Motrin at the same time",
        "can I give Nurofen as well",
        "is it okay to alternate Tylenol and Motrin for fever",
        "y si no le baja la fiebre le puedo dar dalsy",
        "puedo juntar tylenol con motrin si no se le quita la fiebre",
        "kann ich paracetamol und nurofen im wechsel geben",
        "est ce que je peux alterner avec de l advil",
        "posso dar brufen ao mesmo tempo",
        "можно ли чередовать цефекон и нурофен",
        "هل اقدر اعطيه بروفين مع الادول اذا ما نزلت الحرارة",
    ],
)
def test_combinar(catalogo: DrugCatalog, frase: str) -> None:
    assert pregunta_combinar(frase, catalogo)


@pytest.mark.parametrize(
    "frase",
    [
        "how many ml of Tylenol for a 10 kg baby",
        "cuanto apiretal le toca a mi hijo de 12 kilos",
        "wie viel nurofen saft bei 12 kg",
        "how much Motrin for 11 kg",
    ],
)
def test_una_dosis_sigue_siendo_dosis(catalogo: DrugCatalog, frase: str) -> None:
    assert not pregunta_combinar(frase, catalogo)
    assert dose_intent(frase, catalogo)


@pytest.mark.parametrize("marca", ["dolex", "termofren", "biogesic"])
def test_marcas_de_paracetamol(catalogo: DrugCatalog, marca: str) -> None:
    assert dose_intent(f"cuanto {marca} le doy a mi bebe de 8 kilos", catalogo) == (
        "paracetamol",
        8.0,
    )


def test_el_ruso_declina_la_marca(catalogo: DrugCatalog) -> None:
    assert dose_intent("какая дозировка нурофена для ребенка 12 кг", catalogo) == (
        "ibuprofen",
        12.0,
    )


def test_una_marca_con_guiones(catalogo: DrugCatalog) -> None:
    """«qual a dose de ben-u-ron para criança de 12 kg» no daba dosis: «ben-u-ron» se partía."""
    assert dose_intent("qual a dose de ben-u-ron para criança de 12 kg", catalogo) == (
        "paracetamol",
        12.0,
    )


def test_el_medicamento_nuevo_con_el_peso_de_antes(tmp_path: pathlib.Path, config_dir) -> None:
    """«cuánto paracetamol para 10 kilos» → «y si le doy ibuprofeno, ¿cuánto sería?» repetía el
    paracetamol: el enrutador cogía el primer medicamento de la conversación."""
    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.llm import FakeProvider
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.bot.triage import Triage
    from pedibot.index.store import Index, build_index
    from pedibot.ingest.classify import Taxonomy
    from pedibot.ingest.schema import Chunk

    db = tmp_path / "i.db"
    build_index(
        [
            Chunk(
                chunk_id="seup_fiebre#s#1", doc_id="seup_fiebre", org="SEUP", doc_title="Fiebre",
                year=None, lang="es", section="S", pages=[1], text="La fiebre no es peligrosa.",
                topic="fiebre", doc_type="hoja_padres", evidence="sociedad_cientifica",
                usage="publico", source_hash="h", n_words=5,
            )
        ],
        db,
    )
    motor = Engine(
        Retriever(Index(db), Synonyms(config_dir / "synonyms.yaml"),
                  taxonomy=Taxonomy(config_dir / "taxonomia.yaml")),
        Triage(config_dir / "red_flags.yaml"),
        FakeProvider("Según la SEUP, x [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        drugs=catalogo_(),
    )
    a = motor.ask("cuanta dosis de paracetamol para 10 kilos", country="CL", lang="es")
    b = motor.ask(
        "y si le doy ibuprofeno cuanto seria",
        country="CL",
        lang="es",
        history=[
            {"role": "user", "text": "cuanta dosis de paracetamol para 10 kilos"},
            {"role": "assistant", "text": a.text},
        ],
    )
    assert b.verification == "dose_calculator", b.text
    assert b.text.startswith("Ibuprofeno"), b.text[:80]


def catalogo_() -> DrugCatalog:
    return DrugCatalog(RAIZ / "config" / "drugs.yaml")
