"""Agua o líquidos a un bebé de menos de seis meses (4-nov-2026).

«mtoto wangu njiti wa wiki mbili hanyonyi vizuri na ana homa» daba el aviso en suajili y debajo
«Endelea kumnyonyesha mara kwa mara na mpe maji mengi» —sigue con el pecho y dale mucha agua—, a
un prematuro de dos semanas. El NHS de la fiebre dice «plenty of fluids – if your baby is
breastfed, continue to breastfeed»; el redactor lo volvió agua. Antes de los seis meses, sólo pecho
o fórmula.

Aquí decide el código, frase a frase:
  - el agua nombrada («maji», «agua», «water»…) cuenta aunque la frase hable del pecho, porque
    entonces va además de él;
  - los líquidos en general («fluids», «líquidos») cuentan sólo si la frase no dice pecho, leche o
    fórmula, que es como lo dice el NHS;
  - no cuenta si la niega en la misma oración («no le des agua», «usimpe maji»), ni el agua que no
    se bebe (baño, jabón, lavados nasales, «upungufu wa maji» = deshidratación), ni el suero oral.
Entonces, un reintento con la nota. Ver tests/test_no_water_under_six_months.py.
"""

from __future__ import annotations

import re

#: el agua nombrada
AGUA = re.compile(
    r"\b(water|agua|eau|wasser|[áa]gua|maji|voda|вод\w*)\b|पानी|ماء|مياه", re.IGNORECASE
)

#: los líquidos en general
LIQUIDOS = re.compile(
    r"\b(fluids?|liquids?|drinks?|l[íi]quidos?|bebidas?|liquides?|boissons?|flüssigkeit\w*"
    r"|vinywaji|жидкост\w*)\b|तरल|سوائل",
    re.IGNORECASE,
)

#: el pecho, la leche o la fórmula
LECHE = re.compile(
    r"breast|milk|formula|feed|pecho|leche|f[óo]rmula|lactanc|\btomas\b|sein|lait|allait|biberon"
    r"|stillen|muttermilch|brust|fläschchen|peito|leite|mamar|amament|nyony|maziwa"
    r"|दूध|स्तनपान|حليب|رضاع|молок|грудн|смес",
    re.IGNORECASE,
)

#: el agua que no se bebe, o el suero oral: la frase no cuenta
NO_SE_BEBE = re.compile(
    r"bañ|bath|ba[ñn]o|jab[óo]n|soap|savon|seife|sab[ãa]o|sabuni|lav(a|e|ar)|wash|grifo|tap water"
    r"|nasal|nariz|pua\b|oga\b|kuoga|नहला|स्नान|पोंछ|sponge|esponj|sifongo"
    r"|ors\b|suero oral|rehidrat|rehydrat|réhydrat",
    re.IGNORECASE,
)

#: la deshidratación lleva el agua dentro y no es darla: se quita antes de mirar
DESHIDRATACION = re.compile(
    r"upungufu wa maji( mwilini)?|dehydrat\w*|deshidrat\w*|पानी की कमी", re.IGNORECASE
)

#: una negación en la misma oración, antes del agua. Sin «ni», que en suajili es «es» (y el
#: «ni agua» español ya lleva su «no» delante); «usi-» niega en suajili, salvo «usiku», de noche
NIEGA = re.compile(
    r"\b(no|not|don'?t|do not|never|nunca|ne|pas|jamais|kein\w*|nicht|não|nao|nem|usi(?!ku\b)\w*"
    r"|wala|hapana|не|нельзя)\b|नहीं|मत|لا",
    re.IGNORECASE,
)

_FRASE = re.compile(r"(?<=[.!?।؟])\s+|\n+")
_ORACION = re.compile(r"[,;:–—]")


def _negada(frase: str, donde: int) -> bool:
    antes = _ORACION.split(frase[:donde])[-1]
    return bool(NIEGA.search(antes))


def _da_agua(frase: str) -> bool:
    if NO_SE_BEBE.search(frase):
        return False
    f = DESHIDRATACION.sub(" ", frase)
    for m in AGUA.finditer(f):
        if not _negada(f, m.start()):
            return True
    if LECHE.search(f):
        return False
    return any(not _negada(f, m.start()) for m in LIQUIDOS.finditer(f))


def da_agua_al_lactante(texto: str, edad_meses: float | None) -> str | None:
    """La nota para el reintento, o `None` si el niño no es un lactante o no se le da agua."""
    if edad_meses is None or edad_meses >= 6:
        return None
    if not any(_da_agua(f) for f in _FRASE.split(texto)):
        return None
    return (
        "water_under_6_months: this baby is under 6 months, and babies this age take only breast"
        " milk or formula. Do not advise water or other drinks; say instead to keep offering breast"
        " milk or formula, more often if needed"
    )
