from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.llm import FakeProvider
from pedibot.bot.ors import advise
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.index.store import Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk
from pedibot.ops.store import OpsStore
from pedibot.telegram_bot import TelegramFront


def test_ors_bands_and_sources():
    a = advise(0.5)
    assert a.refer and "under one month" in a.lines[0]
    b = advise(6, vomiting=True, lang="es")
    assert (
        b.age_band == "infant"
        and any("5–10 ml" in ln for ln in b.lines)
        and any("1–1,5" in ln for ln in b.lines)
    )
    assert any("SEUP" in s for s in b.sources) and any("AEMPS" in s for s in b.sources)
    c = advise(48)
    assert c.age_band == "child" and any("200 ml" in ln for ln in c.lines) and not c.refer


@pytest.fixture
def front(tmp_path: Path, config_dir):
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
                text="La fiebre no es peligrosa por sí misma.",
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
        FakeProvider("La fiebre no es peligrosa [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
    )
    return TelegramFront(engine, OpsStore(tmp_path / "ops.db"))


def test_commands(front):
    assert "guidelines" in front.handle_command(1, "/start")
    assert front.handle_command(1, "/country es") == "Country set to ES."
    assert front.handle_command(1, "/lang es").startswith("Idioma")
    assert "Cuéntame" in front.handle_command(1, "/help")
    assert front.handle_command(1, "/country") == "Usage: /country ES"
    assert front.handle_command(1, "hola") is None


def test_message_flow_and_feedback(front):
    front.handle_command(7, "/country ES")
    text, aid = front.handle_message(7, "mi hijo de 4 años tiene fiebre")
    assert "Fuentes:" not in text and "[1]" not in text and aid >= 1
    assert front.feedback(7, aid, 1) is True
    assert front.feedback(8, aid, 1) is False  # another chat cannot rate
    text2, _ = front.handle_message(7, "¿y si además vomita?")
    assert text2
    assert len(front.ops.history(front.session_for(7))) == 4
    assert front.session_for(7) != front.session_for(8)


# ---------------------------------------------------------------------------------------------
# Sin edad no se elige banda (9-sep-2026)
#
# `age_months` es opcional en `/api/ors`, y sin él se caía en la rama del niño mayor: «unos
# 200 ml de suero por cada deposición diarreica», que es la cantidad de un niño de más de un año,
# dicha a alguien que no ha contado la edad y podría tener un bebé de dos meses.
#
# Y de paso se perdía el aviso de los menores de dos años — justo con los más vulnerables, el
# único grupo al que ese aviso va dirigido.
#
# Ahora se dan las DOS indicaciones. Las dos se nombran solas («Lactante mayor de 1 mes…», «Niño
# a partir de 1 año…»), así que el padre, que sí sabe la edad, coge la suya. Es más texto, y es
# el único reparto que no puede darle de más a un lactante.


def test_without_an_age_both_amounts_are_given() -> None:
    from pedibot.bot.ors import advise

    a = advise(None, False, "es")
    assert a.age_band == "unknown"
    texto = " ".join(a.lines)
    assert "Lactante" in texto, "falta la indicación del lactante"
    assert "200 ml" in texto, "falta la indicación del niño mayor"


def test_without_an_age_the_under_two_warning_is_kept() -> None:
    from pedibot.bot.ors import advise

    a = advise(None, False, "es")
    assert any("2 años" in w for w in a.warnings), (
        "sin edad se perdía el aviso de los menores de dos años, que son a quienes va dirigido"
    )


def test_an_age_that_is_known_still_picks_one_band() -> None:
    """La otra mitad: cuando la edad SÍ está, se da una sola indicación y es la suya."""
    from pedibot.bot.ors import advise

    lactante = advise(3, False, "es")
    assert lactante.age_band == "infant"
    assert "200 ml" not in " ".join(lactante.lines), "a un lactante se le da la cantidad del niño"

    mayor = advise(18, False, "es")
    assert mayor.age_band == "child"
    assert "Lactante" not in " ".join(mayor.lines)


def test_a_newborn_gets_no_amount_at_all() -> None:
    """Menos de un mes: no hay cantidad que dar, hay que verlo un médico hoy."""
    from pedibot.bot.ors import advise

    a = advise(0.5, True, "es")
    assert a.refer is True and a.age_band == "under_1_month"
    assert "200 ml" not in " ".join(a.lines) and "5–10 ml" not in " ".join(a.lines)
