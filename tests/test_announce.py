from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.announce import send_announcement, too_soon
from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.index.store import Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk
from pedibot.ops.store import OpsStore
from pedibot.telegram_bot import TelegramFront


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
        FakeProvider("Según la SEUP [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
    )
    return TelegramFront(engine, OpsStore(tmp_path / "ops.db"))


def test_audience_and_opt_out(front):
    front.handle_command(11, "/start")
    front.handle_message(12, "mi hijo de 4 años tiene fiebre")
    assert {c for c, _ in front.ops.tg_audience()} == {11, 12}
    assert front.handle_command(12, "/stop").startswith("Done") or "Listo" in front.handle_command(
        12, "/stop"
    )
    assert {c for c, _ in front.ops.tg_audience()} == {11}
    front.handle_command(12, "/start")  # re-subscribes
    assert {c for c, _ in front.ops.tg_audience()} == {11, 12}


def test_dry_run_and_guard(front):
    front.handle_command(11, "/start")
    res = send_announcement(front.ops, "tok", "New: vaccine schedules", dry_run=True)
    assert res == {"audience": 1, "sent": 1, "failed": 0}
    assert too_soon(front.ops)[0] is False  # dry run does not log
    front.ops.log_announcement("x", 1, 0)
    assert too_soon(front.ops)[0] is True
