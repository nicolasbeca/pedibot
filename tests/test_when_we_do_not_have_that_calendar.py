"""«No tengo información fiable» a quien pide el calendario de su país (23-sep-2026).

Arreglado el fallo de servirle el de España a quien pedía el de Chile, la respuesta pasó a ser
la genérica de no-tengo-fuente. Es honesta y es peor de lo que puede ser: el padre no sabe si
falla su pregunta, su país o el sitio entero. Y hay muchos países así — toda América Latina
menos Brasil — así que esa frase la va a leer mucha gente.

Se le dice qué falta, con el nombre de su país, y dónde están los que sí hay.
"""

from __future__ import annotations

from test_the_ai_reads_the_question_first import _json, _motor

from pedibot.bot.vaccines import Vaccines
from pedibot.settings import ROOT


def _motor_con_calendarios():  # noqa: ANN202
    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    motor.vaccines = Vaccines(ROOT / "config" / "vaccines.yaml")
    return motor


def test_it_says_which_country_it_is_missing() -> None:
    a = _motor_con_calendarios().ask(
        "cual es el calendario de vacunas chileno para los 18 meses", lang="es", country="ES"
    )
    assert a.verification == "no_schedule"
    assert "Chile" in a.text
    assert "vaccines" in (a.tool.url if a.tool else "")


def test_the_ones_we_do_have_still_answer() -> None:
    a = _motor_con_calendarios().ask("vacunas en Francia a los 3 meses", lang="es", country="ES")
    assert a.verification == "vaccine_schedule"
