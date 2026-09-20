"""La cinta del brazo: cómo se mide de verdad la desnutrición donde va este proyecto.

20-sep-2026. El sitio ya calcula el peso para la talla con las tablas de la OMS y avisa de la
desnutrición aguda grave. Eso sirve si hay una báscula y un tallímetro. En media África lo que
hay es **una cinta de papel**: el agente de salud comunitario, y muchas veces la propia madre,
mide el perímetro del brazo y lee un color. Es el método que la OMS recomienda para cribar en la
comunidad, y no estaba aquí.

Los cortes, de la guía de la OMS de 2013 sobre el manejo de la desnutrición aguda grave:

    menos de 115 mm ........ desnutrición aguda GRAVE
    de 115 a 125 mm ........ desnutrición aguda moderada
    125 mm o más ........... fuera de esos dos rangos

**Sólo de 6 a 59 meses**, que es el rango para el que existen esos números. Fuera de ahí la
respuesta es que no aplica, no una cifra aproximada: un corte llevado a una edad para la que no
se calculó es peor que no tener corte.

Y dos cosas que esta herramienta NO hace, porque se salen de lo que un padre puede resolver en
casa: no sustituye a la báscula —el peso para la talla y la cinta encuentran niños distintos, y
la OMS pide los dos— y no dice cómo tratar. Un brazo por debajo de 115 mm es una urgencia
médica y lo que toca es ir hoy, no leer más.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Los tres cortes, en milímetros. Están aquí y no en un YAML a propósito: son tres números de
#: una guía publicada, no una preferencia, y no deben poder cambiarse sin tocar este fichero y
#: su prueba.
SEVERE_MM = 115.0
MODERATE_MM = 125.0

#: El rango de edad para el que la OMS da estos cortes. Fuera de él no hay número que dar.
MIN_AGE_MONTHS = 6.0
MAX_AGE_MONTHS = 59.0

SOURCE = (
    "WHO — Guideline: Updates on the management of severe acute malnutrition in infants and "
    "children (2013)"
)
SOURCE_URL = "https://www.who.int/publications/i/item/9789241506328"


@dataclass(frozen=True)
class MuacResult:
    mm: float
    band: str  # "severe" | "moderate" | "ok"
    level: str  # "urgent" | "routine"
    age_months: float | None


#: «El brazo le mide 12 cm», «MUAC 115 mm», «perímetro braquial 11,5». Se acepta en milímetros y
#: en centímetros porque la cinta viene marcada en las dos y los padres copian lo que ven.
_UNIDADES = (
    r"mm|cm|mil[íi]metros?|cent[íi]metros?|mil[íi]metres?|centim[eè]tres?|millim[eè]tres?"
    r"|zentimeter|millimeter|мм|см|مم|سم|मिमी|सेमी|sentimita|milimita"
)
#: El número y su unidad, en los dos órdenes. El suajili escribe «sentimita 11» —la unidad
#: delante— y así lo escribe también quien copia lo que pone en la cinta.
# `(?!\w)` y no `\b`: la barra de palabra NO existe detrás del devanagari, porque «सेमी»
# acaba en una marca combinante y ahí no hay transición que detectar. Es el mismo `\b` que
# ya rompió el triaje en hindi, cazado esta vez por «बाजू की माप 11 सेमी».
_MEDIDA = re.compile(rf"(\d{{1,3}}(?:[.,]\d)?)\s*({_UNIDADES})(?!\w)", re.I)
_MEDIDA_AL_REVES = re.compile(rf"({_UNIDADES})\s*(\d{{1,3}}(?:[.,]\d)?)", re.I)

#: La palabra «brazo» en las nueve lenguas, más los nombres técnicos de la medida.
#:
#: 20-sep-2026: la primera versión de esto pedía «perímetro braquial» o «MUAC», o sea que el
#: padre supiera cómo lo llama la guía. Es el mismo fallo que la palabra «percentil» (L203),
#: repetido doce horas después. Un padre dice «el brazo le mide 11 cm».
_BRAZO = re.compile(
    r"\bmuac\b|\bbrachial\b|shakir"
    r"|brazo|bracito|braquial"
    r"|\barms?\b|upper[- ]arm"
    r"|\bbras\b|brachial"
    r"|\barm\b|oberarm"
    r"|рук[аиуе]\w*|плеч\w*"
    r"|الذراع|ذراعه|ذراعها|العضد"
    r"|बाजू|बांह|बाँह"
    r"|\bmkono\b|mikono",
    re.I,
)

#: Y que no sea una lesión. «Se ha dado un golpe en el brazo y le ha salido un chichón de 3 cm»
#: trae la palabra y trae la medida, y no es esta pregunta ni de lejos.
_ES_LESION = re.compile(
    r"golpe|ca[íi]da|se\s+cay[óo]|roto|rotura|fractur|luxa|esguince|quemad|corte|herida|duele"
    r"|dolor|hinchad|mordi|picadura|moret[óo]n|chich[óo]n|sangr"
    r"|hit|fell|fall|broke|broken|fractur|sprain|burn|cut|wound|hurts?|pain|swollen|swelling"
    r"|bite|bruise|bleed"
    r"|tomb[ée]|cass[ée]|fractur|br[ûu]l|coupure|blessure|mal\s+au|gonfl|piq[ûu]re|bleu|saign"
    r"|gefallen|gebrochen|verbrannt|schnitt|wunde|schmerz|geschwollen|biss|blutet"
    r"|упал|слома|ожог|порез|рана|боли|болит|опух|укус|кровь"
    r"|سقط|كسر|حرق|جرح|ألم|يؤلم|تورم|لدغ|نزيف"
    r"|गिर|टूट|जल|चोट|दर्द|सूज|काट|खून"
    r"|ameanguka|amevunjika|kuungua|jeraha|maumivu|uvimbe|kuumwa|damu",
    re.I,
)


def is_muac_question(text: str) -> bool:
    """La palabra brazo, un número con unidad, y que no sea una lesión.

    Las tres condiciones hacen falta. Sin número no hay nada que leer en la tabla; sin la
    palabra, cualquier medida del mensaje se leería como si fuera el brazo; y sin la tercera, un
    golpe con un chichón de tres centímetros recibiría una franja de desnutrición.
    """
    if not text or not _BRAZO.search(text):
        return False
    if _ES_LESION.search(text):
        return False
    return read_mm(text) is not None


def read_mm(text: str) -> float | None:
    """La medida en milímetros, venga escrita en milímetros o en centímetros.

    «11,5 cm» son 115 mm y «115 mm» también. Los dos se escriben en las cintas, y confundirlos
    es la diferencia entre un niño grave y uno sano, así que la unidad se lee, nunca se supone.
    """
    m = _MEDIDA.search(text or "")
    if m:
        valor, unidad = float(m.group(1).replace(",", ".")), m.group(2).lower()
    else:
        m = _MEDIDA_AL_REVES.search(text or "")
        if not m:
            return None
        unidad, valor = m.group(1).lower(), float(m.group(2).replace(",", "."))
    en_cm = unidad.startswith(("cm", "cent", "см", "سم", "sentimita")) or unidad in (
        "zentimeter",
        "सेमी",
    )
    mm = valor * 10 if en_cm else valor
    # Un brazo de niño está entre 7 y 25 cm. Fuera de ahí lo que hay es un error de unidad o un
    # número mal copiado, y adivinar cuál de los dos sería inventar.
    return mm if 70.0 <= mm <= 250.0 else None


def assess(mm: float, age_months: float | None = None) -> MuacResult | None:
    """La franja en la que cae esa medida, o None si la edad se sale del rango de la guía."""
    if age_months is not None and not (MIN_AGE_MONTHS <= age_months <= MAX_AGE_MONTHS):
        return None
    if mm < SEVERE_MM:
        return MuacResult(mm, "severe", "urgent", age_months)
    if mm < MODERATE_MM:
        return MuacResult(mm, "moderate", "urgent", age_months)
    return MuacResult(mm, "ok", "routine", age_months)


def explain(r: MuacResult, lang: str) -> str:
    """La lectura escrita para un padre, sin pasar por el modelo."""
    from pedibot.bot.strings import tool_strings

    T = tool_strings(lang)
    # La unidad en el alfabeto de quien lee, con la misma tabla que las curvas: «100 mm» dentro
    # de una frase en árabe dice, en cada línea, que el texto no se escribió para ti.
    from pedibot.bot.growth import _UNIDADES

    mm_u = _UNIDADES.get(lang, {}).get("mm", "mm")
    cm_u = _UNIDADES.get(lang, {}).get("cm", "cm")
    medida = f"{r.mm:g} {mm_u} ({r.mm / 10:g} {cm_u})"
    lineas = [T["muac_head"].format(mm=medida), T[f"muac_{r.band}"]]
    if r.band != "ok":
        lineas.append(T["muac_go"])
    lineas.append(T["muac_also"])
    lineas.append(T["vax_source"] + SOURCE + f" — {SOURCE_URL}.")
    return "\n".join(lineas)


#: Lo que el aviso rojo dice como motivo. La cinta es el hallazgo: no hay síntoma que contar.
REASON: dict[str, dict[str, str]] = {
    "severe": {
        "en": "Arm circumference below 115 mm: severe acute malnutrition",
        "es": "Perímetro del brazo por debajo de 115 mm: desnutrición aguda grave",
        "fr": "Périmètre brachial inférieur à 115 mm : malnutrition aiguë sévère",
        "de": "Oberarmumfang unter 115 mm: schwere akute Mangelernährung",
        "ru": "Окружность плеча меньше 115 мм: тяжёлая острая недостаточность питания",
        "ar": "محيط الذراع أقل من 115 مم: سوء تغذية حاد وخيم",
        "pt": "Perímetro do braço abaixo de 115 mm: desnutrição aguda grave",
        "hi": "बाजू की परिधि 115 मिमी से कम: गंभीर तीव्र कुपोषण",
        "sw": "Mzunguko wa mkono chini ya mm 115: utapiamlo mkali sana",
    },
    "moderate": {
        "en": "Arm circumference between 115 and 125 mm: moderate acute malnutrition",
        "es": "Perímetro del brazo entre 115 y 125 mm: desnutrición aguda moderada",
        "fr": "Périmètre brachial entre 115 et 125 mm : malnutrition aiguë modérée",
        "de": "Oberarmumfang zwischen 115 und 125 mm: mäßige akute Mangelernährung",
        "ru": "Окружность плеча от 115 до 125 мм: умеренная острая недостаточность питания",
        "ar": "محيط الذراع بين 115 و125 مم: سوء تغذية حاد متوسط",
        "pt": "Perímetro do braço entre 115 e 125 mm: desnutrição aguda moderada",
        "hi": "बाजू की परिधि 115 से 125 मिमी: मध्यम तीव्र कुपोषण",
        "sw": "Mzunguko wa mkono kati ya mm 115 na 125: utapiamlo mkali wa wastani",
    },
}


def reason(r: MuacResult, lang: str) -> str:
    """El motivo, para el recuadro rojo. Vacío cuando la medida no cae en ninguna franja."""
    return (REASON.get(r.band) or {}).get(lang) or (REASON.get(r.band) or {}).get("en", "")
