"""«¿Qué hago?» es una pregunta de salud aunque se la hagan al chat (29-sep-2026).

En la octava tanda del operador, tres preguntas de verdad recibieron la ficha del servicio:

- «estoy en una isla sin pediatra hasta mañana, ¿qué hago?»
- «¿puedes decirme qué hacer si el hospital está a tres horas?»
- «¿cómo distingues "hace ruido" de "le cuesta respirar"?»

La lectura con IA las tomó por preguntas sobre PediBot, y la segunda además le habla al chat
(«¿puedes decirme…?»), que es la señal que se añadió el 22-sep para «¿puede decirme dónde está el
hospital más cercano?». Las dos señales son buenas; lo que faltaba es que pedir qué HACER, o la
diferencia entre dos síntomas, es pedir lo que dicen las guías. Salvo que se nombre al propio
servicio: «¿qué hago si PediBot no me contesta?» sigue siendo sobre PediBot.
"""

from __future__ import annotations

import pytest
from test_the_ai_reads_the_question_first import _json, _motor


@pytest.mark.parametrize(
    "pregunta,intent",
    [
        ("estoy en una isla sin pediatra hasta mañana, ¿qué hago?", "about_pedibot"),
        ("¿puedes decirme qué hacer si el hospital está a tres horas?", "other"),
        ("¿cómo distingues «hace ruido» de «le cuesta respirar»?", "about_pedibot"),
        ("we live three hours from a hospital, what should I do?", "about_pedibot"),
    ],
)
def test_pedir_que_hacer_no_recibe_la_ficha(pregunta, intent) -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish", intent=intent))
    a = motor.ask(pregunta, lang="es")
    assert a.verification != "about", pregunta


@pytest.mark.parametrize(
    "pregunta",
    [
        "¿qué hago si PediBot no me contesta?",
        # medido sobre las 1.053 que recibieron la ficha en las tandas: estas siete la recibieron
        # con razón, y la primera versión de este arreglo se las quitaba
        'puedo decir simplemente "y ahora que hago?" y que sepa de que hablo?',
        "puede distinguir una emergencia de algo que puede esperar?",
        "puede hacerme preguntas antes de decirme que hacer?",
        "¿puedes distinguir una picadura de mosquito de otra cosa en una foto?",
        "¿puedo preguntarte qué hacer con una receta que pone una letra que no entiendo?",
        "¿qué hago si necesito el calendario de un país no disponible?",
        "ich schreibe auf deutsch aber verstehe español, que hacemos?",
    ],
)
def test_lo_que_pregunta_por_el_servicio_sigue_siendo_sobre_el(pregunta) -> None:
    motor, _ = _motor(_json(lang="es", lang_name="Spanish", intent="about_pedibot"))
    a = motor.ask(pregunta, lang="es")
    assert a.verification == "about", pregunta
