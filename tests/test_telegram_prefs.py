"""Lo que el padre eligió tiene que seguir ahí mañana (8-sep-2026).

`/lang de` y `/country DE` se guardaban en un diccionario en memoria del proceso. La tabla
`tg_users` los tenía escritos desde el primer día y **nadie los leía nunca**, así que cada
reinicio del bot los borraba — y el despliegue reinicia `pedibot-telegram` todas las veces.

El padre no recibe ningún aviso de eso: simplemente, un día el bot le vuelve a contestar en el
idioma adivinado. Y con él se va el país, que es de donde sale el número al que llamar.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.index.store import Index, build_index
from pedibot.ingest.schema import Chunk
from pedibot.ops.store import OpsStore
from pedibot.telegram_bot import COUNTRY_SET, HELP, LANG_SET, STOPPED, TelegramFront

IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


def _engine(tmp_path: Path, config_dir) -> Engine:
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
                text="La fiebre no es peligrosa.",
                topic="fiebre",
                doc_type="hoja_padres",
                evidence="sociedad_cientifica",
                usage="publico",
                source_hash="h",
                n_words=5,
            )
        ],
        db,
    )
    return Engine(
        Retriever(Index(db), Synonyms(config_dir / "synonyms.yaml")),
        Triage(config_dir / "red_flags.yaml"),
        FakeProvider("x [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
    )


def test_the_language_and_country_survive_a_restart(tmp_path: Path, config_dir) -> None:
    ops_db = tmp_path / "ops.db"
    engine = _engine(tmp_path, config_dir)

    antes = TelegramFront(engine, OpsStore(ops_db))
    antes.handle_command(4242, "/lang de")
    antes.handle_command(4242, "/country DE")
    antes.handle_message(4242, "mein Kind hat Fieber")

    # el bot se reinicia: proceso nuevo, diccionario vacío, la misma base
    despues = TelegramFront(engine, OpsStore(ops_db))
    p = despues.prefs_for(4242)
    assert p.lang == "de", "el idioma elegido se ha perdido en el reinicio"
    assert p.country == "DE", "el país elegido se ha perdido, y con él el número de emergencias"


def test_an_unknown_chat_starts_empty(tmp_path: Path, config_dir) -> None:
    front = TelegramFront(_engine(tmp_path, config_dir), OpsStore(tmp_path / "ops.db"))
    p = front.prefs_for(99)
    assert p.lang is None and p.country is None


def test_a_language_no_longer_supported_is_not_restored(tmp_path: Path, config_dir) -> None:
    """Si un día se retira un idioma, quien lo tuviera guardado no puede quedarse colgado de él:
    el motor respondería en inglés y el bot creería estar en otro sitio."""
    ops = OpsStore(tmp_path / "ops.db")
    ops.touch_tg_user(7, "it", "IT")
    front = TelegramFront(_engine(tmp_path, config_dir), ops)
    p = front.prefs_for(7)
    assert p.lang is None and p.country == "IT"


@pytest.mark.parametrize("lang", IDIOMAS)
def test_everything_the_bot_says_on_its_own_is_written_in_every_language(lang: str) -> None:
    """Las cuatro tablas de texto que no pasan por el motor. `/stop` contestaba en inglés a seis
    idiomas y `/country` en castellano a seis, que es peor: parece un descuido de otro producto.
    """
    for nombre, tabla in (
        ("HELP", HELP),
        ("LANG_SET", LANG_SET),
        ("STOPPED", STOPPED),
        ("COUNTRY_SET", COUNTRY_SET),
    ):
        assert lang in tabla, f"{nombre} no está escrito en {lang}"
        assert tabla[lang].strip(), f"{nombre}[{lang}] está vacío"


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_country_reply_names_the_country(lang: str) -> None:
    assert "PT" in COUNTRY_SET[lang].format(c="PT")
