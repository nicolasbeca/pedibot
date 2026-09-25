"""Text cleaning: hyphenation, whitespace, repeated headers/footers, noise lines."""

from __future__ import annotations

import re
from collections import Counter

from pedibot.ingest.extract import Extracted, Line

_WS = re.compile(r"[ \t ]+")
_HYPHEN_BREAK = re.compile(r"(\w)-\s+(\w)")
_LEAFLET_HEADER = re.compile(
    r"^informaci[oó]n para padres$|^informaci[oó]n para (madres|padres) y (padres|madres)$", re.I
)
_PAGE_NUM = re.compile(r"^\s*(página\s+)?\d{1,3}(\s*/\s*\d{1,3})?\s*$", re.I)
_DIGITOS = re.compile(r"\d+")


def normalize_line(text: str) -> str:
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = _WS.sub(" ", text).strip()
    return text


def join_hyphenated(text: str) -> str:
    """'infec- ción' → 'infección' (only when the break is inside a word)."""
    return _HYPHEN_BREAK.sub(r"\1\2", text)


def _sin_numeros(texto: str) -> str:
    """El pie con su número de página sustituido por un hueco.

    25-sep-2026: «Calendario común de vacunación | Página 1 de 3» y su gemela de la página 2 son
    la misma línea con un dígito distinto, y comparando el texto tal cual parecían dos líneas
    vistas una sola vez cada una. Así, ninguna llegaba al umbral y las tres se quedaban dentro:
    la leyenda del calendario español acababa siendo el pasaje que ganaba CUALQUIER pregunta
    sobre una vacuna, con 232 palabras que no contestan nada.
    """
    return _DIGITOS.sub("#", texto)


def repeated_lines(ex: Extracted, min_pages: int = 3, ratio: float = 0.6) -> set[str]:
    """Lines that appear on ≥ ratio of pages (and ≥ min_pages) are headers/footers.

    Se cuentan con los números sustituidos, para que un pie numerado cuente como uno solo; lo
    que se devuelve son las líneas **tal y como estaban**, que es lo que el limpiador compara.
    """
    n_pages = len(ex.pages)
    if n_pages < min_pages:
        return set()
    c: Counter[str] = Counter()
    formas: dict[str, set[str]] = {}
    for p in ex.pages:
        vistas = {normalize_line(ln.text).lower() for ln in p.lines}
        for v in vistas:
            formas.setdefault(_sin_numeros(v), set()).add(v)
        c.update({_sin_numeros(v) for v in vistas})
    tope = max(min_pages, int(n_pages * ratio))
    return {
        original
        for patron, n in c.items()
        if n >= tope and len(patron) > 3
        for original in formas[patron]
    }


def clean(ex: Extracted) -> Extracted:
    noise = repeated_lines(ex)
    for p in ex.pages:
        kept: list[Line] = []
        for ln in p.lines:
            t = normalize_line(ln.text)
            if not t or _PAGE_NUM.match(t) or _LEAFLET_HEADER.match(t) or t.lower() in noise:
                continue
            kept.append(Line(text=t, size=ln.size, bold=ln.bold, page=ln.page))
        p.lines = kept
    return ex
