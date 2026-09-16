"""El percentil se calcula en el chat, no sólo en la página (16-sep-2026).

Medido contra lo vivo el 16-sep: «¿qué percentil tiene mi niña de 8 meses que pesa 7 kg?»
contestaba **«no puedo decirte el percentil exacto»** y ofrecía el enlace a la calculadora.
Tenía delante el sexo, la edad y el peso, y la tabla de la OMS estaba en el mismo servidor.

Las dosis y el calendario de vacunas ya funcionan así desde agosto: cuando el mensaje trae los
datos que la tabla necesita, se contesta **de la tabla** y el modelo no interviene. Esto le da
el mismo trato a la curva de crecimiento, con tres condiciones:

- hace falta el SEXO: la curva de una niña no es la de un niño, y sin él no hay percentil que
  dar. Sin sexo se sigue contestando de las fichas, con el enlace a la página;
- hace falta la EDAD (la lee el triaje, como para las dosis) y el peso o la talla;
- y la pregunta tiene que ser de crecimiento: «pesa 7 kg y tiene fiebre» no es un percentil.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.growth import Growth, measurements
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.bot.vaccines import Vaccines
from pedibot.index.store import Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def growth() -> Growth:
    return Growth(ROOT / "config" / "who_growth.json")


@pytest.fixture
def engine_factory(tmp_path: Path, growth: Growth):
    """El motor entero. Por defecto, con un modelo que REVIENTA si se le llama: una respuesta
    calculada de la tabla no puede pasar por él."""
    db = tmp_path / "i.db"
    build_index(
        [
            Chunk(
                chunk_id="nhs_en_baby_height_and_weight#s#1",
                doc_id="nhs_en_baby_height_and_weight",
                org="NHS",
                doc_title="Your baby's weight and height",
                year=2023,
                lang="es",
                section="S",
                pages=[1],
                text="Los percentiles son las líneas de las gráficas de crecimiento, según el NHS.",
                topic="desarrollo",
                doc_type="hoja_padres",
                evidence="organismo_publico",
                usage="publico",
                source_hash="h",
                n_words=12,
            )
        ],
        db,
    )
    cfg = ROOT / "config"

    def boom(system: str, user: str, **kw):  # noqa: ANN001, ANN202
        raise AssertionError("el modelo no debe intervenir en un percentil calculado")

    def make(responder=boom):  # noqa: ANN001, ANN202
        return Engine(
            Retriever(
                Index(db),
                Synonyms(cfg / "synonyms.yaml"),
                taxonomy=Taxonomy(cfg / "taxonomia.yaml"),
            ),
            Triage(cfg / "red_flags.yaml"),
            FakeProvider(responder),
            EmergencyNumbers(cfg / "emergency_numbers.yaml"),
            drugs=DrugCatalog(cfg / "drugs.yaml"),
            vaccines=Vaccines(cfg / "vaccines.yaml"),
            growth=growth,
        )

    return make


@pytest.fixture
def engine(engine_factory):
    return engine_factory()


# ── leer el mensaje ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "sex"),
    [
        ("mi niña de 8 meses pesa 7 kg", "f"),
        ("mi hija pesa 7 kg", "f"),
        ("mi niño de 8 meses pesa 7 kg", "m"),
        ("mi hijo varón pesa 7 kg", "m"),
        ("my daughter weighs 7 kg", "f"),
        ("my baby boy weighs 7 kg", "m"),
        ("ma fille pèse 7 kg", "f"),
        ("mon garçon pèse 7 kg", "m"),
        ("meine Tochter wiegt 7 kg", "f"),
        ("mein Sohn wiegt 7 kg", "m"),
        ("моя дочь весит 7 кг", "f"),
        ("мой сын весит 7 кг", "m"),
        ("ابنتي وزنها 7 كيلو", "f"),
        ("ابني وزنه 7 كيلو", "m"),
        ("मेरी बेटी का वजन 7 किलो है", "f"),
        ("मेरे बेटे का वजन 7 किलो है", "m"),
        ("minha filha pesa 7 kg", "f"),
        ("meu filho pesa 7 kg", "m"),
        ("mi bebé pesa 7 kg", None),  # sin sexo no hay curva
    ],
)
def test_el_sexo_se_lee_en_las_ocho_lenguas(text: str, sex: str | None) -> None:
    assert measurements(text)[0] == sex


@pytest.mark.parametrize(
    ("text", "kg", "cm"),
    [
        ("mi niña pesa 7 kg", 7.0, None),
        ("mi niña pesa 7,4 kg y mide 68 cm", 7.4, 68.0),
        ("my girl is 68 cm tall", None, 68.0),
        ("mi niño mide 1,05 m", None, 105.0),
        ("mein Mädchen ist 68 cm groß", None, 68.0),
        ("моя дочь 68 см", None, 68.0),
        ("ابنتي طولها 68 سم", None, 68.0),
        ("मेरी बेटी 68 सेमी", None, 68.0),
    ],
)
def test_el_peso_y_la_talla_se_leen(text: str, kg: float | None, cm: float | None) -> None:
    _, peso, talla = measurements(text)
    assert peso == kg and talla == cm


# ── la respuesta ─────────────────────────────────────────────────────────────


def test_el_percentil_se_contesta_de_la_tabla(engine) -> None:
    a = engine.ask("¿qué percentil tiene mi niña de 8 meses que pesa 7 kg?", lang="es")
    assert a.verification == "growth_chart"
    assert "percentil" in a.text.lower()
    assert "Peso para la edad" in a.text
    assert "OMS" in a.text or "WHO" in a.text
    assert a.tool is not None and a.tool.url == "/es/growth"


def test_la_cifra_es_la_misma_que_la_de_la_pagina(engine, growth: Growth) -> None:
    """Un número que sale por dos caminos distintos tiene que ser el mismo número."""
    a = engine.ask("¿qué percentil tiene mi niña de 8 meses que pesa 7 kg?", lang="es")
    esperado = growth.assess("f", 8, weight_kg=7.0).indicators[0].percentile
    assert f"{esperado:g}" in a.text


def test_sin_sexo_no_se_inventa_una_curva(engine_factory) -> None:
    """Se responde de las fichas, como hasta ahora, con el enlace a la calculadora."""
    eng = engine_factory("Los percentiles son las líneas de las gráficas, según el NHS [1].")
    a = eng.ask("¿qué percentil tiene mi bebé de 8 meses que pesa 7 kg?", lang="es")
    assert a.verification != "growth_chart"
    assert a.tool is not None and a.tool.kind == "growth"


def test_un_peso_con_fiebre_no_es_un_percentil(engine_factory) -> None:
    eng = engine_factory("La fiebre no es peligrosa por sí misma, según el NHS [1].")
    a = eng.ask("mi niña de 8 meses pesa 7 kg y tiene fiebre", lang="es")
    assert a.verification != "growth_chart"


def test_una_dosis_sigue_siendo_una_dosis(engine) -> None:
    """La rama de dosis va antes: «mi niña de 14 kg» con un medicamento es una dosis."""
    a = engine.ask("¿cuánto ibuprofeno le doy a mi niña de 3 años que pesa 14 kg?", lang="es")
    assert a.verification == "dose_calculator"


def test_la_desnutricion_grave_sale_avisada(engine) -> None:
    a = engine.ask("mi niña de 8 meses pesa 4,5 kg, ¿qué percentil es?", lang="es")
    assert a.verification == "growth_chart"
    assert "⚠️" in a.text
    assert a.level == "urgent"


def test_en_ingles_tambien(engine) -> None:
    a = engine.ask("what percentile is my 8 month old girl who weighs 7 kg?", lang="en")
    assert a.verification == "growth_chart"
    assert "percentile" in a.text.lower() and "Weight for age" in a.text
    assert a.tool is not None and a.tool.url == "/growth"


# ── dos turnos: lo de ahora manda ────────────────────────────────────────────
# Encontrado probando contra lo vivo el 16-sep, y NO lo veía ninguna prueba: los datos se leían
# del texto de toda la conversación, donde el mensaje viejo va primero. Preguntando por «mi niña
# de 8 meses que pesa 7 kg» y después por «mi niño de 3 años que pesa 13 kg y mide 92 cm», la
# segunda respuesta salió con el sexo, la edad y el peso de la PRIMERA y la talla de la segunda:
# 7 kg para 92 cm, o sea un aviso de desnutrición aguda grave a un niño que está bien.


def test_los_datos_del_mensaje_de_ahora_ganan_a_los_de_antes(engine) -> None:
    historia = [
        {"role": "user", "text": "¿qué percentil tiene mi niña de 8 meses que pesa 7 kg?"},
        {"role": "assistant", "text": "Peso para la edad: percentil 14,6."},
    ]
    a = engine.ask(
        "y mi niño de 3 años que pesa 13 kg y mide 92 cm, ¿qué percentil tiene?",
        lang="es",
        history=historia,
    )
    assert a.verification == "growth_chart"
    assert "13 kg" in a.text and "92 cm" in a.text
    assert "7 kg" not in a.text
    assert "niño" in a.text and "niña" not in a.text
    assert "3 años" in a.text
    assert a.level == "routine"  # no es una desnutrición: era el peso del otro niño


def test_lo_que_falta_hoy_se_toma_de_la_conversacion(engine) -> None:
    """Un padre cuenta en dos frases: «mi niña tiene 8 meses» y luego «pesa 7 kg»."""
    historia = [
        {"role": "user", "text": "mi niña tiene 8 meses"},
        {"role": "assistant", "text": "¿Qué te preocupa?"},
    ]
    a = engine.ask("pesa 7 kg, ¿qué percentil es?", lang="es", history=historia)
    assert a.verification == "growth_chart"
    assert "niña" in a.text and "7 kg" in a.text


def test_una_talla_vieja_no_se_pega_a_un_peso_nuevo(engine) -> None:
    """El mismo fallo, visto en vivo una segunda vez: con la talla de OTRO mensaje, 7 kg para
    92 cm vuelve a dar «desnutrición aguda grave». Las medidas salen de un solo mensaje."""
    historia = [
        {"role": "user", "text": "mi niño de 3 años pesa 13 kg y mide 92 cm"},
        {"role": "assistant", "text": "Peso para la edad: percentil 20,8."},
    ]
    a = engine.ask(
        "what percentile is my 8 month old girl who weighs 7 kg?", lang="en", history=historia
    )
    assert a.verification == "growth_chart"
    assert "92 cm" not in a.text
    assert a.level == "routine"


def test_las_dos_medidas_del_mismo_mensaje_anterior_si_valen(engine) -> None:
    historia = [
        {"role": "user", "text": "mi niña de 8 meses pesa 7 kg y mide 68 cm"},
        {"role": "assistant", "text": "¿Quieres el percentil?"},
    ]
    a = engine.ask("¿y qué percentil tiene?", lang="es", history=historia)
    assert a.verification == "growth_chart"
    assert "7 kg" in a.text and "68 cm" in a.text
