"""La fiebre es de la madre, no del bebé (30-sep-2026).

«I feel unwell with a fever. Should I carry on breastfeeding my baby?» se contestaba bien —sí,
sigue dando el pecho, lávate las manos; NHS— pero empezaba por «si tu bebé tiene menos de 3
meses, la fiebre necesita un médico hoy» y acababa con «¿qué edad tiene?». El motor ve «fiebre»
sin edad y aplica la regla del lactante febril, que aquí no viene a cuento: el bebé no tiene
fiebre.

No es una pregunta «fuera de tema»: dar el pecho estando enferma es crianza y se contesta. Lo
único que cambia es que la fiebre no se atribuye al niño.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import fiebre_del_adulto

DEL_ADULTO = [
    "I feel unwell with a fever. Should I carry on breastfeeding my baby?",
    "I have a fever myself, can I still breastfeed?",
    "Tengo fiebre yo, no mi hijo. ¿Puedo seguir dándole el pecho?",
    "Estoy con fiebre y doy el pecho, ¿qué puedo tomar?",
    "J'ai de la fièvre, est-ce que je peux continuer à allaiter ?",
    "Ich habe Fieber und stille, was darf ich nehmen?",
    "Estou com febre, posso amamentar?",
    "У меня температура, можно ли кормить грудью?",
    "عندي حمى، هل يمكنني الاستمرار في الرضاعة؟",
    "मुझे बुखार है, क्या मैं स्तनपान करा सकती हूँ?",
]

DEL_NINO = [
    "My baby has a fever",
    "Mi hijo tiene fiebre de 39",
    "I think she has a fever, I have a thermometer",
    "Tengo un bebé con fiebre",
    "Tengo miedo de que tenga fiebre",
    "Mon bébé a de la fièvre",
]


@pytest.mark.parametrize("texto", DEL_ADULTO)
def test_se_reconoce_la_fiebre_del_adulto(texto: str):
    assert fiebre_del_adulto(texto)


@pytest.mark.parametrize("texto", DEL_NINO)
def test_la_del_nino_sigue_siendo_del_nino(texto: str):
    assert not fiebre_del_adulto(texto)


def test_el_motor_no_pide_la_regla_del_lactante(tmp_path, config_dir):
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
                chunk_id="nhs_x#s#1",
                doc_id="nhs_x",
                org="NHS",
                doc_title="Breastfeeding when unwell",
                year=None,
                lang="en",
                section="S",
                pages=[1],
                text="If you have a fever or feel unwell you can carry on breastfeeding your "
                "baby. Wash your hands before feeding.",
                topic="alimentacion",
                doc_type="hoja_padres",
                evidence="organismo_publico",
                usage="publico",
                source_hash="h",
                n_words=20,
            )
        ],
        db,
    )
    vistos: list[str] = []

    def llm(sys_: str, user: str) -> str:
        vistos.append(sys_ + "\n" + user)
        return "You can carry on breastfeeding, according to the NHS [1]."

    eng = Engine(
        Retriever(
            Index(db),
            Synonyms(config_dir / "synonyms.yaml"),
            taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
        ),
        Triage(config_dir / "red_flags.yaml"),
        FakeProvider(llm),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
    )
    a = eng.ask("I have a fever myself. Should I carry on breastfeeding my baby?")
    assert vistos, "el modelo no llegó a redactar"
    regla = "Open with ONE sentence: if the child is under 3 months"
    assert not any(regla in v for v in vistos), "se pidió la regla del lactante"
    assert any("the fever is the parent" in v.lower() for v in vistos)
    assert not a.ask_age, "no hay que preguntar la edad del niño por la fiebre de la madre"
