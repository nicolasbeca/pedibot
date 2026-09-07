from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pedibot.api import ApiConfig, create_app
from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.llm import FakeProvider
from pedibot.bot.photo import interpret, parse
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.bot.vaccines import Vaccines, format_answer, is_vaccine_question
from pedibot.index.store import Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk
from pedibot.ops.store import OpsStore


@pytest.fixture(scope="module")
def vax(config_dir):
    return Vaccines(config_dir / "vaccines.yaml")


def test_vaccines_countries_and_lookup(vax):
    assert set(vax.countries) >= {"ES", "GB", "US", "FR", "DE"}
    assert vax.resolve_country("uk") == "GB" and vax.resolve_country("fr") == "FR"
    due, nxt = vax.at_age("ES", 4, "es")
    assert any("MenC" in v for s in due for v in s.vaccines) and nxt and nxt.age_months == 11
    due_gb, _ = vax.at_age("GB", 12, "en")
    assert any("MMRV" in v for s in due_gb for v in s.vaccines)
    txt = format_answer(vax, "US", 2, "en")
    assert "DTaP (dose 1)" in txt and "CDC" in txt
    assert is_vaccine_question("what vaccines does a 4 month old get") and not is_vaccine_question(
        "tiene fiebre"
    )


def test_photo_interpretation():
    d = parse('{"petechiae":"yes","cyanosis":"no","swelling":"no","quality":"ok","note":"spots"}')
    level, text = interpret(d, "en", "999")
    assert level == "urgent" and "glass test" in text
    level2, text2 = interpret(
        parse('{"petechiae":"no","cyanosis":"yes","swelling":"no","quality":"ok","note":""}'),
        "es",
        "112",
    )
    assert level2 == "emergency" and "112" in text2
    assert interpret(parse("garbage"), "en", "911")[0] == "unsure"
    ok_level, ok_text = interpret(
        parse('{"petechiae":"no","cyanosis":"no","swelling":"no","quality":"ok","note":""}'),
        "en",
        "911",
    )
    assert ok_level == "routine" and "cannot replace an examination" in ok_text


