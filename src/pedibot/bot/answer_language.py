"""La respuesta en inglés cuando el padre escribió en otra lengua (4-nov-2026).

«mtoto wangu ana upele mwekundu usiopotea nikibonyeza», con la web en inglés: una de cada tres
respuestas salía en inglés bajo el aviso en suajili. La lectura de la IA acertaba la lengua y el
redactor recibía «ANSWER LANGUAGE: Swahili»; los pasajes, del NHS, lo arrastraban al inglés.

Sólo en un sentido: se pidió otra lengua y el texto sale en inglés. Entre otras dos lenguas el
detector se confunde más (portugués y español), y ahí no se decide nada. Ver
tests/test_the_answer_stays_in_their_language.py.
"""

from __future__ import annotations

import re

from pedibot.bot.retrieval import detect_lang

_CIT = re.compile(r"\[\d{1,2}\]")

#: las lenguas con alfabeto propio. El detector pide más de la mitad de las letras, y un texto en
#: hindi lleno de marcas («Crocin drops», «Calpol syrup») no llega: con una quinta parte basta
_ALFABETO = {"ru": ("Ѐ", "ӿ"), "ar": ("؀", "ۿ"), "fa": ("؀", "ۿ"),
             "hi": ("ऀ", "ॿ")}


def se_pasa_al_ingles(texto: str, codigo: str | None, nombre: str) -> str | None:
    """La nota para el reintento, o `None` si la respuesta está en la lengua pedida o no se sabe."""
    if not codigo or codigo == "en":
        return None
    if codigo in _ALFABETO:
        a, b = _ALFABETO[codigo]
        letras = [c for c in texto if c.isalpha()]
        if letras and sum(a <= c <= b for c in letras) / len(letras) >= 0.2:
            return None
    if detect_lang(_CIT.sub(" ", texto)) != "en":
        return None
    return (
        f"wrong_language: the parent wrote in {nombre} and your answer is in English. Write the"
        f" whole answer in {nombre}, keeping every fact and every citation"
    )
