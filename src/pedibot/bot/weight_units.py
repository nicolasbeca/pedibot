"""El peso en las unidades del padre (5-oct-2026).

Las tablas de dosis y las curvas de la OMS van en kilos. Un padre de EE. UU. —la mayoría de las
consultas reales— dice «22 pounds», y el motor no lo leía: ni la calculadora de dosis, ni las
curvas, ni el campo de peso del chat cuando se escribe «18 lbs». Es aritmética, así que se hace
aquí y sin modelo, como los grados en `temperature.py`: cada peso en libras lleva al lado sus
kilos, «22 pound (10 kg)», y todo lo que lee pesos los encuentra ya en kilos.
"""

from __future__ import annotations

import re

LB_KG = 0.45359237

#: Una cifra con «pound(s)», «lb(s)» o «libra(s)» detrás, que no lleve ya sus kilos.
_LIBRAS = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:[.,]\d+)?)\s*(pounds?|lbs?|libras?)\b(?!\s*\(\s*\d+(?:[.,]\d+)?\s*kg\))",
    re.IGNORECASE,
)

#: Un bebé prematuro pesa unas 2 libras y un adolescente grande pasa de 200; fuera de eso no es
#: el peso de un niño (y «1 pound» suele ser dinero o una tarta).
_MIN_LB, _MAX_LB = 2.0, 300.0

_COMA_DECIMAL = {"es", "fr", "de", "pt", "ru"}
_NOMBRE = {"es": "libras", "pt": "libras", "fr": "livres", "de": "Pfund", "ru": "фунтов"}


def _kilos(m: re.Match[str]) -> float | None:
    lb = float(m.group(1).replace(",", "."))
    if not _MIN_LB <= lb <= _MAX_LB:
        return None
    return round(lb * LB_KG, 1)


def con_kilos(texto: str) -> str:
    """El texto con «(N kg)» detrás de cada peso en libras. Lo demás, intacto."""

    def pon(m: re.Match[str]) -> str:
        kg = _kilos(m)
        return m.group(0) if kg is None else f"{m.group(0)} ({kg:g} kg)"

    return _LIBRAS.sub(pon, texto or "")


def nota_de_peso(texto: str, lang: str) -> str | None:
    """«24 lb = 10.9 kg», para abrir la respuesta: el padre ve con qué peso se ha calculado."""
    partes = []
    for m in _LIBRAS.finditer(texto or ""):
        kg = _kilos(m)
        if kg is None:
            continue
        lb = m.group(1)
        kg_txt = f"{kg:g}"
        if lang in _COMA_DECIMAL:
            kg_txt = kg_txt.replace(".", ",")
        partes.append(f"{lb} {_NOMBRE.get(lang, 'lb')} = {kg_txt} kg")
    return "; ".join(dict.fromkeys(partes)) or None
