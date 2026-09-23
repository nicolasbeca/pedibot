"""«¿Cuál es el número de urgencias aquí?», contestado con la tabla y no con el corpus.

20-sep-2026, probando el sitio vivo: un padre en Nigeria pregunta el número de urgencias y el
chat contesta «no tengo información fiable sobre esto en mis fuentes» mientras el aviso de arriba
lleva el 112 escrito. Teníamos el dato de 90 países, comprobado uno a uno contra su fuente
oficial, y la pregunta más básica de todas se iba al corpus a buscar un pasaje que no existe.

Es el mismo arreglo que ya tienen las vacunas y las dosis: cuando la pregunta es exactamente lo
que una tabla contesta, contesta la tabla. El modelo no interviene, no hay nada que verificar y
no hay forma de que salga un número inventado.

**Sólo cuando el triaje dice `routine`.** Si el niño se está atragantando, esta pregunta no es
una consulta de datos: el aviso ya manda llamar, y lo que el texto tiene que decir es qué hacer
mientras llega la ayuda. Una tabla no sirve para eso.

Y los siete países sin número nacional siguen diciéndolo, que es la razón de que este fichero
exista con esta forma y no como un diccionario de códigos.
"""

from __future__ import annotations

import re
from functools import lru_cache as _lru
from typing import Any

_cache = _lru(maxsize=1)

#: «¿Qué número se marca?». En las nueve lenguas, y con el suajili porque la capa de seguridad
#: ya lo lee. Se pide la PALABRA número junto a la de urgencias: «llama a urgencias» no es esta
#: pregunta —eso es una instrucción, y ya la da el aviso—, y «me duele el número» no existe.
_PREGUNTA = re.compile(
    r"(?:what|which)[^.?]{0,25}\b(?:emergency|ambulance)[^.?]{0,20}\bnumber"
    r"|\bemergency number\b[^.?]{0,25}\b(?:here|in|for|of|call)"
    r"|\b(?:number|phone)\b[^.?]{0,20}\b(?:to call|for an ambulance|for emergencies)"
    r"|(?:qu[ée]|cu[áa]l)[^.?]{0,25}\bn[úu]mero[^.?]{0,20}(?:urgencias|emergencias|ambulancia)"
    r"|\bn[úu]mero de (?:urgencias|emergencias|ambulancia)\b"
    r"|\bnum[ée]ro[^.?]{0,20}(?:d'urgence|des urgences|d'ambulance)"
    r"|\bnotrufnummer\b|\bnotruf\b[^.?]{0,20}\bnummer"
    r"|(?:какой|как[ао]й)[^.?]{0,25}(?:номер)[^.?]{0,25}(?:скорой|экстренн)"
    r"|\bномер (?:скорой|экстренной службы)\b"
    r"|(?:ما|أي)[^.?]{0,25}(?:رقم)[^.?]{0,20}(?:الطوارئ|الإسعاف)"
    r"|\bرقم (?:الطوارئ|الإسعاف)\b"
    r"|\bn[úu]mero d[eo] (?:emerg[êe]ncia|urg[êe]ncia|ambul[âa]ncia)\b"
    r"|(?:आपातकालीन|एम्बुलेंस)[^.?]{0,20}(?:नंबर|नम्बर)"
    # 23-sep-2026, séptima tanda: «a qué número llamo si se pone peor?». Estaban «número de
    # urgencias» y «qué número de emergencias», pero no la forma corta, que es la que sale
    # cuando hay prisa. Pide el verbo llamar al lado para no confundirla con «¿cuántos
    # mililitros?» ni con un número de teléfono cualquiera.
    r"|a qu[ée] n[úu]mero[^.?]{0,20}\b(?:llam|marc|telefon)"
    r"|\bqu[ée] n[úu]mero[^.?]{0,15}\b(?:llam|marc)"
    r"|\b(?:which|what) number[^.?]{0,15}\b(?:do i call|to call|should i call)"
    r"|\bquel num[ée]ro[^.?]{0,15}\bappeler"
    r"|\bwelche nummer[^.?]{0,15}\b(?:anrufen|w[äa]hlen)"
    r"|\bnamba ya (?:dharura|ambulensi)\b",
    re.I,
)


def is_emergency_number_question(text: str) -> bool:
    """¿Está preguntando qué número se marca, y no describiendo un síntoma?"""
    return bool(_PREGUNTA.search(text or ""))


def format_numbers(datos: dict[str, Any], pais_nombre: str, lang: str) -> str:
    """Los números de ese país, tal y como están en la tabla, sin adornos.

    No se escribe ninguna frase de urgencia: eso lo decide el triaje y lo dice el aviso. Aquí
    sólo se lee la tabla en voz alta, que es lo que se ha preguntado.
    """
    from pedibot.bot.strings import tool_strings

    T = tool_strings(lang)
    lineas: list[str] = []
    numero = datos.get("emergency")
    if numero:
        lineas.append(T["emgq_number"].format(country=pais_nombre, number=numero))
    elif datos.get("no_national"):
        lineas.append(T["emgq_none"].format(country=pais_nombre))
    else:
        lineas.append(T["emgq_unsure"].format(country=pais_nombre))
    if datos.get("poison"):
        lineas.append(T["emgq_poison"].format(number=datos["poison"]))
    if datos.get("mental"):
        lineas.append(T["emgq_mental"].format(number=datos["mental"]))
    nota = datos.get("note")
    if isinstance(nota, dict):
        # 20-sep-2026: las 25 notas estaban en inglés y salían dentro de respuestas en español,
        # árabe e hindi. Son la parte más consecuente de la página —«puede que no venga nadie,
        # organiza tú el transporte»— y veintitrés de las veinticinco son de países africanos.
        from pedibot.bot.strings import data_lang

        nota = nota[data_lang(nota, lang)]
    if nota:
        lineas.append(str(nota))
    fuente = datos.get("source")
    if fuente:
        url = datos.get("source_url")
        lineas.append(T["vax_source"] + str(fuente) + (f" — {url}" if url else "") + ".")
    return "\n".join(lineas)


@_cache
def _nombres() -> dict[str, dict[str, str]]:
    """Los nombres de país por lengua, generados con `Intl` por el lado del sitio.

    Python no tiene de dónde sacar «Marruecos»: `locale` depende de lo que el servidor tenga
    instalado y una dependencia más para esto no se sostiene. Node sí lo sabe, y es además la
    MISMA fuente con la que la web pinta sus desplegables, así que los dos lados dicen el mismo
    nombre por construcción. Lo genera `web/site/scripts/export-country-names.mjs`.
    """
    import json

    from pedibot.settings import ROOT

    ruta = ROOT / "config" / "country_names.json"
    if not ruta.exists():
        return {}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def country_name(cc: str, lang: str) -> str:
    """El nombre de ese país en esa lengua, o su código si no se sabe.

    El código es una respuesta fea y es la honesta: «En NG el número es el 112» se entiende, y
    fabricar un nombre no.
    """
    tabla = _nombres()
    por_lengua = tabla.get(lang) or tabla.get("en") or {}
    return por_lengua.get(cc.upper()) or cc.upper()