@pytest.fixture
def client(tmp_path: Path, config_dir):
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
    engine = Engine(
        Retriever(
            Index(db),
            Synonyms(config_dir / "synonyms.yaml"),
            taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
        ),
        Triage(config_dir / "red_flags.yaml"),
        FakeProvider("x [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(config_dir / "drugs.yaml"),
        vaccines=Vaccines(config_dir / "vaccines.yaml"),
    )

    def fake_vision(*a, **k):
        return (
            '{"petechiae":"yes","cyanosis":"no","swelling":"no","quality":"ok","note":"t"}',
            0.0001,
        )

    return TestClient(
        create_app(
            engine,
            OpsStore(tmp_path / "ops.db"),
            ApiConfig(allowed_origins=["*"]),
            vision_fn=fake_vision,
        )
    )


def test_vaccine_api_and_chat_routing(client):
    j = client.get("/api/vaccines?country=GB&age_months=2&lang=en").json()
    assert j["country"] == "GB" and any("6-in-1" in v for s in j["due"] for v in s["vaccines"])
    assert client.get("/api/vaccines?country=IT").status_code == 404
    a = client.post(
        "/api/ask",
        json={"question": "what vaccines does my 4 month old get?", "country": "ES", "lang": "en"},
    ).json()
    assert a["verification"] == "vaccine_schedule" and "MenC" in a["text"]


def test_photo_api(client, monkeypatch):
    from pedibot import settings as st

    monkeypatch.setattr(
        st,
        "get_settings",
        lambda: type(
            "S",
            (),
            {
                "photo_enabled": True,
                "deepseek_api_key": "k",
                "deepseek_base_url": "u",
                "deepseek_vision_model": "m",
            },
        )(),
    )
    import pedibot.api as api_mod

    monkeypatch.setattr(api_mod, "get_settings", st.get_settings, raising=False)
    r = client.post(
        "/api/photo",
        json={"image_b64": "A" * 200, "mime": "image/png", "lang": "en", "country": "GB"},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["level"] == "urgent" and "glass test" in j["text"] and j["signs"]["petechiae"] == "yes"


def test_french_and_german_schedules_lock_the_2026_facts(vax):
    """Transcribed on 2-sep-2026 from the official pages, not from memory — and rightly so:
    the STIKO 2026 calendar moved meningococcal ACWY to 12-14 YEARS and dropped the old MenC
    dose at 12 months, and France made MenB (3/5/12 m) and MenACWY (6+12 m) MANDATORY on
    1-jan-2025. These asserts exist so a future re-transcription cannot silently regress."""
    # France writes its own names: Méningocoque B at 3 months, mandatory
    due_fr, _ = vax.at_age("FR", 3, "en")
    assert any("Méningocoque B" in v and "obligatoire" in v for s in due_fr for v in s.vaccines)
    # France: MenACWY starts at 6 months
    due_fr6, _ = vax.at_age("FR", 6, "en")
    assert any("Méningocoque ACWY" in v for s in due_fr6 for v in s.vaccines)
    # Germany: MenB is an infant series (2 months onwards)...
    due_de, _ = vax.at_age("DE", 2, "en")
    assert any("MenB" in v for s in due_de for v in s.vaccines)
    # ...and MenACWY is the adolescent dose at 12-14 years, NOT at 12 months
    due_de12m, _ = vax.at_age("DE", 12, "en")
    assert not any("ACWY" in v for s in due_de12m for v in s.vaccines)
    due_de13y, _ = vax.at_age("DE", 150, "en")
    assert any("ACWY" in v for s in due_de13y for v in s.vaccines)


def test_the_portuguese_schedule_is_the_pnv_2025_not_the_2020(vax):
    """Publicábamos un calendario derogado (7-sep-2026).

    La ficha citaba el «PNV 2020, Norma 18/2020». La DGS lo sustituyó **en octubre de 2025** por
    el PNV 2025 (Livro Azul de Vacinas, Parte 1), que dice literalmente: *"O presente PNV
    substitui, a partir de outubro de 2025, o PNV 2020"*. Sus dos cambios principales, tal y como
    los enumera el propio documento:

      · Substituição da vacina MenC pela vacina MenACWY aos 12 meses de idade.
      · Substituição da vacina Pn13 pela vacina Pn20 aos 2, 4 e 12 meses de idade.

    Transcrito del Quadro n.º 1 leyendo las coordenadas del PDF, no la mancha de texto: la tabla
    es un gráfico y `pdftotext -layout` mezcla las columnas. Al hacerlo apareció además una
    ausencia que venía de antes: **faltaba la Td de los 10 años**.

    Estos asertos existen para que una futura re-transcripción no lo deshaga en silencio.
    """
    doce, _ = vax.at_age("PT", 12, "en")
    puestas = [v for s in doce for v in s.vaccines]
    assert any("MenACWY" in v for v in puestas), "a los 12 meses el PNV 2025 pone MenACWY"
    assert not any("MenC)" in v for v in puestas), "el MenC de los 12 meses ya no está"
    assert any("Pn20" in v for v in puestas)
    for edad in (2, 4):
        due, _ = vax.at_age("PT", edad, "en")
        assert any("Pn20" in v for s in due for v in s.vaccines), f"Pn20 a los {edad} meses"
    diez, _ = vax.at_age("PT", 120, "en")
    assert any("Td" in v for s in diez for v in s.vaccines), "la Td de los 10 años faltaba"


def test_every_schedule_says_which_edition_it_transcribes(vax):
    """Un calendario sin año no se puede comprobar, y el de Portugal llevaba cinco años caducado
    sin que nada lo notara.

    La cita tiene que decir **qué edición se transcribió**: el año del documento cuando lo lleva,
    y la fecha de consulta cuando la fuente es una página viva que no imprime edición (el caso de
    Brasil, que este candado cazó al escribirse)."""
    import re

    import yaml

    raiz = Path(__file__).resolve().parents[1]
    raw = yaml.safe_load((raiz / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    sin_año = [
        code for code, c in raw["countries"].items()
        if not re.search(r"\b20\d\d\b", c["source"])
    ]
    assert not sin_año, f"calendarios sin año en la cita: {sin_año}"
