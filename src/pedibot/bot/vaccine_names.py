"""El nombre de una vacuna, en el idioma del que pregunta (20-sep-2026).

58 de los 66 calendarios salen del almacén público de la OMS, que los da en inglés. Un padre
marroquí preguntando en árabe leía «Polio, oral (OPV)» y «Vitamin A (a supplement, not a
vaccine)» en mitad de una respuesta en su idioma, y son justo los países a los que va esto.

**La sigla no se traduce.** BCG, OPV, IPV, MMR, DTP, HPV y Hib es lo que está impreso en la
cartilla de papel que la madre tiene en la mano, en Nairobi igual que en Sevilla, y es lo que le
van a decir en el centro de salud. Lo que se traduce es lo que la explica.

Lo que no esté en la tabla **sale tal cual**, y eso es la regla, no el apaño: los ocho
calendarios transcritos a mano del documento nacional usan las palabras del propio ministerio, y
ésas mandan sobre cualquier traducción que se pueda hacer aquí.
"""

from __future__ import annotations

import functools
import re
from typing import Any

import yaml

from pedibot.settings import ROOT

#: «DTaP-Hib-HepB-IPV (hexavalent) or DTwP-Hib-HepB (pentavalent)». Se parte por « or », pero
#: sólo donde los paréntesis están cerrados: «MMRV vaccine (1st or 2nd dose after 1 July 2024)»
#: es UN nombre, y partirlo ahí lo dejaba en «MMRV vaccine (1st» y «2nd dose after…)».
_O = " or "

#: «— 2nd dose 1 months later», tal cual lo escribe el generador de la OMS.
_SEGUNDA = re.compile(r" — 2nd dose (\d+) (months?|years?|weeks?) later$")


@functools.lru_cache(maxsize=1)
def _tabla() -> dict[str, Any]:
    ruta = ROOT / "config" / "vaccine_names.yaml"
    return yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}


def _parte_por_or(nombre: str) -> list[str]:
    """Parte por « or » sólo cuando no estamos dentro de un paréntesis."""
    trozos: list[str] = []
    resto = nombre
    while True:
        i = resto.find(_O)
        if i < 0:
            trozos.append(resto)
            return trozos
        izquierda = resto[:i]
        if izquierda.count("(") == izquierda.count(")"):
            trozos.append(izquierda)
            resto = resto[i + len(_O) :]
        else:
            # el « or » está dentro de un paréntesis: se busca el siguiente
            j = resto.find(_O, i + 1)
            if j < 0:
                trozos.append(resto)
                return trozos
            izquierda, resto = resto[:j], resto[j + len(_O) :]
            trozos.append(izquierda)


def _una(nombre: str, lang: str, tabla: dict[str, Any]) -> str:
    """Un nombre suelto, ya sin « or »: se le quitan las coletillas, se traduce y se rehace."""
    cola = ""
    segunda = _SEGUNDA.search(nombre)
    if segunda:
        nombre = nombre[: segunda.start()]
        plantilla = (tabla.get("second_dose") or {}).get(lang)
        unidad_en = segunda.group(2).rstrip("s") + "s"  # «month» y «months» son la misma
        # «2.ª dosis 1 meses después» se lee como un error porque lo es
        cual = "units_one" if segunda.group(1) == "1" else "units"
        unidad = ((tabla.get(cual) or {}).get(unidad_en) or {}).get(lang, segunda.group(2))
        if plantilla:
            cola = plantilla.format(n=segunda.group(1), unit=unidad) + cola

    for sufijo, traducciones in (tabla.get("suffixes") or {}).items():
        if nombre.endswith(sufijo):
            nombre = nombre[: -len(sufijo)]
            cola = traducciones.get(lang, sufijo) + cola
            break

    traducido = ((tabla.get("names") or {}).get(nombre.strip()) or {}).get(lang)
    return (traducido or nombre) + cola


def localise(nombre: str, lang: str) -> str:
    """El nombre de una vacuna en ese idioma, o el mismo nombre si no está en la tabla."""
    if not nombre or lang == "en":
        # En inglés la tabla diría lo mismo que ya pone, y pasar por ella sólo añade formas de
        # equivocarse. La entrada `en` existe igualmente, para poder comprobar la tabla entera.
        return nombre
    tabla = _tabla()
    trozos = _parte_por_or(nombre)
    o = (tabla.get("or_word") or {}).get(lang, _O)
    return o.join(_una(t, lang, tabla) for t in trozos)


def list_separator(lang: str) -> str:
    """La coma con la que se juntan dos vacunas de la misma visita, en esa lengua."""
    return ((_tabla().get("list_sep") or {}).get(lang)) or ", "


def known_names() -> set[str]:
    """Los nombres que la tabla sabe traducir. Lo usan las pruebas y el informe de cobertura."""
    return set((_tabla().get("names") or {}).keys())
