"""Palpitaciones con dolor de pecho, falta de aire o mareo (9-oct-2026).

Pendiente desde el 5-oct: «my 12 year old says his heart races and he gets dizzy when running» y
«mein Sohn hat beim Sport Brustschmerzen» salían rutina. La hoja del NHS sobre palpitaciones:
«Call 999 or go to A&E if you currently have heart palpitations and … chest pain, shortness of
breath, feeling faint or fainting. If you've had these symptoms but they've now stopped, ask your
GP surgery for an urgent appointment, call 111». Un padre escribe casi siempre cuando ya ha pasado,
así que el nivel es «que lo vean hoy». El dolor de pecho solo no entra: la hoja del NHS de dolor de
pecho dice que, tras ejercicio y mejorando con reposo, suele ser muscular.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage


@pytest.fixture(scope="module")
def triaje() -> Triage:
    from pedibot.eval import fake_engine_from_settings

    return fake_engine_from_settings().triage


SALTA = [
    "my 12 year old says his heart races and he gets dizzy when running",
    "my daughter had palpitations and felt like she was going to faint",
    "her heart was pounding and she was short of breath",
    "mi hijo dice que el corazón le va a mil y le cuesta respirar",
]

NO_SALTA = [
    "my heart races when I drink coffee, can my kid have caffeine",
    "is it normal for a child's heart to beat faster after running",
    "my son has chest pain after doing push ups at the gym",
    "mi hija tiene palpitaciones cuando está nerviosa por los exámenes",
]


@pytest.mark.parametrize("texto", SALTA)
def test_it_fires(triaje: Triage, texto: str) -> None:
    r = triaje.assess(texto)
    assert "palpitations_with_red_signs" in [m.id for m in r.matched], texto
    # «le cuesta respirar» trae además su propia regla, más grave: manda la más alta
    assert r.level in ("urgent", "emergency")


@pytest.mark.parametrize("texto", NO_SALTA)
def test_it_does_not(triaje: Triage, texto: str) -> None:
    assert "palpitations_with_red_signs" not in [m.id for m in triaje.assess(texto).matched], texto
