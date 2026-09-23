"""«El calendario de vacunas chileno» devolvió el español (23-sep-2026).

Del registro del día anterior, una consulta real desde España:

    «cual es el calendario de vacunas chileno para los 18 meses»

y la respuesta fue la tabla del Ministerio de Sanidad **de España**, con su fuente y su aire de
exactitud. Dos cosas fallaron a la vez:

1. el país del selector pisaba al que el padre había escrito, cuando escribirlo es lo más
   explícito que se puede hacer;
2. Chile no está entre los 66 calendarios transcritos —no lo tenemos— y en vez de decirlo se
   sirvió el de al lado.

Dar el calendario de otro país es peor que no dar ninguno: las edades y las vacunas cambian, y
el padre se va creyendo que ya lo sabe.
"""

from __future__ import annotations

from test_the_ai_reads_the_question_first import _json, _motor

from pedibot.bot.vaccines import Vaccines, country_in_question
from pedibot.settings import ROOT


def _con_calendarios():  # noqa: ANN202 — el motor de juguete no los trae, y aquí son el asunto
    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    motor.vaccines = Vaccines(ROOT / "config" / "vaccines.yaml")
    return motor


def test_the_country_written_in_the_question_is_recognised() -> None:
    assert country_in_question("el calendario de vacunas de Chile") == "CL"
    assert country_in_question("cual es el calendario de vacunas chileno") == "CL"
    assert country_in_question("el calendario mexicano de vacunas") == "MX"


def test_a_country_we_do_not_have_is_not_answered_with_another_one() -> None:
    a = _con_calendarios().ask(
        "cual es el calendario de vacunas chileno para los 18 meses", lang="es", country="ES"
    )
    assert a.verification != "vaccine_schedule", a.text
    assert "Ministerio de Sanidad" not in a.text


def test_the_country_written_beats_the_one_picked() -> None:
    """Con Francia escrita y España elegida, manda Francia."""
    a = _con_calendarios().ask(
        "qué vacunas tocan en Francia a los 3 meses", lang="es", country="ES"
    )
    assert a.verification == "vaccine_schedule"
    assert "Fran" in a.text or "France" in a.text
