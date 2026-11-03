"""Fiebre de dos días y la respuesta no decía cuándo ir al médico (consulta 1125, 1-nov-2026).

«My 2 year old has had a fever of 39 degrees for two days. What should I do?» (smartbench, por el
MCP). Seis veces la misma pregunta; cinco respuestas daban la lista del NHS —llama al 111 si dura 5
días o más, si no come, si está deshidratado; al 999 si tiene el cuello rígido, manchas que no
desaparecen…—. La sexta tenía ese pasaje delante ([7], «Don't», que lleva dentro «Urgent advice:
Call 111 if…»), citaba el mismo documento del NHS por otra sección y acababa en «Watch their general
condition and colour». La regla c) del prompt ya pide la lista entera: es el modelo, que una de cada
tantas se la salta. La 807 (hindi, 6 meses, «¿lo baño para bajarle la fiebre?») igual.

El candado: si la respuesta usa un documento y otro pasaje de ESE documento dice cuándo pedir ayuda,
y la respuesta no lo cita ni manda al médico en ninguna frase (las de la dosis no cuentan: «at the
dose your paediatrician recommends» no es un cuándo ir), un reintento con la nota. Del mismo
documento, para no traer la lista de otra situación (la regla c, y la v12). Medido el 3-nov sobre
las 385 respuestas sin aviso guardadas que se pueden releer (otras 248 citan pasajes renombrados
al reindexar): dispara en 2, la 1125 y la 807, las dos de verdad sin el cuándo ir. Sin la segunda
condición disparaba en 9, y 7 ya decían «avisa a su médico» o traían la lista de otra situación.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.answer import REVISA as _REVISA
from pedibot.bot.answer import TRADUCE as _TRADUCE
from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.interpret import SYSTEM as _LECTURA
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.bot.when_to_get_help import falta_cuando_pedir_ayuda
from pedibot.index.store import Hit, Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk


def _chunk(cid: str, org: str, section: str, text: str, red: bool = False) -> Chunk:
    return Chunk(
        chunk_id=cid,
        doc_id=cid.split("#")[0],
        org=org,
        doc_title="High temperature (fever) in children",
        year=2025,
        lang="en" if org == "NHS" else "es",
        section=section,
        pages=[1],
        text=text,
        topic="fiebre",
        doc_type="hoja_padres",
        evidence="organismo_publico",
        usage="publico",
        is_red_flag=red,
        source_hash="h",
        n_words=len(text.split()),
    )


LEAD = _chunk(
    "nhs_en_fever_in_children#high_temperature_fever_in_children#1",
    "NHS",
    "High temperature (fever) in children",
    "A high temperature (fever) is very common in young children. The temperature usually returns"
    " to normal within 1 to 4 days.",
)
DONT = _chunk(
    "nhs_en_fever_in_children#don_t#1",
    "NHS",
    "Don’t",
    "do not undress your child or sponge them down to cool them; do not give aspirin to children"
    # «fever» en vez de «high temperature» del original, para que la búsqueda léxica de la prueba
    # lo traiga: en vivo llega por los vectores
    " under 16 years of age; Urgent advice: Call 111 if your child: has a fever that's"
    " lasted for 5 days or more; does not want to eat, or is not their usual self and you're"
    " worried; is dehydrated; Immediate action required: Call 999 if your child: has a stiff neck;",
)
SEUP_QUE_ES = _chunk(
    "seup_fiebre#que_es_la_fiebre#1", "SEUP", "¿QUÉ ES LA FIEBRE?", "Es un mecanismo de defensa."
)
SEUP_CASA = _chunk(
    "seup_fiebre#que_podemos_hacer_en_casa_cuando_tiene_f#1",
    "SEUP",
    "¿QUÉ PODEMOS HACER EN CASA CUANDO TIENE FIEBRE?",
    "Los más utilizados son el paracetamol y el ibuprofeno que se pueden dar a la dosis"
    " recomendada por su pediatra cada 6-8 horas.",
)

HITS = [Hit(c, 10.0, 1) for c in (LEAD, SEUP_QUE_ES, SEUP_CASA, DONT)]

#: la 1125, recortada, con los números de HITS
LA_1125 = (
    "A fever is very common in young children, and the temperature usually returns to normal within"
    " 1 to 4 days, according to the NHS [1]. It is a defence mechanism, according to the SEUP [2].\n\n"
    "Make sure they drink plenty. Paracetamol or ibuprofen can lower the temperature, at the dose"
    " your paediatrician recommends, every 6 to 8 hours [3]. Do not bathe them in cold water.\n\n"
    "Watch their general condition and colour."
)


def test_the_answer_without_when_to_get_help_is_sent_back():
    nota = falta_cuando_pedir_ayuda(LA_1125, HITS)
    assert nota is not None
    assert "[4]" in nota  # el pasaje que tiene la lista, por su número


def test_citing_the_list_is_enough():
    texto = LA_1125 + " Call for advice if the fever has lasted 5 days or more [4]."
    assert falta_cuando_pedir_ayuda(texto, HITS) is None


@pytest.mark.parametrize(
    "frase",
    [
        "If you are worried, see a GP.",
        "Get medical advice if the paracetamol is not helping.",
        "Si está decaído, consulta con su pediatra.",
        "Wenn es Ihrem Kind schlechter geht, gehen Sie zur Kinderärztin.",
        "Si l'enfant ne boit plus, consultez un médecin.",
        "अगर बच्चा सुस्त लगे तो डॉक्टर को दिखाएँ।",
        "إذا ساءت حالته، راجع الطبيب.",
        "Если ребёнку хуже, обратитесь к врачу.",
        "Akiendelea vibaya, mpeleke kwa daktari.",
        "Se piorar, procure o pediatra.",
    ],
)
def test_any_sentence_sending_them_to_a_doctor_is_enough(frase: str):
    """Ya dice cuándo ir, aunque no sea con la lista: no se rehace (de las 9 que disparaban sin
    esto, 7 eran así: «avisa a su médico», «consultar con su pediatra», «ask the doctor»)."""
    assert falta_cuando_pedir_ayuda(LA_1125 + "\n\n" + frase, HITS) is None


def test_the_doctor_of_the_dose_sentence_does_not_count():
    """«at the dose your paediatrician recommends» está en la 1125 y no dice cuándo ir."""
    texto = "Paracetamol can help, at the dose your paediatrician recommends [1]."
    assert falta_cuando_pedir_ayuda(texto, HITS) is not None


def test_a_list_from_a_document_the_answer_does_not_use_is_left_alone():
    """Del mismo documento o nada: la lista de urgencias de los trastornos alimentarios no es para
    un niño de 3 años delgado, ni la del tobillo roto para una pregunta de ejercicios."""
    texto = "It is a defence mechanism, according to the SEUP [2]. Offer fluids [3]."
    assert falta_cuando_pedir_ayuda(texto, HITS) is None


def test_a_list_marked_only_by_its_heading_counts():
    """`is_red_flag` no marca todas: «When and where to get medical help» del pañal no la lleva."""
    lista = _chunk(
        "nhs_en_nappy_rash#when_and_where_to_get_medical_help#1",
        "NHS",
        "When and where to get medical help",
        "Non-urgent advice: See a health visitor or GP if: the nappy rash does not go away;",
    )
    uso = _chunk("nhs_en_nappy_rash#nappy_rash#1", "NHS", "Nappy rash", "Nappy rash is common.")
    hits = [Hit(uso, 10.0, 1), Hit(lista, 9.0, 1)]
    assert falta_cuando_pedir_ayuda("Nappy rash is common, says the NHS [1].", hits) is not None


def test_a_list_marked_as_warning_signs_counts():
    lista = _chunk("nhs_en_x#y#1", "NHS", "Symptoms", "a stiff neck; a rash that does not fade;", red=True)
    uso = _chunk("nhs_en_x#z#1", "NHS", "X", "X is common.")
    hits = [Hit(uso, 10.0, 1), Hit(lista, 9.0, 1)]
    assert falta_cuando_pedir_ayuda("X is common, says the NHS [1].", hits) is not None


# --- en el motor ---------------------------------------------------------------------------


def _redaccion(llm):  # noqa: ANN001, ANN202
    return [c for c in llm.calls if c[0] not in (_LECTURA, _TRADUCE, _REVISA)]


@pytest.fixture
def motor(tmp_path: Path, config_dir: Path):
    db = tmp_path / "i.db"
    build_index([LEAD, DONT, SEUP_QUE_ES, SEUP_CASA], db)

    def make(responder):  # noqa: ANN001, ANN202
        llm = FakeProvider(responder)
        return Engine(
            Retriever(
                Index(db),
                Synonyms(config_dir / "synonyms.yaml"),
                taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
            ),
            Triage(config_dir / "red_flags.yaml"),
            llm,
            EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        ), llm

    return make


def _numero(user: str, cid_texto: str) -> str:
    """El número con que el redactor ve un pasaje en SOURCES."""
    for bloque in user.split("\n\n["):
        if cid_texto in bloque:
            return bloque.split("]")[0].lstrip("[")
    raise AssertionError(cid_texto)


def test_the_engine_rewrites_it_once_with_the_note(motor):
    def responde(system: str, user: str) -> str:
        if system in (_LECTURA, _REVISA):
            return "no es json"
        lead = _numero(user, "very common in young children")
        if "missing_when_to_get_help" not in system:
            return (
                f"A fever is very common in young children, according to the NHS [{lead}]."
                " Watch their general condition and colour."
            )
        lista = _numero(user, "Urgent advice")
        return (
            f"A fever is very common in young children, according to the NHS [{lead}]. Call for"
            f" advice if it has lasted 5 days or more or they are not their usual self [{lista}]."
        )

    eng, llm = motor(responde)
    a = eng.ask("My 2 year old has had a fever of 39 degrees for two days. What should I do?",
                country="GB")
    assert a.level == "routine"
    assert a.verification == "regenerated"
    assert "5 days or more" in a.text
    assert len(_redaccion(llm)) == 2
