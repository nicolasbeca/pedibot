"""Respira mal y nadie ha dicho por qué: fuera los pasajes de una enfermedad (22-oct-2026).

Bajo el aviso de dificultad respiratoria grave, el redactor escribe «lo que dicen las fuentes que
se haga mientras llega la ayuda» con los pasajes que tiene delante. Si todos son de una enfermedad
concreta —el crup, el VRS, la bronquiolitis—, copia el consejo de esa enfermedad para un niño del
que nadie ha dicho que la tenga: «aire fresco delante de la nevera abierta» (el Pseudokrupp del
BIÖG) a un niño con tiraje (batería alemana, 20-oct). Es la regla c) del prompt —nunca de otra
situación—, y el revisor con los pasajes se midió peor (5-oct): aquí decide el código.

Si el padre nombra la causa («crup», «asma», «pitos», «bronquiolitis»), es su situación y los
pasajes se quedan. Ver tests/test_severe_breathing_without_a_named_cause.py.
"""

from __future__ import annotations

import re

from pedibot.index.store import Hit

#: las reglas del triaje bajo las que se aplica
REGLAS = frozenset({"severe_breathing"})

#: el tema de los pasajes que son de una enfermedad respiratoria concreta (config/taxonomia.yaml)
TEMA = "respiratorio"

#: el padre nombra la causa, o un signo que la nombra (la tos de perro es el crup, los pitos son
#: el asma o la bronquiolitis), en las ocho lenguas del sitio
CAUSA_NOMBRADA = re.compile(
    r"croup|krupp|\bcrup|laring|laryng|bellend|barking|\bperro|aboie"
    r"|bronchiolit|bronquiolit|\brsv\b|rs-virus|\bvrs\b|respiratory syncytial"
    r"|asthm|\basma|asthme|inhal|salbutamol|ventolin|pumpe|spray"
    r"|pneumon|neumon|lungenentz|wheez|pfeif|giemen|sibil|\bpitos|sifflement|chiado"
    r"|keuchhusten|whooping|tos ferina|coqueluche|pertussis|coqueluche"
    r"|bronchit|bronquit|grippe|influenza|\bgripe|\bflu\b|erk[äa]ltung|\bcold\b|catarro|resfriad|rhume"
    r"|круп|ларингит|бронхиолит|астм|пневмон|бронхит|коклюш|свист"
    r"|الربو|الخانوق|القصيبات|ذات الرئة|الالتهاب الرئوي|السعال الديكي|صفير|بخاخ"
    r"|अस्थमा|दमा|निमोनिया|ब्रोंकाइटिस|काली खांसी|सीटी",
    re.IGNORECASE,
)


#: va al mensaje del redactor cuando se han quitado pasajes: sin ellos no queda ninguno que diga
#: qué hacer mientras llega la ayuda, y el redactor lo rellenaba de su cosecha con la cita de la
#: SEUP («keep your son upright… do not give him anything to eat or drink [1]», 22-oct-2026)
NOTA_SIN_CAUSA = (
    "NOTE: the parent has not said what is causing the breathing difficulty, and no passage below"
    " says what to do while help comes. Write only what the passages say: that these signs need"
    " emergency care now, and any other sign they list that makes it more serious — one or two"
    " sentences. Do NOT add advice on position, eating, drinking or anything else to do: no source"
    " here gives it.\n"
)


def sin_otra_causa(hits: list[Hit], pregunta: str, reglas: set[str] | frozenset[str]) -> list[Hit]:
    """Los pasajes que puede usar el redactor, sin los de una enfermedad que nadie ha nombrado.

    Nunca deja la lista vacía: si sólo había pasajes de enfermedad, se quedan (el aviso de encima
    ya dice lo que hay que hacer, y un «no tengo información» debajo sería peor)."""
    if not (REGLAS & set(reglas)) or CAUSA_NOMBRADA.search(pregunta):
        return hits
    quedan = [h for h in hits if h.chunk.topic != TEMA]
    return quedan or hits
