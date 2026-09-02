"""French safety layer (fase francesa, paso 2 — 3-sep-2026).

The rule that gates everything: a French website may not exist before the triage reads French.
These are the phrases a French parent would type at 3am; every one must fire the same rule and
level as its Spanish and English twins. The age parser matters just as much — «il a 2 mois avec
de la fièvre» must land on the under-3-months rule, and it only does if "mois" parses.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pedibot.api import ApiConfig, create_app
from pedibot.bot.answer import EmergencyNumbers, Engine, build_banner
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms, detect_lang
from pedibot.bot.triage import Triage, parse_age_months
from pedibot.index.store import Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk
from pedibot.ops.store import OpsStore


@pytest.fixture(scope="module")
def triage(config_dir) -> Triage:
    return Triage(config_dir / "red_flags.yaml")


@pytest.fixture()
def client_fr(tmp_path: Path, config_dir):
    """The whole API with a one-chunk index: enough to check that French gets through."""
    db = tmp_path / "i.db"
    build_index(
        [
            Chunk(
                chunk_id="seup_fiebre#s#1",
                doc_id="seup_fiebre",
                org="SEUP",
                doc_title="Fiebre",
                year=None,
                lang="es",
                section="S",
                pages=[1],
                text="La fiebre no es peligrosa por si misma.",
                topic="fiebre",
                doc_type="hoja_padres",
                evidence="sociedad_cientifica",
                usage="publico",
                source_hash="h",
                n_words=6,
            )
        ],
        db,
    )
    engine = Engine(
        Retriever(
            Index(db),
            Synonyms(config_dir / "synonyms.yaml"),
            taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
        ),
        Triage(config_dir / "red_flags.yaml"),
        FakeProvider("Selon la SEUP, la fièvre n'est pas dangereuse en soi [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
    )
    return TestClient(
        create_app(engine, OpsStore(tmp_path / "ops.db"), ApiConfig(allowed_origins=["*"]))
    )


# ── emergencias ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("phrase", "rule"),
    [
        ("mon bébé ne répond pas, il est inconscient", "not_responding"),
        ("ma fille ne se réveille pas", "not_responding"),
        ("il fait des convulsions depuis deux minutes", "seizure"),
        ("mon fils n'arrive pas à respirer", "severe_breathing"),
        ("elle a du mal à respirer et ses lèvres sont bleues", "severe_breathing"),
        ("il a arrêté de respirer quelques secondes", "severe_breathing"),
        ("ses lèvres et sa langue sont gonflées après une cacahuète", "anaphylaxis"),
        ("mon bébé s'étouffe avec un morceau de pomme", "choking"),
        ("il a fait une fausse route et tousse sans pouvoir respirer", "choking"),
        ("sa peau est marbrée et grise", "mottled_skin"),
        ("il est tombé sur la tête et a perdu connaissance", "head_injury_loss_consciousness"),
        ("la plaie n'arrête pas de saigner", "severe_bleeding"),
        ("on voit l'os, je crois que c'est une fracture ouverte", "open_fracture"),
        ("des taches sur la peau qui ne disparaissent pas quand j'appuie", "petechiae_fever"),
        ("elle a des pétéchies et de la fièvre", "petechiae_fever"),
    ],
)
def test_a_french_emergency_fires_the_rule(triage, phrase, rule):
    tr = triage.assess(phrase)
    assert tr.level == "emergency", phrase
    assert rule in [r.id for r in tr.matched], phrase


# ── urgentes ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("phrase", "rule"),
    [
        ("il respire très vite et fait un sifflement", "moderate_breathing"),
        ("elle est très somnolente, difficile à réveiller", "drowsy_irritable"),
        ("yeux enfoncés et couche sèche depuis ce matin", "dehydration"),
        ("il vomit et se plaint d'un fort mal de tête", "vomiting_headache"),
        ("il s'est cogné la tête hier et ce matin il vomit", "vomiting_after_head_injury"),
        ("elle a avalé une pile bouton", "foreign_body_ingestion"),
        ("il a bu de l'eau de javel", "poisoning"),
        ("mal au ventre très fort qui empire depuis des heures", "severe_abdominal_pain"),
        ("son poignet est tordu et déformé après la chute", "deformity_fracture"),
        ("mon nouveau-né refuse de téter depuis hier", "newborn_refusing_feeds"),
        ("il s'est brûlé la main avec le fer à repasser", "burn"),
    ],
)
def test_a_french_urgent_sign_fires_the_rule(triage, phrase, rule):
    tr = triage.assess(phrase)
    assert tr.level in ("urgent", "emergency"), phrase
    assert rule in [r.id for r in tr.matched], phrase


def test_french_mental_health_protocol(triage):
    tr = triage.assess("ma fille dit qu'elle veut mourir")
    assert tr.level == "mental_health"
    tr2 = triage.assess("mon ado se fait du mal, il se coupe")
    assert tr2.level == "mental_health"


def test_a_routine_french_question_stays_routine(triage):
    assert triage.assess("mon fils de 4 ans a un rhume, que faire ?").level == "routine"
    assert triage.assess("quels vaccins à 6 mois ?").level == "routine"


# ── edad y fiebre en francés ─────────────────────────────────────────────────


def test_french_ages_parse():
    assert parse_age_months("il a 2 mois") == 2
    assert parse_age_months("ma fille de 3 ans") == 36
    assert parse_age_months("un bébé de 6 semaines") == pytest.approx(6 / 4.345, abs=0.1)
    assert parse_age_months("il a 10 jours de vie") == pytest.approx(10 / 30.4, abs=0.05)
    assert parse_age_months("deux mois") == 2


def test_a_two_month_old_with_fever_in_french_is_urgent(triage):
    tr = triage.assess("mon bébé de 2 mois a de la fièvre")
    assert tr.level == "urgent"
    assert "infant_fever_under_3_months" in [r.id for r in tr.matched]


# ── idioma y textos ──────────────────────────────────────────────────────────


def test_french_is_detected():
    assert detect_lang("mon bébé de 2 mois a de la fièvre, que faire ?") == "fr"
    assert detect_lang("ma fille tousse beaucoup la nuit") == "fr"
    # the other two must not regress
    assert detect_lang("mi hijo tiene fiebre") == "es"
    assert detect_lang("my son has a fever") == "en"


def test_the_banner_speaks_french(triage):
    tr = triage.assess("mon bébé ne répond pas")
    banner = build_banner(tr, "fr", {"emergency": "15 / 112", "poison": None, "mental": "3114"})
    assert banner is not None and "15 / 112" in banner
    assert "Appelle" in banner or "urgences" in banner
    assert "Ne répond pas" in banner  # the reason, in French, not in English


# ── la puerta de entrada ──────────────────────────────────────────────────────


def test_the_api_accepts_french(client_fr):
    """A French triage that the API refuses to receive is a French triage that does not exist."""
    r = client_fr.post(
        "/api/ask", json={"question": "mon bébé ne répond pas", "lang": "fr", "country": "FR"}
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["level"] == "emergency"
    assert j["banner"] and "15 / 112" in j["banner"]  # the French number, not 112 by default


def test_french_without_saying_the_language(client_fr):
    """The parent types French and never picks a language: detection has to carry it."""
    j = client_fr.post("/api/ask", json={"question": "ma fille de 2 mois a de la fièvre"}).json()
    assert j["level"] == "urgent" and j["lang"] == "fr"
