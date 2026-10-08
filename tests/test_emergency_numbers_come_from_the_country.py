"""Los números de urgencias, cotejados con la autoridad del propio país (8-oct-2026).

Senegal daba el 15 (el SAMU de Francia) porque la guía de viajes británica (FCDO) lo decía; el
Ministerio de Salud de Senegal dice 1515 (L262). Cotejados después los sospechosos, sobre todo
África francófona; cambian sólo los que una fuente oficial del país confirma. Los dudosos sin
fuente oficial (Camerún, Madagascar, Togo, Chad, Bolivia, Mozambique, Etiopía) se quedan como
estaban y están anotados en STATE.md: cambiar un número de urgencias sin estar seguro es peor.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import EmergencyNumbers


@pytest.fixture(scope="module")
def numeros(config_dir) -> EmergencyNumbers:
    return EmergencyNumbers(config_dir / "emergency_numbers.yaml")


@pytest.mark.parametrize(
    "pais,empieza,fuente",
    [
        ("SN", "1515", "sante.gouv.sn"),  # Ministerio de Salud: «SAMU Composer le 1515»
        ("RW", "912", "ughe.org"),  # SAMU del Ministerio de Salud, número nacional gratuito
        ("BJ", "112", "beninwebtv.bj"),  # ARCEP, plan de números cortos (jun-2026): 112 SAMU-BENIN
        ("BF", "15", "sidwaya.info"),  # SAMU nacional, número corto y gratuito
        ("MA", "141", "lematin.ma"),  # «Allô SAMU 141», Ministerio de Salud
        ("ZW", "999", "zim.gov.zw"),  # portal del Gobierno: «All emergencies, 999»
    ],
)
def test_the_number_is_the_one_the_country_gives(numeros, pais, empieza, fuente):
    n = numeros.get(pais, "en")
    assert n["emergency"].startswith(empieza), (pais, n["emergency"])
    assert fuente in (n.get("source_url") or ""), (pais, n.get("source_url"))
