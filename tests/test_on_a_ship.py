"""En un barco, primero el centro médico de a bordo (30-sep-2026).

«Vamos de crucero por el Mediterráneo con un bebé de 10 meses: ¿a qué número llamo si hay una
urgencia en el barco?» recibía «en España, el número de urgencias es el 112». En alta mar el 112
no suena, y lo que hay que hacer lo dice el CDC (Travelers' Health, dominio público): «report
your symptoms to the ship's medical center». Los números del país siguen debajo, que en puerto o
en tierra sí sirven.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import en_un_barco


@pytest.mark.parametrize(
    "texto",
    [
        "Vamos de crucero con el bebé, ¿a qué número llamo si hay una urgencia en el barco?",
        "We're on a cruise ship, what number do I call in an emergency?",
        "Nous sommes en croisière, quel numéro appeler ?",
        "Wir sind auf einer Kreuzfahrt, welche Notrufnummer?",
        "Estamos num cruzeiro, para que número ligo?",
        "Мы в круизе, какой номер экстренной помощи?",
    ],
)
def test_se_reconoce_el_barco(texto: str):
    assert en_un_barco(texto)


@pytest.mark.parametrize(
    "texto", ["¿Cuál es el número de urgencias en España?", "Emergency number in Kenya?"]
)
def test_en_tierra_no(texto: str):
    assert not en_un_barco(texto)


def test_la_respuesta_empieza_por_el_centro_medico_del_barco(tmp_path, config_dir):
    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.llm import FakeProvider
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.bot.triage import Triage
    from pedibot.index.store import Index, build_index

    db = tmp_path / "i.db"
    build_index([], db)
    eng = Engine(
        Retriever(Index(db), Synonyms(config_dir / "synonyms.yaml")),
        Triage(config_dir / "red_flags.yaml"),
        FakeProvider("x"),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
    )
    a = eng.ask(
        "Vamos de crucero con un bebé de 10 meses. ¿A qué número llamo si hay una urgencia "
        "en el barco?",
        country="ES",
    )
    assert a.verification == "emergency_number"
    primera = a.text.strip().splitlines()[0].lower()
    assert "barco" in primera and "médico" in primera, a.text
    assert "CDC" in a.text and "112" in a.text
