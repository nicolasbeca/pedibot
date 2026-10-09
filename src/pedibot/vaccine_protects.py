"""De qué protege cada vacuna de un calendario (9-oct-2026). Los datos y el porqué, en
`config/vaccine_protects.yaml`; aquí sólo se aplican.

La web recibe el resultado ya calculado (`por_pais`, exportado por `scripts/export_catalog.py`),
igual que los nombres traducidos: el mismo cálculo en Python y en JavaScript acabaría separándose.
"""

from __future__ import annotations

import re
from functools import cache
from typing import Any

import yaml

from pedibot.settings import ROOT

LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


@cache
def _datos() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "config" / "vaccine_protects.yaml").read_text(encoding="utf-8"))


@cache
def _reglas() -> list[tuple[re.Pattern[str], list[str]]]:
    return [(re.compile(r["match"], re.I), list(r["diseases"])) for r in _datos()["rules"]]


def enfermedades(vacuna: str) -> list[str]:
    """Las enfermedades de las que protege, en el orden de la tabla y sin repetir."""
    low = vacuna.lower()
    out: list[str] = []
    for rx, ks in _reglas():
        if rx.search(low):
            out.extend(k for k in ks if k not in out)
    return out


#: Un paréntesis que habla de la dosis o del momento, no de la vacuna: lleva una cifra o más de
#: tres palabras («1re dose, obligatoire», «every year from 6 months»). «(OPV)» y «(tuberculosis)»
#: se quedan: son lo que pone la cartilla.
_PARENTESIS = re.compile(r"\s*\(([^()]*)\)")


def nombre_corto(nombre: str) -> str:
    def quitar(m: re.Match[str]) -> str:
        dentro = m.group(1)
        return "" if re.search(r"\d", dentro) or len(dentro.split()) > 3 else m.group(0)

    n = _PARENTESIS.sub(quitar, nombre)
    n = re.split(r"\s+[—–]\s+", n)[0]
    # el número de la dosis pegado al nombre («OPV-1», «JE-2», «Rotavirus-3»), no el de «6-in-1»
    n = re.sub(r"(?:(?<=[^\W\d_])|(?<=\)))(?<!in)-\d+(?=\s|$|\()", "", n.strip())
    return n.strip(" ,")


def por_pais() -> dict[str, list[dict[str, Any]]]:
    """{país: [{"names": {lengua: [nombre, …]}, "diseases": [clave, …]}]}.

    Una línea por cada conjunto de enfermedades, con todas las vacunas del calendario que lo
    cubren: «DTPa» y «Difteria-tétanos-tosferina (DTPa)» son la misma línea, y MenB, MenC y
    MenACWY van juntas en la de la meningitis."""
    from pedibot.bot.vaccine_names import localise

    paises = yaml.safe_load((ROOT / "config" / "vaccines.yaml").read_text(encoding="utf-8"))["countries"]
    out: dict[str, list[dict[str, Any]]] = {}
    for code, p in paises.items():
        grupos: dict[tuple[str, ...], dict[str, list[str]]] = {}
        for fila in p["schedule"]:
            for v in fila["vaccines"]:
                v = str(v)
                ks = enfermedades(v)
                if not ks:
                    continue
                g = grupos.setdefault(tuple(ks), {lg: [] for lg in LANGS})
                for lg in LANGS:
                    n = nombre_corto(localise(v, lg))
                    # «Varicela» y «Varicela (VVZ)» son la misma: se queda la que trae la sigla
                    base = _PARENTESIS.sub("", n).strip().lower()
                    igual = next((x for x in g[lg] if _PARENTESIS.sub("", x).strip().lower() == base), None)
                    if igual is None:
                        g[lg].append(n)
                    elif len(n) > len(igual):
                        g[lg][g[lg].index(igual)] = n
        out[code] = [{"names": g, "diseases": list(ks)} for ks, g in grupos.items()]
    return out


def tabla_web() -> dict[str, Any]:
    d = _datos()
    return {"countries": por_pais(), "diseases": d["diseases"], "sources": d["sources"]}
