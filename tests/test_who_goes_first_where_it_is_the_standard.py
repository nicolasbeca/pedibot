"""El zinc: en Kenia la guía de la OMS tiene que estar delante (20-sep-2026).

Salió probando la web viva como un padre de Nairobi, no leyendo código, que es la séptima vez
que ese método encuentra algo y el código no. La pregunta fue «my baby is 7 months and has
watery diarrhoea since yesterday», con Kenia seleccionada, y la respuesta —correcta, segura y
con fuentes— hablaba de suero de rehidratación y de cuándo ir al médico, citando a MedlinePlus
y a la SEUP. **No mencionaba el zinc.**

Y en Kenia, en Nigeria, en Etiopía y en la India el zinc no es un detalle: la OMS lo recomienda
de 10 a 14 días, acorta el episodio alrededor de un 25 % y reduce el volumen de heces alrededor
de un 30 %, y es política nacional en esos países.

**Lo que se comprobó antes de tocar nada, porque cambia el diagnóstico:**

- el documento de la OMS **ya estaba en el corpus**, en varios idiomas, con su ficha y su cita;
- y **sí salía** cuando la pregunta era de tratamiento («should I give my child zinc», «what
  treatment»). Contestaba con la OMS delante y con las dos cifras.

O sea que no faltaba información y no había que añadir fuentes. Lo que pasaba es que **cuando el
padre describe un síntoma en vez de pedir un remedio**, ganan las fuentes europeas, que no
hablan de zinc porque en Europa no se usa así. Un padre asustado describe un síntoma.

El arreglo es empujar los términos de la OMS en la recuperación cuando la pregunta es de diarrea
**y el país es uno donde esa guía es la norma**. No inventa nada ni escribe nada en la respuesta:
mete el documento que allí es la norma entre los pasajes que el modelo tiene delante.

**Y de dónde sale «donde esa guía es la norma», que es la parte que casi hago mal.** Iba a
escribir «los africanos y los del sur de Asia», que suena razonable, y es justo lo que no se hizo
con las marcas de Etiopía y del Congo: plausible no es una fuente. La fuente estaba dentro del
propio documento de la OMS, que acota él mismo su alcance a «low-income countries», y esa frase
se traduce a códigos de país con la clasificación del Banco Mundial, que es pública, anual y
descargable (`scripts/build_income_levels.py`).

Lo que este candado NO permite, y es la otra mitad: que el zinc aparezca con una dosis. La dosis
depende de la edad —distinta por encima y por debajo de los seis meses— y eso va por la vía de
las dosis, con su tabla y su fuente, o no va.
"""

from __future__ import annotations

import pytest

from pedibot.bot.who_first import (
    LOW_INCOME,
    WHO_DIARRHOEA_TERMS,
    extra_terms,
    is_a_diarrhoea_question,
)


@pytest.mark.parametrize(
    "texto",
    [
        "my baby is 7 months and has watery diarrhoea since yesterday",
        "mi hijo tiene diarrea desde ayer",
        "mon enfant a la diarrhée depuis hier",
        "mein Kind hat seit gestern Durchfall",
        "у моего ребёнка понос со вчерашнего дня",
        "ابني عنده إسهال من أمس",
        "मेरे बच्चे को कल से दस्त हैं",
        "o meu filho tem diarreia desde ontem",
        "he has loose stools and is not drinking",
        "lleva toda la noche con deposiciones líquidas",
    ],
)
def test_reconoce_una_pregunta_de_diarrea_en_las_ocho_lenguas(texto: str) -> None:
    assert is_a_diarrhoea_question(texto), texto


@pytest.mark.parametrize(
    "texto",
    [
        "mi hijo está estreñido y lleva cuatro días sin hacer caca",
        "my child has a fever of 39 and a rash",
        "le duele el oído desde anoche",
        "mein Kind hustet seit drei Tagen",
        "tiene lombrices, ¿qué le doy?",
    ],
)
def test_no_confunde_otras_cosas_del_aparato_digestivo(texto: str) -> None:
    """«digestivo» de la taxonomía incluye estreñimiento y lombrices, y ahí el zinc no pinta."""
    assert not is_a_diarrhoea_question(texto), texto


def test_en_kenia_se_empujan_los_terminos_de_la_oms() -> None:
    t = extra_terms("my baby has watery diarrhoea since yesterday", "KE")
    assert t, "Kenia es de renta baja: la guía de la OMS es la norma allí"
    assert "zinc" in t


