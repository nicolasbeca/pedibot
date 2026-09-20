"""«¿Cuál es el número de urgencias aquí?», contestado con la tabla (20-sep-2026).

Probando el sitio vivo como un padre en Nigeria: preguntó el número y el chat contestó «no tengo
información fiable sobre esto en mis fuentes», mientras el aviso de arriba llevaba el 112
escrito. Teníamos el dato de 90 países, leído uno a uno de su fuente oficial, y la pregunta más
básica de todas se iba al corpus a buscar un pasaje que no existe.

Las tres cosas que este fichero vigila, por orden de lo que costaría que fallaran:

1. **Que con el niño atragantado NO conteste la tabla.** Si el triaje ha disparado, «¿cuál es el
   número?» no es una consulta de datos: el aviso ya manda llamar y lo que hace falta debajo es
   qué hacer mientras llega la ayuda. Contestar a la letra sería contestar a la pregunta y no a
   lo que está pasando.
2. **Que los siete países sin número lo sigan diciendo.** Ésa es la respuesta allí, y es la que
   más trabajo costó.
3. **Que una frase con síntomas no se lea como esta pregunta**, porque entonces un niño con
   fiebre recibiría una ficha de teléfonos.
"""

from __future__ import annotations

import pytest

from pedibot.bot.emergency_question import (
    country_name,
    format_numbers,
    is_emergency_number_question,
)

PREGUNTAN = [
    "what is the emergency number here?",
    "which emergency number do I call?",
    "what is the emergency number in Morocco",
    "¿cuál es el número de urgencias?",
    "qué número de emergencias hay aquí",
    "quel est le numéro d'urgence ici ?",
    "wie lautet die Notrufnummer?",
    "какой номер скорой помощи здесь?",
    "ما هو رقم الطوارئ في المغرب؟",
    "qual é o número de emergência aqui?",
    "आपातकालीन नंबर क्या है?",
    "namba ya dharura ni ipi?",
]

NO_PREGUNTAN = [
    "mi hijo tiene fiebre desde ayer",
    "llama a urgencias ahora mismo",
    "my child has a rash on his belly",
    "how much paracetamol for 12 kg",
    "¿cuántos ml de dalsy le doy?",
    "el niño no respira bien",
]


@pytest.mark.parametrize("texto", PREGUNTAN)
def test_la_pregunta_se_reconoce(texto: str) -> None:
    assert is_emergency_number_question(texto), f"no se ha reconocido: «{texto}»"


@pytest.mark.parametrize("texto", NO_PREGUNTAN)
def test_lo_que_no_es_esta_pregunta_no_lo_parece(texto: str) -> None:
    """«Llama a urgencias» es una instrucción, no una consulta: la da el aviso, no la tabla."""
    assert not is_emergency_number_question(texto), f"se ha leído como la pregunta: «{texto}»"


def test_un_pais_con_numero_lo_dice_con_su_fuente() -> None:
    datos = {
        "emergency": "112",
        "poison": None,
        "mental": None,
        "source": "Nigeria Federal Ministry of Health",
        "source_url": "https://example.gov.ng/",
    }
    texto = format_numbers(datos, "Nigeria", "en")
    assert "112" in texto
    assert "Nigeria" in texto
    assert "example.gov.ng" in texto


def test_un_pais_sin_numero_nacional_lo_dice_y_no_inventa() -> None:
    """Siete países. Es la respuesta allí, y la que más trabajo costó de todo el catálogo."""
    texto = format_numbers({"emergency": None, "no_national": True}, "Liberia", "es")
    assert "no hay número nacional" in texto.lower()
    assert not any(ch.isdigit() for ch in texto), f"ha aparecido una cifra: «{texto}»"


def test_un_pais_sin_verificar_dice_que_no_lo_ha_podido_verificar() -> None:
    texto = format_numbers({"emergency": None, "unverified": True}, "Zambia", "es")
    assert "verificar" in texto.lower()


def test_el_aviso_de_la_fuente_sobre_sudan_viaja_con_el_numero() -> None:
    """El 999 sudanés viene con la advertencia de que a menudo no contesta. Callarla sería dar
    por buena una llamada que puede no responder nadie."""
    datos = {
        "emergency": "999",
        "note": "The source warns that emergency services in Sudan are often unresponsive.",
        "source": "UK FCDO",
    }
    texto = format_numbers(datos, "Sudán", "es")
    assert "unresponsive" in texto


@pytest.mark.parametrize(
    ("cc", "lang", "esperado"), [("MA", "es", "Marruecos"), ("KE", "ru", "Кения")]
)
def test_el_pais_se_nombra_en_el_idioma_del_lector(cc: str, lang: str, esperado: str) -> None:
    assert country_name(cc, lang) == esperado


def test_un_pais_desconocido_sale_como_su_codigo() -> None:
    """Feo y honesto. Fabricar un nombre no es una opción."""
    assert country_name("ZZ", "es") == "ZZ"


