"""Cuando el fármaco no es para este niño, no se dice cuánto (8-sep-2026).

Decisión del operador. Lo que había: para un bebé de dos meses y cinco kilos, la calculadora
escribía «⚠️ no dar sin consultar: menor de 3 meses, por debajo de la edad mínima» y a
continuación **50 mg** y la tabla de mililitros bote a bote — de ibuprofeno, que su propia ficha
del catálogo excluye por debajo de tres meses y de cinco kilos. En la web era peor todavía: los
50 mg iban en tipografía grande arriba del todo y el aviso quedaba debajo de la tabla.

A las tres de la madrugada se leen los números.

Se conserva lo que ayuda a decidir —qué fármaco es, por qué no, y de dónde sale la norma— y
desaparece lo único que se podría echar en una jeringa. Los dos frentes a la vez, porque son dos
códigos distintos para el mismo número (ver test_two_calculators_agree.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pedibot.api import ApiConfig, create_app
from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.dose import calculate, format_result, presentation_label
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.index.store import Index, build_index
from pedibot.ingest.schema import Chunk
from pedibot.ops.store import OpsStore

IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


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
        Retriever(Index(db), Synonyms(config_dir / "synonyms.yaml")),
        Triage(config_dir / "red_flags.yaml"),
        FakeProvider("x [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(config_dir / "drugs.yaml"),
    )
    return TestClient(
        create_app(engine, OpsStore(tmp_path / "ops.db"), ApiConfig(allowed_origins=["*"]))
    )


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_chat_gives_no_figure_for_a_drug_this_child_may_not_have(lang: str) -> None:
    texto = format_result(calculate("ibuprofeno", 5.0, 2.0), lang)
    assert "50 mg" not in texto, f"[{lang}] sigue diciendo los miligramos"
    assert " ml" not in texto, f"[{lang}] sigue diciendo los mililitros"
    assert "AEPap" in texto, f"[{lang}] se ha llevado por delante la fuente"


def test_the_chat_still_gives_the_figure_when_the_drug_is_for_this_child() -> None:
    """La otra mitad: quitar la dosis a quien sí puede tomarla rompería la herramienta."""
    texto = format_result(calculate("paracetamol", 14.0, 36.0), "en")
    assert "210 mg" in texto and "8.7 ml" in texto


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_web_gives_no_figure_either(client, lang: str) -> None:
    j = client.post(
        "/api/dose",
        json={"drug": "nurofen", "weight_kg": 5, "age_months": 2, "lang": lang},
    ).json()
    assert j["refer"] is True
    assert j["mg"] is None and j["mg_min"] is None and j["mg_max"] is None
    assert j["ml_by_form"] == []
    assert j["source"] and j["notes"], f"[{lang}] sin motivo ni fuente no queda nada útil"


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_reason_is_written_in_words_the_parent_reads(client, lang: str) -> None:
    """La web pintaba los identificadores internos tal cual, teniendo las ocho traducciones."""
    j = client.post(
        "/api/dose",
        json={"drug": "nurofen", "weight_kg": 5, "age_months": 2, "lang": lang},
    ).json()
    assert j["warnings_text"], f"[{lang}] sin texto de aviso"
    assert "under_3_months_refer" not in j["warnings_text"]
    assert all("_" not in w for w in j["warnings_text"]), f"[{lang}] {j['warnings_text']}"


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_bottle_is_named_in_the_readers_language(client, lang: str) -> None:
    """«jarabe» y «gotas» son palabras nuestras, no lo que pone en la caja: se traducen.

    Salían en castellano en los ocho idiomas, en la lista donde un padre busca SU bote. El
    comprobador de fugas de idioma no las ve: mira las páginas construidas, y esta lista la
    pinta el navegador con lo que responde el API.
    """
    j = client.post(
        "/api/dose", json={"drug": "paracetamol", "weight_kg": 14, "lang": lang}
    ).json()
    formas = " ".join(f["form"] for f in j["ml_by_form"])
    if lang != "es":
        assert "jarabe" not in formas, f"[{lang}] {formas}"
    # el portugués escribe «gotas» igual que el castellano: ahí no hay fuga que buscar
    if lang not in ("es", "pt"):
        assert "gotas" not in formas, f"[{lang}] {formas}"
    assert any(str(p) in formas for p in (120, 100)), f"[{lang}] se ha perdido la concentración"


def test_a_brand_keeps_the_words_printed_on_its_box() -> None:
    """Lo contrario también: «infant», «six plus» o «baby drops» es lo que un padre tiene en la
    mano, y traducirlo le quitaría la forma de encontrarlo en la lista."""
    assert presentation_label("infant 120 mg/5 ml", "de") == "infant 120 mg/5 ml"
    assert presentation_label("six plus 250 mg/5 ml", "ru") == "six plus 250 mg/5 ml"


# ---------------------------------------------------------------------------------------------
# Sin edad, un fármaco con edad mínima tampoco da la cifra (9-sep-2026)
#
# El desplegable de la web tiene una opción que dice literalmente «no lo sé». Con ella, el
# ibuprofeno a 5 kg devolvía la dosis entera y sin un solo aviso — y 5 kg es un peso de lactante.
# El ibuprofeno no se da por debajo de tres meses ni de cinco kilos.
#
# Sin la edad no se puede descartar la contraindicación, así que se trata igual que cuando SÍ
# sabemos que no toca: se dice por qué y no se dice cuánto. El paracetamol no tiene edad mínima,
# así que el caso corriente sigue funcionando sin indicarla.


@pytest.mark.parametrize("lang", IDIOMAS)
def test_without_an_age_a_drug_with_a_minimum_age_gives_no_figure(lang: str) -> None:
    r = calculate("ibuprofeno", 5.0, None)
    assert r.refer is True, "sin edad, el ibuprofeno daba la dosis entera"
    assert "age_unknown" in r.warnings
    texto = format_result(r, lang)
    assert "50 mg" not in texto and " ml" not in texto, f"[{lang}] sigue diciendo la cifra"


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_reason_names_the_missing_age(lang: str) -> None:
    """El aviso tiene que decir qué falta, no solo que no se da: el padre sabe la edad y con eso
    puede volver a preguntar."""
    from pedibot.bot.strings import tool_strings

    texto = tool_strings(lang)["dose_warn"]["age_unknown"]
    assert texto.strip() and "_" not in texto, f"[{lang}] aviso vacío o sin traducir"


def test_a_drug_without_a_minimum_age_still_works_without_one() -> None:
    """La otra mitad: el paracetamol no tiene edad mínima, y exigirla habría roto el caso
    corriente para no ganar nada."""
    r = calculate("paracetamol", 14.0, None)
    assert r.refer is False and r.mg == 210.0


def test_a_valid_age_is_unaffected() -> None:
    r = calculate("ibuprofeno", 20.0, 48)
    assert r.refer is False and r.mg == 200.0
