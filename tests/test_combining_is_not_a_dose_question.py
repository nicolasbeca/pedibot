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