@pytest.mark.parametrize("pais", ["KE", "NG", "ET", "IN", "EG", "PK", "TZ", "MA"])
def test_los_mercados_a_los_que_vamos_estan_dentro(pais: str) -> None:
    assert pais in LOW_INCOME
    assert extra_terms("mi hijo tiene diarrea", pais)


@pytest.mark.parametrize("pais", ["ES", "GB", "DE", "US", "FR", "PT", "RU"])
def test_en_europa_y_estados_unidos_no_se_toca_nada(pais: str) -> None:
    """Allí el zinc no es práctica habitual, y eso es criterio clínico, no mío."""
    assert pais not in LOW_INCOME
    assert extra_terms("mi hijo tiene diarrea", pais) == []


def test_sin_pais_no_se_supone_nada() -> None:
    """Quien no ha elegido país no es «probablemente de renta baja»; es desconocido."""
    assert extra_terms("mi hijo tiene diarrea", None) == []
    assert extra_terms("mi hijo tiene diarrea", "") == []


def test_una_pregunta_que_no_es_de_diarrea_no_empuja_nada_ni_en_kenia() -> None:
    assert extra_terms("my child has a fever of 39", "KE") == []
    assert extra_terms("mi hijo está estreñido", "NG") == []


def test_los_terminos_no_llevan_ninguna_dosis() -> None:
    """La dosis de zinc depende de la edad y va por la vía de las dosis, con su fuente, o no va."""
    import re

    for t in WHO_DIARRHOEA_TERMS:
        assert not re.search(r"\d", t), f"«{t}» lleva una cifra y no debería"


def test_la_lista_de_paises_dice_de_donde_sale() -> None:
    """Una lista de 72 países sin procedencia es una opinión con formato de dato."""
    import json

    from pedibot.settings import ROOT

    d = json.loads((ROOT / "config" / "income_levels.json").read_text(encoding="utf-8"))
    assert "World Bank" in d["fuente"]
    assert d["fuente_url"].startswith("https://")
    assert d["descargado"]
    assert d["categorias"] == ["LIC", "LMC"]
    assert len(d["low_and_lower_middle_income"]) == len(LOW_INCOME) >= 50


def test_el_motor_pasa_los_terminos_al_recuperador_y_solo_donde_toca() -> None:
    """La política se prueba arriba; esto prueba el cable, que es donde se rompen estas cosas.

    Una regla correcta que nadie llama no arregla nada, y desde fuera las dos cosas se ven igual.
    """
    from pedibot.bot.answer import EmergencyNumbers, Engine
    from pedibot.bot.drugs import DrugCatalog
    from pedibot.bot.triage import Triage
    from pedibot.ingest.classify import Taxonomy
    from pedibot.settings import ROOT

    CONFIG = ROOT / "config"
    vistos: list[list[str]] = []

    class RecuerdaElPush:
        """Un recuperador que no recupera: sólo apunta con qué términos le llamaron."""

        thin_langs: frozenset[str] = frozenset()
        taxonomy = Taxonomy(CONFIG / "taxonomia.yaml")

        def expand(self, query, lang):  # noqa: ANN001, ANN202
            return []

        def search(self, query, lang, red_flag_boost=False, push=None):  # noqa: ANN001, ANN202
            vistos.append(list(push or []))
            return [], []

    motor = Engine(
        RecuerdaElPush(),  # type: ignore[arg-type]
        Triage(CONFIG / "red_flags.yaml"),
        None,
        EmergencyNumbers(CONFIG / "emergency_numbers.yaml"),
        drugs=DrugCatalog(CONFIG / "drugs.yaml"),
    )

    motor.ask("mi hijo de 2 años tiene diarrea desde ayer", country="KE", lang="es")
    assert vistos and "zinc" in vistos[-1], "en Kenia la OMS tiene que competir por entrar"

    motor.ask("mi hijo de 2 años tiene diarrea desde ayer", country="ES", lang="es")
    assert vistos[-1] == [], "en España no se toca: allí el zinc no es práctica habitual"

    motor.ask("mi hijo de 2 años tiene tos desde ayer", country="KE", lang="es")
    assert vistos[-1] == [], "la tos no lleva términos de diarrea ni en Kenia"


def test_lo_que_la_pregunta_anterior_dijo_tambien_cuenta() -> None:
    """«¿y cuánto le doy?» después de «tiene diarrea» sigue siendo una pregunta de diarrea.

    Se mira el contexto y no sólo la última frase, que es como habla un padre en un chat.
    """
    assert is_a_diarrhoea_question("mi hijo tiene diarrea ¿y qué le doy de comer?")
    assert extra_terms("tiene diarrea desde ayer y ahora vomita", "NG")
