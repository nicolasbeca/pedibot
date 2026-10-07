"""Los Ratgeber del RKI son para médicos (5-oct-2026).

Estaban catalogados como hoja para padres, y en alemán ganaban por la lengua: a «mein Baby
erbricht seit heute Morgen zweimal» le llegaban el norovirus, la salmonela y la EHEC del RKI en vez
de la página del NHS sobre vómitos. «RKI-Ratgeber für Ärztinnen und Ärzte» dice su propia
colección. Catalogados como lo que son, de 89 preguntas en alemán cambian 16, casi todas a mejor.
"""

from __future__ import annotations

import pathlib

import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def test_los_ratgeber_no_son_hojas_para_padres() -> None:
    fuentes = yaml.safe_load((RAIZ / "config" / "fuentes_web.yaml").read_text(encoding="utf-8"))
    lista = fuentes["sources"] if isinstance(fuentes, dict) else fuentes
    rki = [f for f in lista if str(f.get("doc_id", "")).startswith("rki_de_")]
    assert len(rki) >= 30
    assert all(f["doc_type"] == "guia_clinica" for f in rki)


def test_y_pesan_menos_que_una_pagina_para_padres() -> None:
    """7-oct-2026: aun como guía clínica ganaban en alemán sólo por la lengua («Husten seit einer
    Woche» → tos ferina, tuberculosis, VRS y covid). Con 0,6, de 81 preguntas en alemán cambian 16,
    casi todas a la página para padres (vómitos de la SEUP, crup y VRS del NHS)."""
    from pedibot.index.store import ORG_WEIGHT

    assert ORG_WEIGHT["RKI"] < 1
