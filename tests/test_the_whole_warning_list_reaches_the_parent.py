"""La lista de «cuándo consultar» llega entera (8-oct-2026).

El BIÖG (kindergesundheit-info.de) aceptó un ejemplo de respuesta con una condición: «Die Liste
wann ein Arzt dringend ist bitte aber vollständig übernehmen». Con el prompt v12 («when to get
help: one sentence») se caían de uno a tres motivos de siete en cada tirada; medido sobre la
batería difícil, sólo el 34 % de los motivos que aplicaban llegaban a la respuesta. El v14 pide
todos los que pueden aplicar a este niño (52 %), y prohíbe suavizar además de endurecer.
"""

from __future__ import annotations

import inspect

from pedibot.bot.answer import Engine, load_prompt


def test_production_uses_the_prompt_that_keeps_the_whole_list():
    por_defecto = inspect.signature(Engine.__init__).parameters["prompt_version"].default
    assert por_defecto == "answer_v14"
    assert inspect.signature(load_prompt).parameters["version"].default == "answer_v14"


def test_the_prompt_asks_for_every_reason_and_forbids_softening():
    _, texto = load_prompt("answer_v14")
    # las reglas, sin la cabecera de comentarios (que cita la regla vieja para explicarla)
    texto = texto[texto.index("You are PediBot") :]
    assert "keep EVERY reason that can apply to this child" in texto
    assert "NEVER STRENGTHEN OR SOFTEN WHAT A SOURCE SAYS" in texto
    # el candado del 7-oct sigue: nada de signos de otra enfermedad
    assert "never take warning signs from a passage about another condition" in texto
    assert "when to get help: one sentence" not in texto.lower()
