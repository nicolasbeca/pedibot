"""El antibiótico recetado: ni una cifra, pero sí ayuda (26-oct-2026).

Consulta real 1075 (España): «Mi hija le han recetado amoxicilina con 14kg de peso. Tiene autitis.
La amoxicilina que me han enviado es de 125mg/5ml.» La respuesta fue segura y casi vacía: «no
puedo calcularla aquí», cómo repartir las tomas, y de la otitis nada, porque «autitis» no llevaba
a ningún pasaje de oído.

No se da la dosis, y es decisión del operador (26-oct): la tabla autorizada de la AEPap pone la
amoxicilina a 25-50 mg/kg/día, y en la otitis la guía de Donostia, que también está en el índice,
receta 80-90. Un padre con una receta correcta que la comparase con la tabla general creería que le
han dado de más, y daría de menos. Así que el redactor recibe una nota: ninguna cifra del
antibiótico, que siga la receta, que el farmacéutico le confirma los ml de su frasco, y que conteste
lo demás (la infección que nombra, el dolor y cuándo volver al médico).
"""

from __future__ import annotations

import pytest

from pedibot.bot.prescribed import (
    NOTA_ANTIBIOTICO,
    da_cifra_del_antibiotico,
    nota_antibiotico,
    pregunta_por_antibiotico,
)
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import get_settings

LA_REAL = (
    "Mi hija le han recetado amoxicilina con 14kg de peso. Tiene autitis. La amoxicilina que me "
    "han enviado es de 125mg/5ml."
)

DE_ANTIBIOTICO = [
    LA_REAL,
    "My son was prescribed amoxicillin for an ear infection, he weighs 18 kg",
    "How many ml of Augmentin for a 12 kg toddler?",
    "Le médecin a prescrit de l'amoxicilline à ma fille",
    "Meu filho está tomando antibiótico para otite",
    "Mein Kind bekommt ein Antibiotikum gegen Mittelohrentzündung",
    "моему сыну назначили амоксициллин",
    "can I give the antibiotic with milk?",
]

NO_DE_ANTIBIOTICO = [
    "How much Calpol for 14 kg?",
    "¿Cuánto ibuprofeno le doy a mi hijo de 14 kg?",
    "Mi hijo tiene otitis y le duele mucho",
]


@pytest.mark.parametrize("texto", DE_ANTIBIOTICO)
def test_the_antibiotic_is_seen(texto: str) -> None:
    assert pregunta_por_antibiotico(texto)
    assert nota_antibiotico(texto) == NOTA_ANTIBIOTICO


@pytest.mark.parametrize("texto", NO_DE_ANTIBIOTICO)
def test_paracetamol_and_plain_otitis_are_not(texto: str) -> None:
    assert not pregunta_por_antibiotico(texto)
    assert nota_antibiotico(texto) == ""


def test_the_note_says_what_to_do_and_what_not() -> None:
    nota = NOTA_ANTIBIOTICO
    assert "NO dose" in nota and "not even from a DOSE TABLE" in nota
    assert "prescription" in nota and "pharmacist" in nota
    assert "ear infection" in nota  # por qué no se compara con una tabla
    assert "rest of the question" in nota


DA_CIFRA = [
    "Según la AEPap, la amoxicilina se da a 25-50 mg/kg al día [3].",
    "That is 80 mg per kg a day, split into three doses.",
    "Con su frasco serían 5,6 ml cada 8 horas [3].",
    "Give 7 ml three times a day.",
]

NO_DA_CIFRA = [
    # la concentración del frasco no es una dosis: la 1075 la decía y estaba bien
    "La amoxicilina para niños se presenta en dos concentraciones, de 125 mg en 5 ml o de 250 mg en 5 ml, según el NHS [1].",
    "Su frasco es de 125mg/5ml.",
    "The bottle says 250 mg / 5 ml.",
    "Use la jeringa oral que viene con el medicamento [1].",
]


@pytest.mark.parametrize("texto", DA_CIFRA)
def test_a_dose_of_the_antibiotic_is_caught(texto: str) -> None:
    assert da_cifra_del_antibiotico(texto)


@pytest.mark.parametrize("texto", NO_DA_CIFRA)
def test_the_bottle_strength_is_not_a_dose(texto: str) -> None:
    assert not da_cifra_del_antibiotico(texto)


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


def test_autitis_reaches_the_ear(buscador: Retriever) -> None:
    hits, _ = buscador.search(LA_REAL, "es")
    ids = [h.chunk.chunk_id for h in hits]
    assert any("otitis" in i or "ear_infection" in i for i in ids), ids
