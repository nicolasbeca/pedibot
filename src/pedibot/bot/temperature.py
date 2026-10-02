"""Los grados en las unidades del padre (2-oct-2026).

Las guías están en Celsius y el modelo escribe en Celsius. Un padre de EE. UU. piensa en
Fahrenheit: «fever of 39» recibió «38 °C or more» y «110 degree celsius» recibió «110 °C is not a
real body temperature», cuando 110 sólo tiene sentido en °F. Esto es aritmética, así que se hace
aquí y no se le pide al modelo: cada cifra en °C de la respuesta lleva su °F entre paréntesis, y
un número que el padre escribió y sólo cabe en °F abre la respuesta con su conversión.
"""

from __future__ import annotations

import re

#: Donde el termómetro de casa marca Fahrenheit: EE. UU. y sus territorios, Liberia, Belice,
#: Bahamas, Caimán, Palaos, Micronesia y las Marshall.
FAHRENHEIT_COUNTRIES = frozenset(
    {"US", "PR", "GU", "VI", "AS", "MP", "UM", "LR", "BZ", "BS", "KY", "PW", "FM", "MH"}
)

_ESCRIBE_F = re.compile(
    r"\d\s*(?:°|º|deg(?:ree)?s?|grados?)?\s*(?:F\b|fahrenheit)", re.IGNORECASE
)
#: Una cifra que sólo es una temperatura del cuerpo en °F (35 °C = 95 °F; 46 °C = 115 °F), con
#: algo al lado que diga que es una temperatura, para no leer «101 pounds» como fiebre.
_NUM_F = re.compile(r"(?<![\d.,])(9[5-9]|1[01]\d)(?:[.,](\d))?(?![\d])")
_ES_TEMPERATURA = re.compile(
    r"fever|temp|degree|°|º|celsius|fahrenheit|fiebre|grados|fièvre|fieber|febre|"
    r"температур|жар|حرارة|حمى|बुखार|तापमान|homa",
    re.IGNORECASE,
)
_NO_ES_TEMPERATURA = re.compile(r"pounds?|lbs?\b|libras?|kg|kilos?|cm|ml|mg", re.IGNORECASE)

#: «38 °C», «37.5°C», «38,5 ºC»… que no lleve ya su °F detrás.
#: También «39C» y «38 degrees C», que el modelo escribe a veces (en vivo, 2-oct-2026).
_C = re.compile(
    r"(?<![\d.,])(\d{2})(?:([.,])(\d))?(\s?)(?:[°º]\s?|\s?degrees?\s)?C\b"
    r"(?!\s*\(\s*\d+(?:[.,]\d)?\s*°F)"
)


def _f_de(c: float) -> float:
    return round(c * 9 / 5 + 32, 1)


def _c_de(f: float) -> float:
    return round((f - 32) * 5 / 9, 1)


def _fmt(x: float, coma: bool) -> str:
    s = f"{x:.1f}".rstrip("0").rstrip(".")
    return s.replace(".", ",") if coma else s


def _numero_en_f(pregunta: str) -> tuple[str, float] | None:
    if not _ES_TEMPERATURA.search(pregunta) or _NO_ES_TEMPERATURA.search(pregunta):
        return None
    m = _NUM_F.search(pregunta)
    if not m:
        return None
    texto = m.group(1) + (f".{m.group(2)}" if m.group(2) else "")
    return texto, float(texto)


def lee_en_fahrenheit(pregunta: str, country: str | None) -> bool:
    """¿Este padre necesita los °F?"""
    if (country or "").upper() in FAHRENHEIT_COUNTRIES:
        return True
    return bool(_ESCRIBE_F.search(pregunta or "")) or _numero_en_f(pregunta or "") is not None


def con_fahrenheit(texto: str) -> str:
    """Cada temperatura del cuerpo en °C con su °F al lado. Las que no son del cuerpo (110 °C),
    no: convertir un disparate sólo lo hace más largo."""

    def cambia(m: re.Match[str]) -> str:
        coma = m.group(2) == ","
        c = float(m.group(1) + (f".{m.group(3)}" if m.group(3) else ""))
        if not 30 <= c <= 45:
            return m.group(0)
        return f"{m.group(0)} ({_fmt(_f_de(c), coma)} °F)"

    return _C.sub(cambia, texto)


def nota_de_conversion(pregunta: str) -> str | None:
    """«110 °F = 43.3 °C» cuando el padre escribió una cifra que sólo cabe en °F."""
    got = _numero_en_f(pregunta or "")
    if got is None:
        return None
    texto, f = got
    return f"{texto} °F = {_fmt(_c_de(f), False)} °C"
