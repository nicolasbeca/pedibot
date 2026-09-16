"""Ocho frases de alarma que el triaje veía como rutina (16-sep-2026).

Salieron solas: al regenerar 118 guías con fuentes que su lector puede abrir, las guías pasaron a
advertir con las palabras del NHS y de la OMS en vez de con las del SEUP, y `test_guides_agree_
with_triage` empezó a señalar frases que el triaje no reconocía. Son huecos de verdad, no ruido
de la traducción: cada una es una frase que una guía nuestra pone como motivo para ir a urgencias.

    [en] there are pauses when your child breathes        → apnea, y sólo estaba en castellano
    [fr] il y a des pauses dans sa respiration            → estaba «pauses respiratoires», no ésta
    [fr] beaucoup de mal à respirer                       → estaba «du mal à respirer»
    [ru] нехватка дыхания / поверхностное дыхание         → no estaban
    [ar] مشاكل تنفس خطيرة / تحول الشفاه                    → estaba el sustantivo, no «problemas»
    [ar] تأخر في استعادة الوعي أكثر من 3 دقائق              → no estaba
    [ar] نعسان جدا بعد استعادة الوعي                       → el somnoliento sólo en otras lenguas
    [en] swallowed, touched or breathed in something harmful → el tóxico tenía que ir nombrado

Un triaje que no reconoce la frase con la que nuestra propia guía avisa es peor que uno corto:
el padre lee el aviso en la guía y no lo recibe en el chat.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


CASOS = [
    ("en", "there are pauses when your child breathes", "emergency"),
    ("en", "my baby has pauses in his breathing", "emergency"),
    ("fr", "il y a des pauses dans sa respiration", "emergency"),
    ("fr", "mon enfant a beaucoup de mal à respirer", "emergency"),
    ("ru", "у ребёнка сильная нехватка дыхания", "emergency"),
    ("ru", "частое поверхностное дыхание у ребёнка", "emergency"),
    ("ar", "طفلي عنده مشاكل تنفس خطيرة", "emergency"),
    ("ar", "تحول لون شفاه طفلي إلى الأزرق", "emergency"),
]

#: Éstas no son urgencia inmediata pero tampoco rutina: hay que verlas hoy.
CASOS_URGENTES = [
    ("ar", "تأخر طفلي في استعادة الوعي أكثر من 3 دقائق"),
    ("ar", "طفلي نعسان جدا بعد استعادة الوعي"),
    ("en", "my child may have swallowed, touched or breathed in something harmful"),
]


@pytest.mark.parametrize(("lang", "frase", "nivel"), CASOS)
def test_la_frase_de_alarma_se_reconoce(triaje: Triage, lang: str, frase: str, nivel: str) -> None:
    r = triaje.assess(frase)
    assert r.level == nivel, f"[{lang}] «{frase}» → {r.level} ({[x.id for x in r.matched]})"


@pytest.mark.parametrize(("lang", "frase"), CASOS_URGENTES)
def test_y_estas_no_son_rutina(triaje: Triage, lang: str, frase: str) -> None:
    r = triaje.assess(frase)
    assert r.level in ("urgent", "emergency"), f"[{lang}] «{frase}» → {r.level}"


def test_y_lo_corriente_sigue_siendo_corriente(triaje: Triage) -> None:
    """La mitad que hace segura a la otra: un patrón nuevo que salte de más satura el aviso."""
    for frase in (
        "mi hijo respira bien pero tiene mocos",
        "my child breathes normally and is playing",
        "mon enfant respire bien",
        "طفلي يتنفس بشكل طبيعي",
        "ребёнок дышит нормально",
    ):
        assert triaje.assess(frase).level == "routine", frase
