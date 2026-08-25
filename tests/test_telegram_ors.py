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
    assert "Fuentes:" in text and aid >= 1
    assert front.feedback(7, aid, 1) is True
    assert front.feedback(8, aid, 1) is False  # another chat cannot rate
    text2, _ = front.handle_message(7, "¿y si además vomita?")
    assert "Fuentes:" in text2 or "No tengo" in text2
    assert len(front.ops.history(front.session_for(7))) == 4
    assert front.session_for(7) != front.session_for(8)
