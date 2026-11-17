"""Un remedio casero que ninguna guía nombra: ni sí ni no (17-nov-2026).

«Should I put oil or ghee on my newborn baby umbilical cord?» (gancho del 12-nov, India) abría con
«No, do not put oil or ghee on the cord», y ninguno de los pasajes —la AEP con la clorhexidina,
el BIÖG con el agua hervida— habla del aceite ni del ghee. El redactor dedujo un «no» de lo que sí
recomiendan. Puede ser la respuesta buena, pero no es lo que dicen las fuentes, y PediBot sólo
dice lo que dicen las fuentes.

Si el padre pregunta por poner algo de esta lista y ningún pasaje lo nombra, el redactor recibe
una nota: decir que las guías que tiene no hablan de eso, y luego lo que sí dicen. Si algún pasaje
lo nombra, no hay nota: esa guía contesta. Ver tests/test_home_remedy_not_in_the_guides.py.
"""

from __future__ import annotations

import re

from pedibot.index.store import Hit

#: el remedio, en las lenguas en que pregunta el padre y en las de los pasajes (en, es, de, fr, pt)
REMEDIOS: dict[str, re.Pattern[str]] = {
    "oil": re.compile(
        r"\boils?\b|\baceite|\b[öo]l\b|\b[öo]le\b|\bhuile|\b[óo]leo|\bazeite|масл|زيت|तेल|\bmafuta",
        re.I,
    ),
    "ghee": re.compile(r"\bghee|\bghi\b|घी|سمن", re.I),
    "butter": re.compile(r"\bbutter|mantequilla|\bbeurre|manteiga|сливочн", re.I),
    "turmeric": re.compile(r"turmeric|c[úu]rcuma|kurkuma|curcuma|हल्दी|كركم", re.I),
    "toothpaste": re.compile(r"toothpaste|pasta de dientes|dentifric|zahnpasta|pasta de dente", re.I),
    "cow dung": re.compile(r"cow ?dung|esti[ée]rcol|bouse|गोबर", re.I),
    "ash": re.compile(r"\bash(es)?\b|\bceniza|\bcendre|\basche\b|\bcinza|राख", re.I),
    "talc": re.compile(r"\btalc|polvos de talco|\btalco|puder\b|पाउडर", re.I),
    "breast milk on it": re.compile(r"breast ?milk on|leche materna en el|lait maternel sur", re.I),
}

#: el padre pregunta por PONER algo: en la piel, el ombligo, una herida, una quemadura…
PONER = re.compile(
    r"\bput|\bapply|\brub|\bsmear|\buse\b|\bpon(?:er|go|e|es|emos|le|erle)?\b|p[óo]ng|untar|unto"
    r"|echar|echo|aplic|mettre|mets|appliqu"
    r"|auftragen|eincremen|\bdrauf|passar|colocar|намаз|нанес|ضع|أضع|دهن|लगा|लगाएं|kupaka|kuweka",
    re.I,
)

NOTA = (
    "NOTE: the parent asks about putting {cosa} on it. No passage below mentions {cosa}. Say first,"
    " in one short sentence, that the guidelines you have do not talk about {cosa}; then give what"
    " the passages DO say about caring for it. Do NOT say yes or no to {cosa}, and do not call it"
    " safe or harmful: no source here does.\n"
)


def nota_remedio(pregunta: str, hits: list[Hit]) -> str:
    """La nota para el redactor, o «» si no pregunta por un remedio o una guía lo nombra."""
    if not PONER.search(pregunta):
        return ""
    texto = " ".join(h.chunk.text for h in hits)
    faltan = [
        nombre
        for nombre, patron in REMEDIOS.items()
        if patron.search(pregunta) and not patron.search(texto)
    ]
    if not faltan:
        return ""
    return NOTA.format(cosa=" or ".join(faltan))