# ── el motor entero, que es donde de verdad se decide ────────────────────────────────────────


@pytest.fixture
def motor(tmp_path):
    """Un motor mínimo con las tablas de verdad: tres pasajes y los 90 números."""
    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.llm import FakeProvider
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.bot.triage import Triage
    from pedibot.index.store import Index, build_index
    from pedibot.ingest.classify import Taxonomy
    from pedibot.ingest.schema import Chunk
    from pedibot.settings import ROOT

    def trozo(cid, texto, red=False):
        return Chunk(
            chunk_id=cid,
            doc_id=cid.split("#")[0],
            org="SEUP",
            doc_title="Fiebre. Información para padres",
            year=None,
            lang="es",
            section="¿Qué hacer?",
            pages=[1],
            text=texto,
            topic="fiebre",
            doc_type="hoja_padres",
            evidence="sociedad_cientifica",
            usage="publico",
            is_red_flag=red,
            is_dose_table=False,
            is_dose_source=False,
            source_url="https://seup.org/x.pdf",
            source_hash="h",
            n_words=len(texto.split()),
        )

    db = tmp_path / "i.db"
    build_index(
        [
            trozo("seup_fiebre#q#1", "La fiebre no es peligrosa por sí misma, según la SEUP."),
            trozo(
                "seup_atragantamiento#q#1", "Ante un atragantamiento, dé cinco golpes.", red=True
            ),
        ],
        db,
    )
    cfg = ROOT / "config"

    def hacer(responde):
        llm = FakeProvider(responde)
        return (
            Engine(
                Retriever(
                    Index(db),
                    Synonyms(cfg / "synonyms.yaml"),
                    llm=None,
                    taxonomy=Taxonomy(cfg / "taxonomia.yaml"),
                ),
                Triage(cfg / "red_flags.yaml"),
                llm,
                EmergencyNumbers(cfg / "emergency_numbers.yaml"),
            ),
            llm,
        )

    return hacer


def test_la_tabla_contesta_cuando_no_hay_urgencia(motor) -> None:
    """La pregunta tranquila la contesta la tabla, sin pasar por el modelo."""
    engine, llm = motor(lambda *a, **k: "esto no debería llamarse nunca")
    r = engine.ask("what is the emergency number here?", country="NG", lang="en")
    assert "112" in r.text
    assert "Nigeria" in r.text
    assert r.tool is not None and r.tool.kind == "emergency"
    assert r.verification == "emergency_number"


def test_con_el_nino_atragantado_NO_contesta_la_tabla(motor) -> None:
    """La misma pregunta, con el niño atragantándose, no es una consulta de datos.

    El aviso ya manda llamar y lo que hace falta debajo es qué hacer mientras llega la ayuda.
    Leer la ficha de teléfonos ahí sería contestar a la letra de la pregunta y no a lo que está
    pasando, y es el único caso de esta herramienta en el que eso costaría algo.
    """
    engine, _ = motor(lambda *a, **k: "TEXT: Ponle de lado [1].")
    r = engine.ask(
        "what is the emergency number, my child is choking and can't breathe",
        country="NG",
        lang="en",
    )
    assert r.level != "routine", "el triaje tiene que haber disparado con esto"
    assert r.verification != "emergency_number", "con una alarma activa manda el aviso, no la tabla"


def test_sin_pais_no_se_adivina(motor) -> None:
    """Ni inferido del idioma ni por la primera opción de una lista: se cae al corpus."""
    engine, _ = motor(lambda *a, **k: "TEXT: No tengo fuentes para esto.")
    r = engine.ask("what is the emergency number here?", country=None, lang="en")
    assert r.verification != "emergency_number"


def test_la_tabla_de_nombres_cubre_todos_los_paises() -> None:
    """`config/country_names.json` lo genera Node con `Intl` y puede quedarse atrás.

    Si alguien añade un país y no la regenera, el chat diría «En LY el número es el 1415», que
    se entiende y canta. Esto lo convierte en un fallo aquí, que es donde tiene que doler.
    Se regenera con `node scripts/export-country-names.mjs` desde `web/site`, y el despliegue
    lo hace solo.
    """
    import json

    import yaml

    from pedibot.settings import ROOT

    nombres = json.loads((ROOT / "config" / "country_names.json").read_text(encoding="utf-8"))
    emergencias = yaml.safe_load(
        (ROOT / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8")
    )
    vacunas = yaml.safe_load((ROOT / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    codigos = {k for k in emergencias if k != "default"} | set(vacunas["countries"])

    for lang in ("en", "es", "fr", "de", "ru", "ar", "pt", "hi", "sw"):
        assert lang in nombres, f"falta la lengua {lang} en country_names.json"
        faltan = sorted(codigos - set(nombres[lang]))
        assert not faltan, (
            f"{lang}: sin nombre para {faltan}. Regenera con "
            "`node scripts/export-country-names.mjs` desde web/site."
        )
