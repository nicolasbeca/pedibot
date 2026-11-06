"""Un objeto tragado no es una intoxicación: fuera las hojas de tóxicos (6-nov-2026).

Bajo el aviso de objeto tragado, el redactor escribe «lo que dicen las fuentes que se haga» con los
pasajes que tiene delante, y la búsqueda trae la hoja de intoxicaciones de la SEUP porque se habla
de tragar. Así salía «do not give water, milk, oil», «try to work out how much was swallowed» y
«separate the child from whatever is left of the object» para una moneda (pruebas 1195 y 1198).
Es consejo de otra situación, la regla c) del prompt; como en bot/breathing_cause.py, lo decide el
código. Si también ha saltado la regla `poisoning`, hay un tóxico de verdad y la hoja se queda.

Ver tests/test_swallowed_object_is_not_poisoning.py.
"""

from __future__ import annotations

from pedibot.index.store import Hit

#: las reglas del triaje bajo las que se aplica
REGLAS = frozenset({"foreign_body_ingestion", "button_battery"})

#: si salta esta, la hoja de tóxicos es la situación del padre
TOXICO = "poisoning"

#: el tema de los pasajes de intoxicaciones (config/taxonomia.yaml)
TEMA = "intoxicacion"

#: sin la hoja no queda ningún pasaje que diga qué hacer de camino, y el redactor lo rellenaría de
#: su cosecha; y los de Ecimed hablan de vigilar en casa después de que un médico lo haya visto
NOTA_OBJETO = (
    "NOTE: the child swallowed an object, not a poison, and no passage below says what to do on"
    " the way. Write only what the passages say: that this needs to be seen as the warning above"
    " says, and any sign they list that makes it more serious. Do NOT add advice about food,"
    " drink, vomiting or how much was swallowed. Do NOT tell the parent to watch at home or check"
    " the stools: that is for after a doctor has seen the child.\n"
)


def sin_hoja_de_toxicos(hits: list[Hit], reglas: set[str] | frozenset[str]) -> list[Hit]:
    """Los pasajes que puede usar el redactor, sin los de intoxicaciones si lo tragado es un objeto.

    Nunca deja la lista vacía: el aviso de encima ya dice qué hacer, y un «no tengo información»
    debajo sería peor."""
    if not (REGLAS & set(reglas)) or TOXICO in reglas:
        return hits
    quedan = [h for h in hits if h.chunk.topic != TEMA]
    return quedan or hits
