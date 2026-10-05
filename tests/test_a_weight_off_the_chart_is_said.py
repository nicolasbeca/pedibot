"""Un peso fuera de la curva se dice (5-oct-2026).

Consulta real desde Alemania: «Mein Kind hat Erbrechen… (Alter: 4 Jahre) (Gewicht: 10 kg)».
10 kg a los 4 años está por debajo de −3 desviaciones en la curva de la OMS, sea niño (z −3,8) o
niña (z −3,6), y la respuesta no lo mencionó. O es una errata —y las dosis van por peso— o es un
niño que necesita que lo vean. En los dos casos el padre tiene que saberlo.

Sin el sexo no hay curva, así que sólo se avisa cuando el peso queda fuera para los dos: así no
hay que preguntar y nunca se avisa de más.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.growth import Growth, aviso_peso_extremo

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def curvas() -> Growth:
    return Growth(RAIZ / "config" / "who_growth.json")


def test_diez_kilos_a_los_cuatro_anos_se_dice(curvas: Growth) -> None:
    nota = aviso_peso_extremo(curvas, 48, 10.0, "de")
    assert nota is not None
    assert "10 kg" in nota


@pytest.mark.parametrize("lang", ["en", "es", "fr", "de", "pt", "ru", "ar", "hi"])
def test_en_las_ocho_lenguas(curvas: Growth, lang: str) -> None:
    assert aviso_peso_extremo(curvas, 48, 10.0, lang)
    assert aviso_peso_extremo(curvas, 24, 30.0, lang)  # 30 kg a los 2 años: por arriba


@pytest.mark.parametrize(
    ("meses", "kg"),
    [
        (48, 16.0),  # un niño de 4 años normal
        (8, 8.2),  # 18 lb a los 8 meses
        (24, 12.0),
        (48, 12.5),  # bajo para un niño y no para una niña: sin sexo, no se avisa
    ],
)
def test_un_peso_normal_no_dice_nada(curvas: Growth, meses: float, kg: float) -> None:
    assert aviso_peso_extremo(curvas, meses, kg, "en") is None


def test_fuera_de_la_tabla_no_se_inventa(curvas: Growth) -> None:
    assert aviso_peso_extremo(curvas, 400, 10.0, "en") is None
    assert aviso_peso_extremo(curvas, 48, 0.1, "en") is None


def test_el_chat_lo_dice(tmp_path: pathlib.Path, config_dir) -> None:
    """La consulta real, de punta a punta: el aviso va debajo de la respuesta."""
    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.drugs import DrugCatalog
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
                chunk_id="rki_de_noro#s#1",
                doc_id="rki_de_noro",
                org="RKI",
                doc_title="Noroviren",
                year=None,
                lang="de",
                section="S",
                pages=[1],
                text="Erbrechen und Durchfall sind typisch.",
                topic="digestivo",
                doc_type="hoja_padres",
                evidence="organismo_publico",
                usage="publico",
                source_hash="h",
                n_words=5,
            )
        ],
        db,
    )
    motor = Engine(
        Retriever(
            Index(db),
            Synonyms(config_dir / "synonyms.yaml"),
            taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
        ),
        Triage(config_dir / "red_flags.yaml"),
        FakeProvider("Laut RKI x [1]."),
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(config_dir / "drugs.yaml"),
        growth=Growth(config_dir / "who_growth.json"),
    )
    a = motor.ask(
        "Mein Kind hat Erbrechen. Was kann ich tun? (Alter: 4 Jahre) (Gewicht: 10 kg)",
        country="DE",
        lang="de",
    )
    assert "10 kg ist für 4 Jahre" in a.text, a.text
    b = motor.ask(
        "Mein Kind hat Erbrechen. Was kann ich tun? (Alter: 4 Jahre) (Gewicht: 16 kg)",
        country="DE",
        lang="de",
    )
    assert "Hinweis:" not in b.text
