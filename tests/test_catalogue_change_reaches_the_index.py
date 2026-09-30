"""Cambiar una fuente en el catálogo tiene que llegar al índice (30-sep-2026).

La ingesta decide «sin cambios» por el hash del FICHERO. Así que cambiar el tema, el título o la
licencia de una fuente en el catálogo no llegaba nunca a sus fragmentos: el 30-sep se le quitó
el tema «fiebre» a una página del NHS sobre termómetros (echaba a la ficha de tifoidea de una
pregunta en hindi) y el índice siguió diciendo «fiebre» hasta que se borraron sus fragmentos a
mano. Un catálogo que no manda sobre el índice es una cuenta atrás: tarde o temprano alguien
corrige una licencia y la cita sigue saliendo con la vieja.
"""

from __future__ import annotations

import json
import pathlib

import yaml

from pedibot.ingest.pipeline import run_ingest

HTML = """<!doctype html><html><head><title>Thermometers</title></head><body><main>
<h1>How to take your baby's temperature</h1>
<p>Use a digital thermometer under the arm. Hold your baby's arm gently against their side and
leave the thermometer in place for as long as the instructions say.</p>
<p>Ear thermometers can give misleading readings in young babies because their ear holes are
small. Forehead strips are not reliable either.</p>
</main></body></html>"""


def _catalogo(ruta: pathlib.Path, tema: str, titulo: str) -> None:
    ruta.write_text(
        yaml.safe_dump(
            {
                "sources": [
                    {
                        "doc_id": "nhs_en_thermo",
                        "file": "web/nhs_en_thermo.html",
                        "org": "NHS",
                        "title": titulo,
                        "year": 2025,
                        "lang": "en",
                        "topic": tema,
                        "doc_type": "hoja_padres",
                        "evidence": "organismo_publico",
                        "usage": "publico",
                        "age_groups": ["lactante"],
                        "url": "https://www.nhs.uk/x",
                    }
                ]
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def _primero(out: pathlib.Path) -> dict:
    return json.loads((out / "chunks" / "nhs_en_thermo.jsonl").read_text(encoding="utf-8").split("\n")[0])


def test_el_tema_nuevo_llega_a_los_fragmentos(tmp_path: pathlib.Path, config_dir) -> None:
    fuentes = tmp_path / "FUENTES"
    (fuentes / "web").mkdir(parents=True)
    (fuentes / "web" / "nhs_en_thermo.html").write_text(HTML, encoding="utf-8")
    cfg = tmp_path / "config"
    cfg.mkdir()
    cat = cfg / "fuentes.yaml"
    out = tmp_path / "index"

    _catalogo(cat, "fiebre", "Taking a temperature")
    run_ingest(fuentes, out, cat, config_dir / "taxonomia.yaml")
    assert _primero(out)["topic"] == "fiebre"

    _catalogo(cat, "general", "How to take your baby's temperature")
    reps = run_ingest(fuentes, out, cat, config_dir / "taxonomia.yaml")
    assert [r.status for r in reps] == ["ok"], "el catálogo cambió y se dio por «sin cambios»"
    primero = _primero(out)
    assert primero["topic"] == "general"
    assert primero["doc_title"] == "How to take your baby's temperature"


def test_sin_cambios_sigue_siendo_sin_cambios(tmp_path: pathlib.Path, config_dir) -> None:
    fuentes = tmp_path / "FUENTES"
    (fuentes / "web").mkdir(parents=True)
    (fuentes / "web" / "nhs_en_thermo.html").write_text(HTML, encoding="utf-8")
    cfg = tmp_path / "config"
    cfg.mkdir()
    cat = cfg / "fuentes.yaml"
    out = tmp_path / "index"
    _catalogo(cat, "general", "Taking a temperature")
    run_ingest(fuentes, out, cat, config_dir / "taxonomia.yaml")
    reps = run_ingest(fuentes, out, cat, config_dir / "taxonomia.yaml")
    assert [r.status for r in reps] == ["unchanged"]
