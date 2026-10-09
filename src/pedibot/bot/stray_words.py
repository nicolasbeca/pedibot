"""Palabras españolas que se cuelan en respuestas en otra lengua (9-oct-2026).

Muchas guías del índice están en castellano (SEUP, AEPap, Familia y Salud) y el modelo las
traduce al contestar. A veces deja un término clínico sin traducir: el 9-oct un padre de EE. UU.
leyó «after an antitérmico» (consulta real 1053). Es un cambio de palabra, así que se hace aquí y
no se le pide al modelo. La lista crece con cada fuga vista en una consulta real, nunca a ojo.
Las lenguas que tienen la palabra como propia (el portugués dice «antitérmico») no se tocan.
"""

from __future__ import annotations

import re

#: término español → {lengua: (singular, plural)}
_SUELTAS: dict[str, dict[str, tuple[str, str]]] = {
    "antit[eé]rmico": {
        "en": ("fever medicine", "fever medicines"),
        "fr": ("antipyrétique", "antipyrétiques"),
        "de": ("fiebersenkendes Mittel", "fiebersenkende Mittel"),
    },
}


def sin_palabras_sueltas(texto: str, lang: str) -> str:
    for raiz, por_lengua in _SUELTAS.items():
        cambio = por_lengua.get(lang)
        if not cambio:
            continue
        patron = re.compile(rf"(\b[Aa]n\s+)?\b({raiz})(s?)\b", re.IGNORECASE)

        def _pon(m: re.Match[str], cambio: tuple[str, str] = cambio) -> str:
            palabra = cambio[1] if m.group(3) else cambio[0]
            if m.group(2)[0].isupper() and lang != "de":
                palabra = palabra[0].upper() + palabra[1:]
            articulo = m.group(1) or ""
            if articulo and lang == "en":
                # «an antitérmico» → «a fever medicine»
                articulo = ("A" if articulo[0] == "A" else "a") + articulo[2:]
            return articulo + palabra

        texto = patron.sub(_pon, texto)
    return texto
