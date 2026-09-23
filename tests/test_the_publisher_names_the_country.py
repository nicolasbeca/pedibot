"""El candado del país, donde impide en vez de donde avisa (23-sep-2026).

`test_vaccine_guides_name_their_country` existe desde el 7-sep y mira las guías YA publicadas.
Anoche el servidor publicó una novena —«Vacinas atrasadas», en portugués— que daba las edades del
calendario español sin nombrar a España, y el candado saltó aquí, en mi máquina, catorce horas
después de que estuviera viva. Es el mismo error que L227 y que la fuga de idioma: el guardián
que corre después del despliegue sirve para enterarse, no para impedir.

Así que la comprobación se mueve al publicador, que es quien puede no escribir el fichero. Las
tablas de autoridades y de gentilicios viven ahora en producción y el candado viejo las importa
de allí: una sola lista que mantener.
"""

from __future__ import annotations

from pedibot.publish.articles import _problems
from pedibot.publish.paises import AUTORIDAD, NOMBRES, pais_de_las_fuentes

CUERPO = """As vacinas ensinam o corpo a se defender [1].

## O que é

O calendário indica quem deve receber cada vacina [1]. {frase}

## O que você pode fazer em casa

- Leve o seu filho às consultas de rotina [1].

## Quando procurar o médico ou o pronto-socorro

Procure seu médico se notar sinais de alarme [1]:

- Falta de ar [1].

## Perguntas frequentes

**O que é o calendário?** É a lista de vacinas por idade [1].
"""

SIN_PAIS = "A primovacinação contra a doença pneumocócica é feita aos 2 e 4 meses [1]."
CON_PAIS = "No calendário da Espanha, a primovacinação contra a doença pneumocócica é feita aos 2 e 4 meses [1]."

FUENTES = [("Ministerio de Sanidad", "Calendario común de vacunación 2025")] * 4


def test_the_authority_says_which_country() -> None:
    assert pais_de_las_fuentes(FUENTES) == "ES"
    assert pais_de_las_fuentes([("WHO", "Immunization coverage")]) is None
    mezcla = [("Ministerio de Sanidad", "x"), ("RKI", "y")]
    assert pais_de_las_fuentes(mezcla) is None  # sin mayoría clara, no se acusa a nadie


def test_the_publisher_refuses_a_schedule_without_its_country() -> None:
    p = _problems(
        "Vacinas atrasadas",
        CUERPO.format(frase=SIN_PAIS),
        [],
        "pt",
        topic="vacunas_atrasadas",
        fuentes=FUENTES,
    )
    assert any("country_not_named" in x for x in p), p


def test_the_publisher_accepts_it_when_the_country_is_named() -> None:
    p = _problems(
        "Vacinas atrasadas",
        CUERPO.format(frase=CON_PAIS),
        [],
        "pt",
        topic="vacunas_atrasadas",
        fuentes=FUENTES,
    )
    assert not any("country_not_named" in x for x in p), p


def test_a_fever_guide_is_not_asked_for_a_country() -> None:
    """La fiebre vale igual en Hamburgo que en Sevilla; sólo el calendario es de un país."""
    p = _problems(
        "Febre na criança",
        CUERPO.format(frase=SIN_PAIS),
        [],
        "pt",
        topic="fiebre",
        fuentes=FUENTES,
    )
    assert not any("country_not_named" in x for x in p), p


def test_every_country_we_can_blame_can_be_named_in_every_language() -> None:
    """Si sabemos acusar a un país, tenemos que saber decir su nombre en las ocho lenguas."""
    for pais in set(AUTORIDAD.values()):
        formas = NOMBRES.get(pais)
        assert formas, f"{pais} acusa y no tiene nombres"
        for lang in ("en", "es", "fr", "de", "pt", "ru", "ar", "hi"):
            assert formas.get(lang), f"falta cómo se dice «{pais}» en {lang}"
