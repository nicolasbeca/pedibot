"""La tarjeta del catálogo se genera, no se escribe (28-sep-2026).

Había dos ficheros contando lo mismo: `dataset/README.md`, generado, con las estadísticas por
organización, idioma y tema; y `dataset/HUGGINGFACE.md`, escrito a mano, con la cabecera YAML que
Hugging Face necesita para las etiquetas y la tabla navegable. Subir el dataset pedía renombrar
el segundo a `README.md` —un paso que sólo falla en silencio: la página sale vacía— y mantener a
mano unas cifras que el primero ya contaba solo. Duró cuatro días y en ese tiempo el guion ya
decía 645 documentos cuando eran 632.

Ahora el generador escribe la cabecera, así que el fichero que se sube es el que se genera.
"""

from __future__ import annotations

import pathlib

import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TARJETA = RAIZ / "dataset" / "README.md"


def _cabecera() -> dict:
    t = TARJETA.read_text(encoding="utf-8")
    assert t.startswith("---\n"), "sin cabecera YAML, Hugging Face no pone ninguna etiqueta"
    fin = t.index("\n---\n", 3)
    return yaml.safe_load(t[4:fin])


def test_the_generated_card_carries_its_header() -> None:
    d = _cabecera()
    assert d["license"] == "cc0-1.0", d.get("license")
    assert len(d["language"]) == 8, d.get("language")
    assert d["configs"][0]["data_files"] == "sources.csv", d.get("configs")
    assert "paediatrics" in d["tags"]


def test_the_numbers_in_the_card_are_the_ones_counted() -> None:
    """Y las cifras del texto son las del catálogo, porque las escribe el mismo guion."""
    import json

    docs = json.loads((RAIZ / "dataset" / "sources.json").read_text(encoding="utf-8"))
    texto = TARJETA.read_text(encoding="utf-8")
    assert f"**{len(docs)} documents" in texto, f"la tarjeta no dice {len(docs)}"
    assert f"{len({d['org'] for d in docs})} organisations" in texto


def test_there_is_no_second_card_to_keep_in_sync() -> None:
    otra = RAIZ / "dataset" / "HUGGINGFACE.md"
    assert not otra.exists(), (
        "dos ficheros con la misma tarjeta se desincronizan: el que se sube es el generado"
    )
