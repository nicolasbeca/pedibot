"""El peso en las unidades del padre (5-oct-2026).

De las consultas reales, siete de cada diez son en inglés y la mayoría de EE. UU., donde un niño
pesa «22 pounds». El motor sólo conocía los kilos: «how many ml of Tylenol for a 22 pound baby»
(batería escrita con el reparto de las consultas reales) no llegaba a la calculadora de dosis y
el modelo contestaba sin cifra; «(weight: 18 lbs)» del propio campo del chat no se leía; «mi hija
pesa 15 libras» tampoco. Las libras sólo existían en el código para NO confundirlas con fiebre.

Es aritmética, así que se hace a la entrada y sin modelo: cada peso en libras lleva al lado sus
kilos, «22 pound (10 kg)». Así lo leen de una vez la dosis, las curvas y el redactor, y el padre
ve la conversión.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.answer import dose_intent
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.weight_units import con_kilos, nota_de_peso

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def catalogo() -> DrugCatalog:
    return DrugCatalog(RAIZ / "config" / "drugs.yaml")


@pytest.mark.parametrize(
    ("texto", "kg"),
    [
        ("how many ml of Tylenol for a 22 pound baby", 10.0),
        ("how much Motrin for 24 lbs", 10.9),
        ("my son is 4 and weighs 25 pounds, is that too little", 11.3),
        ("my baby fell off the bed (age: 8 months) (weight: 18 lbs)", 8.2),
        ("mi niño tiene fiebre de 102 F y pesa 30 libras, cuanto Tylenol", 13.6),
        ("cuanto tylenol para un bebe de 20 libras", 9.1),
        ("my daughter weighs 50 pounds and is 6 years old", 22.7),
        ("my child is 6 and weighs 44lb", 20.0),
        ("she is 1 year old and 21.5 lbs", 9.8),
    ],
)
def test_cada_libra_lleva_sus_kilos(texto: str, kg: float) -> None:
    salida = con_kilos(texto)
    assert f"({kg:g} kg)" in salida, salida
    assert texto.split()[0] in salida  # lo que escribió el padre se queda


@pytest.mark.parametrize(
    "texto",
    [
        "my 3 year old has a fever of 101",
        "my son weighs 12 kg",
        "how much Motrin for 24 lbs (10.9 kg)",  # ya convertido: no se duplica
        "a pound cake gave him a rash",
        "five pounds of apples",
    ],
)
def test_lo_que_no_es_un_peso_en_libras_no_se_toca(texto: str) -> None:
    assert con_kilos(texto) == texto


def test_la_dosis_llega_con_libras(catalogo: DrugCatalog) -> None:
    assert dose_intent(con_kilos("how many ml of Tylenol for a 22 pound baby"), catalogo) == (
        "paracetamol",
        10.0,
    )
    assert dose_intent(con_kilos("cuanto tylenol para un bebe de 20 libras"), catalogo) == (
        "paracetamol",
        9.1,
    )


@pytest.fixture
def motor(tmp_path: pathlib.Path, config_dir):
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
                chunk_id="nhs_en_fever#s#1",
                doc_id="nhs_en_fever",
                org="NHS",
                doc_title="Fever",
                year=None,
                lang="en",
                section="S",
                pages=[1],
                text="A fever is a high temperature.",
                topic="fiebre",
                doc_type="hoja_padres",
                evidence="organismo_publico",
                usage="publico",
                source_hash="h",
                n_words=6,
            )
        ],
        db,
    )
    return Engine(
        Retriever(
            Index(db),
            Synonyms(config_dir / "synonyms.yaml"),
            taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
        ),
        Triage(config_dir / "red_flags.yaml"),
        FakeProvider("The NHS says x [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(config_dir / "drugs.yaml"),
    )


def test_el_chat_da_la_dosis_con_libras(motor) -> None:
    """La pregunta de la batería, de punta a punta: sale la tabla, con 10 kg, y la conversión."""
    a = motor.ask("how many ml of Tylenol for a 22 pound baby", country="US", lang="en")
    assert a.verification == "dose_calculator", a.verification
    assert a.text.startswith("22 lb = 10 kg"), a.text[:200]
    assert "10 kg" in a.text


def test_la_respuesta_dice_la_conversion() -> None:
    assert nota_de_peso("how much Motrin for 24 lbs", "en") == "24 lb = 10.9 kg"
    assert nota_de_peso("cuanto tylenol para un bebe de 20 libras", "es") == "20 libras = 9,1 kg"
    assert nota_de_peso("my son weighs 12 kg", "en") is None


def test_sin_edad_pregunta_la_edad_y_luego_da_la_dosis(motor) -> None:
    """«how much Motrin for 24 lbs»: el ibuprofeno necesita saber que tiene más de 3 meses. Se
    pregunta la edad (no se prohíbe), y con la respuesta sale la dosis con el peso de antes."""
    a = motor.ask("how much Motrin for 24 lbs", country="US", lang="en")
    assert "How old is your child?" in a.text, a.text
    assert "Do not give" not in a.text
    b = motor.ask(
        "he is 2 years old",
        country="US",
        lang="en",
        history=[
            {"role": "user", "text": "how much Motrin for 24 lbs"},
            {"role": "assistant", "text": a.text},
        ],
    )
    assert b.verification == "dose_calculator", b.verification
    assert "• Dose:" in b.text, b.text


@pytest.mark.parametrize(
    ("pregunta", "lang"),
    [
        ("how much Calpol for a 3 year old", "en"),
        ("cuanto tempra le doy a mi hijo de 3 años", "es"),
        ("wie viel Paracetamol darf ich meinem Kind geben", "de"),
    ],
)
def test_sin_peso_pregunta_el_peso_y_luego_da_la_dosis(motor, pregunta: str, lang: str) -> None:
    """«How much Calpol for a 3 year old» recibía «mira el prospecto». La dosis va por peso: se
    pregunta, y con la respuesta sale la tabla."""
    from pedibot.bot.strings import tool_strings

    a = motor.ask(pregunta, country="GB", lang=lang)
    assert a.verification == "dose_ask_weight", (a.verification, a.text)
    cabeza = tool_strings(lang)["dose_ask_weight"].split("{name}")[0]
    assert a.text.startswith(cabeza), a.text
    b = motor.ask(
        "14 kg",
        country="GB",
        lang=lang,
        history=[{"role": "user", "text": pregunta}, {"role": "assistant", "text": a.text}],
    )
    assert b.verification == "dose_calculator", (b.verification, b.text)
