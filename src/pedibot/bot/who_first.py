"""Donde la guía de la OMS es la norma nacional, tiene que ir delante (20-sep-2026).

El corpus de este proyecto está escorado a Europa y a Estados Unidos, porque es de donde se
puede reutilizar material con licencia clara. Eso no se nota en casi nada: una fiebre es una
fiebre en Nairobi y en Madrid. Se nota en lo poco donde el tratamiento estándar **es distinto
según dónde viva el niño**, y la diarrea infantil es el caso de libro.

El caso que lo destapó, probando la web viva como un padre de Nairobi: «my baby is 7 months and
has watery diarrhoea since yesterday», con Kenia seleccionada. La respuesta era correcta y
segura —suero en cantidades pequeñas, nada de refrescos, cuándo ir al médico— citando a
MedlinePlus y a la SEUP, y **no mencionaba el zinc**, que allí es la mitad del tratamiento.

Lo importante: **el documento de la OMS ya estaba en el corpus y sí salía** cuando la pregunta
era de tratamiento. Lo que fallaba es que, cuando el padre **describe un síntoma** en vez de
pedir un remedio, ganan las fuentes europeas — y un padre asustado describe un síntoma.

Así que esto no añade fuentes ni escribe nada en la respuesta. Empuja unos términos en la
recuperación para que el documento que allí es la norma entre entre los pasajes que el modelo
tiene delante. Si el modelo no lo usa, no pasa nada; si lo usa, lo cita.

**De dónde sale «donde es la norma».** No de mí. La propia hoja de la OMS acota su alcance:
«Diarrhoea due to infection is widespread throughout developing countries. In low-income
countries, children under 3 years old experience on average three episodes of diarrhoea every
year», y pone el suero y el zinc juntos como medidas clave de tratamiento. Esa frase se traduce
a códigos de país con la clasificación por renta del Banco Mundial, que es pública, anual y
descargable (`scripts/build_income_levels.py` → `config/income_levels.json`).

La tentación era escribir «los africanos y los del sur de Asia». Suena razonable y es justo lo
que no se hizo con las marcas de Etiopía y del Congo: plausible no es una fuente.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from pedibot.settings import ROOT

#: Los términos que se empujan. **Ninguno lleva una cifra, y es a propósito**: la dosis de zinc
#: depende de la edad —distinta por encima y por debajo de los seis meses— y una cifra va por la
#: vía de las dosis, con su tabla y su fuente, o no va. Aquí sólo se pide que el documento de la
#: OMS compita por entrar entre los pasajes.
WHO_DIARRHOEA_TERMS: tuple[str, ...] = (
    "zinc",
    "rehydration",
    "rehidratación",
    "réhydratation",
    "ors",
    "sro",
)

#: La palabra en las ocho lenguas del sitio, por prefijo. «Deposiciones líquidas» y «loose
#: stools» entran porque es como lo escribe un padre que no usa la palabra clínica.
_DIARREA = re.compile(
    r"diarre|diarrh|diarré|durchfall|поно́с|понос|диаре|إسهال|اسهال|दस्त|अतिसार"
    r"|deposiciones? l[ií]quid|heces l[ií]quid|loose stool|watery stool|selles liquides"
    r"|wässrig|wassrig|жидкий стул|براز مائي|पतले दस्त|fezes l[ií]quidas",
    re.I,
)

#: Lo que NO es diarrea aunque comparta el tema «digestivo» de la taxonomía. Sin esto, una
#: pregunta de estreñimiento en Nigeria se llevaría términos de rehidratación, que es lo
#: contrario de lo que necesita.
_NO_ES = re.compile(
    r"estre[ñn]i|constipat|verstopfung|запор|إمساك|कब्ज|prisão de ventre"
    r"|lombric|oxiuro|threadworm|pinworm|oxyure|madenw[üu]rmer|острицы|ديدان|कीड़े",
    re.I,
)


@lru_cache(maxsize=1)
def _income() -> frozenset[str]:
    d = json.loads((ROOT / "config" / "income_levels.json").read_text(encoding="utf-8"))
    return frozenset(c.upper() for c in d["low_and_lower_middle_income"])


LOW_INCOME: frozenset[str] = _income()


def is_a_diarrhoea_question(text: str) -> bool:
    """¿Habla de diarrea, y no de otra cosa del aparato digestivo?"""
    if not text:
        return False
    return bool(_DIARREA.search(text)) and not _NO_ES.search(text)


#: La nota que se le da al redactor. **No afirma nada**, y eso es deliberado: le dice que no se
#: deje la mitad de lo que su propia fuente citada enumera. Si el pasaje de la OMS no está entre
#: los que le han tocado, no tiene nada que obedecer y la nota no hace nada.
#:
#: Hizo falta porque el empujón de la recuperación funcionó y no bastó: con Kenia, el pasaje
#: «Prevention and treatment» de la OMS ya entraba entre las fuentes y el modelo contaba de él el
#: suero, la alimentación y el lavado de manos, y se saltaba el zinc. No es mala fe: la regla 6
#: del prompt le pide 110 palabras, y algo tiene que caerse. Esto le dice qué no.
PROMPT_NOTE = (
    "LOCAL STANDARD: this parent's country follows WHO guidance for childhood diarrhoea, where "
    "oral rehydration salts and zinc supplements are BOTH listed as key treatment measures. If a "
    "WHO passage among your sources says so, do not present rehydration as the only one and do "
    "not drop the zinc — it is not optional there. Give no amount and no duration unless a "
    "passage states them literally.\n"
)


def prompt_note(text: str, country: str | None) -> str:
    """La nota para el redactor, o cadena vacía. Mismas condiciones que `extra_terms`."""
    return PROMPT_NOTE if extra_terms(text, country) else ""


def extra_terms(text: str, country: str | None) -> list[str]:
    """Los términos a empujar, o nada.

    Sin país no se supone nada: quien no ha elegido no es «probablemente de renta baja», es
    desconocido, y adivinarlo sería la misma clase de error que el selector de país que venía
    con los Emiratos preseleccionados.
    """
    if not country or country.upper() not in LOW_INCOME:
        return []
    if not is_a_diarrhoea_question(text):
        return []
    return list(WHO_DIARRHOEA_TERMS)


# ── Y la mitad simétrica: lo tropical donde no lo hay (23-sep-2026) ──────────────────────────
#
# Del registro: «My 8 year old has vomiting, fever and a red rash», con Estados Unidos elegido.
# La respuesta hablaba de la SEUP y después del DENGUE, con sus signos de alarma. La hoja de la
# OMS está en el corpus, encaja con esas tres palabras y el modelo la usó. Para ese padre no es
# información: es un susto y una pista falsa, y mientras lee eso no está mirando si las manchas
# se borran al presionar.
#
# Esto no quita la hoja ni la esconde: le dice al redactor dónde vive el niño. Donde el dengue
# ES endémico no se dice nada, y un viaje mencionado lo reabre — que es cuando de verdad hay que
# nombrarlo.
TROPICALES = ("dengue", "malaria", "paludismo", "chikun", "zika", "tifoidea", "typhoid")

#: Países donde estas enfermedades NO son endémicas. Lista corta y explícita a propósito: lo que
#: no está aquí no recibe la nota, porque equivocarse en este sentido es peor.
SIN_ENDEMIA = frozenset(
    {
        "US",
        "CA",
        "GB",
        "IE",
        "ES",
        "PT",
        "FR",
        "DE",
        "IT",
        "NL",
        "BE",
        "LU",
        "CH",
        "AT",
        "SE",
        "NO",
        "DK",
        "FI",
        "IS",
        "PL",
        "CZ",
        "SK",
        "HU",
        "RO",
        "BG",
        "GR",
        "HR",
        "SI",
        "EE",
        "LV",
        "LT",
        "RU",
        "UA",
        "BY",
        "NZ",
        "JP",
        "KR",
    }
)

_VIAJE = re.compile(
    r"\b(viaj\w+|volvimos de|venimos de|hemos estado en|estuvimos en|de vacaciones en"
    r"|travel\w*|trip|came back from|just returned|holiday in|voyage|revenons de"
    r"|reise|urlaub in|поездк\w*|путешеств\w*|سفر|यात्रा)\b",
    re.I | re.U,
)

TROPICAL_NOTE = (
    "WHERE THE CHILD IS: this family is in a country where dengue, malaria, chikungunya, Zika "
    "and typhoid are NOT endemic, and they have not mentioned any travel. If a passage is about "
    "one of those, do not offer it as a possible cause of what the parent describes. Use the "
    "passages about what is common where they are. Say nothing about this instruction.\n"
)


def tropical_note(text: str, country: str | None) -> str:
    """La nota sobre enfermedades tropicales, o cadena vacía.

    23-sep-2026, segunda vuelta. La primera versión pedía país conocido Y la palabra «fiebre» en
    la pregunta, y por eso no se aplicó a «respira rápido pero no tiene fiebre y está tranquilo»,
    que recibió los signos de gravedad del dengue como explicación. Ahora la nota se pone
    siempre, salvo en los tres casos en que esas hojas sí vienen a cuento:

    - el niño está en un país donde eso es endémico (sólo se calla donde se sabe que lo es);
    - el padre cuenta un viaje;
    - el padre nombra la enfermedad, y entonces la pregunta ES esa.

    Quien no ha elegido país sigue sin ser «seguramente europeo». Pero ofrecerle dengue para
    explicarle un síntoma suelto no le ayuda en ningún país del mundo.
    """
    bajo = (text or "").lower()
    if country and country.upper() not in SIN_ENDEMIA:
        return ""
    if _VIAJE.search(bajo):
        return ""
    if any(n in bajo for n in TROPICALES):
        return ""
    return TROPICAL_NOTE
