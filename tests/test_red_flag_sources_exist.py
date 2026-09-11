"""Un aviso de alarma no puede citar un documento que no existe (11-sep-2026).

Cada regla de `red_flags.yaml` lleva un `source`: el documento del que sale ese criterio. Es la
mitad seria del aviso — lo que separa «ve a urgencias» de una opinión es la ficha que lo respalda.

Se descubrió escribiendo las cuatro reglas de mordedura de serpiente, rabia, dengue y tétanos:
dos de ellas citaban `who_en_snakebite-envenoming` y `who_en_dengue-and-severe-dengue`, con
guiones, y los documentos reales del catálogo son `who_en_snakebite_envenoming` y
`who_en_dengue_and_severe_dengue`, con guiones bajos. **Las 2.873 pruebas pasaron igual.** Nadie
comprobaba que la fuente citada existiera; el aviso habría salido al padre señalando a un
documento inexistente.

Es exactamente la regla de la casa —fuente o silencio— aplicada a la capa que más importa, la de
seguridad, que era justo donde no estaba puesta.
"""

from __future__ import annotations

import yaml

from pedibot.settings import ROOT


def _catalogo() -> set[str]:
    ids: set[str] = set()
    for f in ("fuentes.yaml", "fuentes_web.yaml"):
        datos = yaml.safe_load((ROOT / "config" / f).read_text(encoding="utf-8"))
        ids |= {d["doc_id"] for d in datos["sources"]}
    return ids


def _reglas() -> list[dict]:
    datos = yaml.safe_load((ROOT / "config" / "red_flags.yaml").read_text(encoding="utf-8"))
    return datos["rules"]


def test_toda_regla_dice_de_donde_sale():
    sin_fuente = sorted(r["id"] for r in _reglas() if not r.get("source"))
    assert not sin_fuente, f"reglas sin documento que las respalde: {sin_fuente}"


def test_toda_fuente_citada_esta_en_el_catalogo():
    ids = _catalogo()
    huerfanas = sorted(
        (r["id"], r["source"]) for r in _reglas() if r.get("source") and r["source"] not in ids
    )
    assert not huerfanas, (
        "estas reglas citan un documento que no está en el catálogo; el aviso saldría "
        f"señalando a algo que no existe: {huerfanas}"
    )
