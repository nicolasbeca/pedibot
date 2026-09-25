"""Preguntar por una reacción a una vacuna puesta en Francia no es pedir el calendario francés.

De la octava tanda (23-sep-2026):

    «mi hijo tiene una reacción después de una vacuna que recibió en Francia»
    → «Francia — calendario vacunal 2026: • 2 meses: Hexavalent DTC…»

Es efecto de lo que arreglé ayer: el país escrito en la pregunta pasó a mandar sobre el
seleccionado, y con eso cualquier pregunta de vacunas que nombre un país saca su tabla. El país
escrito sigue mandando — pero sólo cuando lo que se pide ES un calendario.

Y el calendario se escribe en la lengua del padre, no en la del país: «I selected Spain but I
need the vaccination calendar for France» devolvía «France — calendrier vaccinal».
"""

from __future__ import annotations

import re

from test_the_ai_reads_the_question_first import _json, _motor

from pedibot.bot.vaccines import Vaccines
from pedibot.settings import ROOT


def _motor_con_calendarios():  # noqa: ANN202
    motor, _ = _motor(_json(lang="es", lang_name="Spanish"))
    motor.vaccines = Vaccines(ROOT / "config" / "vaccines.yaml")
    return motor


def test_a_reaction_is_not_a_schedule() -> None:
    a = _motor_con_calendarios().ask(
        "mi hijo tiene una reacción después de una vacuna que recibió en Francia",
        lang="es",
        country="ES",
    )
    assert a.verification != "vaccine_schedule", a.text


def test_asking_for_the_schedule_still_gives_it() -> None:
    for q in (
        "qué vacunas tocan en Francia a los 3 meses",
        "calendario de vacunas de Francia",
        "quiero el calendario vacunal francés",
    ):
        a = _motor_con_calendarios().ask(q, lang="es", country="ES")
        assert a.verification == "vaccine_schedule", q


def test_the_schedule_is_written_in_the_parents_language() -> None:
    """Lo que el padre lee —las edades— va en su lengua, no en la del país.

    El título («France — calendrier vaccinal 2026») y los nombres de los productos se dejan como
    los publica el ministerio francés: son el nombre del documento y de las vacunas tal y como
    aparecen en la cartilla, y traducirlos a mano sería inventarle etiquetas que allí no están.
    """
    a = _motor_con_calendarios().ask(
        "quiero el calendario de vacunas de Francia", lang="es", country="ES"
    )
    assert a.verification == "vaccine_schedule"
    edades = [x for x in a.text.split("\n") if x.startswith("• ")]
    assert edades, a.text
    for linea in edades:
        edad = linea.split(":", 1)[0]
        assert re.search(r"meses|mes\b|años|año\b|semanas|nacimiento", edad), edad
        assert "mois" not in edad and "ans" not in edad, edad


def test_the_ages_are_said_differently_in_every_language() -> None:
    """La guardia nueva midió en castellano y dejó fuera media Europa (23-sep-2026).

    «¿Qué vacunas le tocan a los 2 meses?» pide el calendario, y por eso el patrón buscaba «a
    los N». Pero un padre francés escribe «pour un bébé de 3 mois», uno alemán «mit 2 Monaten» y
    uno brasileño «aos 4 meses», y los tres se quedaron fuera: tres casos del conjunto dorado que
    llevaban meses en verde. Una regla escrita en una lengua y medida en una lengua no está
    medida.
    """
    from pedibot.bot.vaccines import pide_calendario

    for q in (
        "Quels vaccins pour un bébé de 3 mois en France ?",
        "Welche Impfungen mit 2 Monaten in Deutschland?",
        "Quais vacinas aos 4 meses no Brasil?",
        "¿Qué vacunas le tocan a los 2 meses?",
        "which vaccines at 6 months in Ireland?",
        "quelles vaccinations à 12 mois ?",
    ):
        assert pide_calendario(q), q

    # y lo que NO es pedir el calendario sigue sin serlo
    for q in (
        "mi hijo tiene una reacción después de una vacuna que recibió en Francia",
        "mon enfant a de la fièvre après le vaccin",
        "mein Kind hat eine Schwellung nach der Impfung",
    ):
        assert not pide_calendario(q), q


def test_the_selected_country_does_not_serve_the_calendar_either() -> None:
    """25-sep-2026. El 23 se arregló a medias y hoy se vio en vivo.

    Aquel día: «una reacción a una vacuna que recibió en Francia» devolvía el calendario
    francés, y se corrigió que **el país escrito** sólo mande cuando lo que se pide ES un
    calendario. Pero la puerta de entrada seguía siendo «la pregunta menciona una vacuna», así
    que con el país puesto en el selector —lo normal— cualquier duda sobre una vacuna concreta
    seguía devolviendo la tabla entera:

        «mi hijo vomitó después de la vacuna del rotavirus, ¿hay que repetirla?»
        → «España — calendario común 2026: • Al nacer: Hepatitis B…»

    Un padre con el niño vomitando recibía 23 líneas de tabla y ninguna respuesta.
    """
    motor = _motor_con_calendarios()
    for q in (
        "mi hijo vomitó después de la vacuna del rotavirus, ¿hay que repetirla?",
        "le ha salido un bulto donde le pusieron la vacuna",
        "tiene fiebre desde la vacuna de ayer",
    ):
        a = motor.ask(q, lang="es", country="ES")
        assert a.verification != "vaccine_schedule", f"{q} → {a.text[:80]}"


def test_and_asking_for_it_with_the_selector_still_works() -> None:
    """Y lo que sí es pedir el calendario sigue dándolo, con el país del selector."""
    motor = _motor_con_calendarios()
    for q in (
        "qué vacunas le tocan a los 4 meses",
        "el calendario de vacunas",
        "calendario vacunal",
    ):
        a = motor.ask(q, lang="es", country="ES")
        assert a.verification == "vaccine_schedule", q
