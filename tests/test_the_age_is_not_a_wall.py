"""La edad no puede ser un muro (12-sep-2026).

Medido en el registro de producción (137 respuestas reales): el bot pidió la edad **11 veces, y
10 de esos padres no volvieron a escribir**. La sesión media tiene 1,01 preguntas. Un padre
árabe preguntó tres veces si era malaria y las tres veces se le pidió la edad. La regla que lo
motivaba es buena —fiebre en un lactante de menos de tres meses es urgente y sin edad no se
sabe—, pero pedirla ANTES de responder la convertía en un muro que el padre no cruzaba.

Ahora, con fiebre y sin edad, se **responde**: la respuesta abre con la regla del lactante
(«si tiene menos de tres meses, al médico hoy»), evita dosis concretas, y cierra pidiendo la
edad para afinar; la API lo marca con `ask_age` y el chat pinta los botones de edad debajo de
la respuesta, no en su lugar.

Y el lector de edades, medido contra 39 formas naturales en las ocho lenguas, fallaba en
seis: «año y medio», «डेढ़ साल», «ano e meio», «1,5 года» (que leía **cinco años**),
«18 شهراً» (tanwin) y «un an et demi». Todas de un niño de 18 meses: justo la edad en que la
dosis y las reglas cambian.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.answer import AGE_REFINES, EmergencyNumbers, Engine, _age_context
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage, TriageResult, parse_age_months
from pedibot.index.store import Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk

LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


# ── el lector de edades ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("frase", "meses"),
    [
        ("My 4-year-old has a fever of 38.8", 48),
        ("my 18-month-old", 18),
        ("4yo with fever", 48),
        ("a 6-week-old baby", 1.4),
        ("a year and a half", 18),
        ("she is 2.5 years old", 30),
        ("mi hijo de 4 años", 48),
        ("mi niña de 18 meses", 18),
        ("bebé de 3 semanas", 0.7),
        ("mi hijo de año y medio", 18),
        ("tiene un año y medio", 18),
        ("mon fils de 4 ans", 48),
        ("ma fille de 18 mois", 18),
        ("un an et demi", 18),
        ("mein Sohn ist 4 Jahre alt", 48),
        ("mein 4-jähriger", 48),
        ("anderthalb Jahre", 18),
        ("eineinhalb Jahre alt", 18),
        ("сыну 4 года", 48),
        ("дочке 18 месяцев", 18),
        ("ребенок 1,5 года", 18),
        ("полтора года", 18),
        ("моему сыну 5 лет", 60),
        ("ابني عمره 4 سنوات", 48),
        ("طفلي عمره سنتان", 24),
        ("رضيعي عمره شهران", 2),
        ("ابنتي عمرها 18 شهراً", 18),
        ("عمره سنة ونصف", 18),
        ("मेरा बेटा 4 साल का है", 48),
        ("मेरी बेटी 18 महीने की है", 18),
        ("बच्चा डेढ़ साल का", 18),
        ("मेरा 2 साल का बच्चा", 24),
        ("o meu filho de 4 anos", 48),
        ("a minha filha de 18 meses", 18),
        ("tem 1 ano e meio", 18),
        ("um ano e meio", 18),
    ],
)
def test_la_edad_se_lee_como_la_dice_el_padre(frase: str, meses: float):
    got = parse_age_months(frase)
    assert got is not None and abs(got - meses) < 0.6, f"«{frase}» → {got}, esperaba {meses}"


def test_una_cifra_suelta_no_es_una_edad():
    """«she is 5» o «(3)» pueden ser cualquier cosa: mejor no saberla que inventarla."""
    assert parse_age_months("she is 5") is None
    assert parse_age_months("my toddler (3) has a rash") is None
    assert parse_age_months("fiebre de 39 desde hace 2 días") is None


# ── responder sin edad ────────────────────────────────────────────────────────────────────
def _chunk(cid: str, text: str, lang: str = "es") -> Chunk:
    return Chunk(
        chunk_id=cid,
        doc_id=cid.split("#")[0],
        org="SEUP",
        doc_title="Fiebre. Información para padres",
        year=None,
        lang=lang,
        section="¿Qué hacer?",
        pages=[1],
        text=text,
        topic="fiebre",
        doc_type="hoja_padres",
        evidence="sociedad_cientifica",
        usage="publico",
        source_url="https://seup.org/fiebre.pdf",
        source_hash="h",
        n_words=len(text.split()),
    )


@pytest.fixture
def engine(tmp_path: Path, config_dir):
    db = tmp_path / "i.db"
    build_index(
        [
            _chunk(
                "seup_fiebre#que_hacer#1",
                "La fiebre no es peligrosa por sí misma, según la SEUP. Ofrezca líquidos. "
                "Acuda a urgencias si el niño tiene menos de 3 meses.",
            )
        ],
        db,
    )
    llm = FakeProvider(
        "Si tiene menos de tres meses, debe verlo un médico hoy. Con más edad, la fiebre no es "
        "peligrosa por sí misma, según la SEUP [1]. Ofrezca líquidos [1]."
    )
    eng = Engine(
        Retriever(
            Index(db),
            Synonyms(config_dir / "synonyms.yaml"),
            taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
        ),
        Triage(config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
    )
    return eng, llm


def test_con_fiebre_y_sin_edad_se_responde_y_se_pide_la_edad_despues(engine):
    eng, llm = engine
    a = eng.ask("mi hijo tiene fiebre")
    assert a.verification == "ok", "sin edad se sigue devolviendo asked_age: el muro sigue ahí"
    assert llm.calls, "no se llamó al modelo: no se respondió"
    assert a.ask_age is True
    assert a.text.rstrip().endswith(AGE_REFINES["es"]), "la respuesta no cierra pidiendo la edad"
    assert "no es peligrosa" in a.text


def test_con_edad_no_se_pide(engine):
    eng, _ = engine
    a = eng.ask("mi hijo de 4 años tiene fiebre")
    assert a.verification == "ok" and a.ask_age is False
    assert AGE_REFINES["es"] not in a.text


def test_sin_fiebre_no_se_pide(engine):
    eng, _ = engine
    a = eng.ask("mi hijo tiene mocos y tos")
    assert a.ask_age is False


def test_el_modelo_recibe_la_regla_del_lactante_cuando_no_hay_edad():
    ctx = _age_context(TriageResult(level="routine", matched=[], age_months=None, has_fever=True))
    assert "3 months" in ctx and "unknown" in ctx.lower()
    assert "dose" in ctx.lower(), (
        "sin edad no se pueden dar dosis concretas, y el modelo no lo sabe"
    )


@pytest.mark.parametrize("lang", LANGS)
def test_la_pregunta_final_esta_en_cada_lengua(lang: str):
    assert AGE_REFINES[lang].strip()
    if lang != "en":
        assert AGE_REFINES[lang] != AGE_REFINES["en"]


def test_la_api_y_el_chat_llevan_el_campo():
    from pedibot.api import AskOut
    from pedibot.settings import ROOT

    assert "ask_age" in AskOut.model_fields and AskOut.model_fields["ask_age"].default is False
    chat = (ROOT / "web/site/src/components/Chat.astro").read_text(encoding="utf-8")
    assert "j.ask_age" in chat, "el chat no pinta los botones de edad debajo de la respuesta"
    trozo = chat[chat.index("j.ask_age") :][:300]
    assert "return h" not in trozo, "con ask_age el chat corta la respuesta como si fuera asked_age"
