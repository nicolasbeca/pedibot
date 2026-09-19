"""Un fichero de guía en una dirección redirigida no sube al servidor (19-sep-2026).

El invariante ya lo vigilaba `test_the_old_addresses_still_work.py`, sobre esta copia. Lo que
faltaba era impedir que la copia se lo llevara al servidor: `deploy.sh --no-pull` manda lo local,
y lo local llevaba 61 guías que el servidor había retirado hacía semanas. Cada despliegue las
resucitaba. Nadie lo vio porque la redirección gana y el lector llega bien; lo que salió torcido
fue el recuento, 568 donde se podían abrir 507, y esa cifra ya estaba fuera.

Así que esto prueba la pieza que corre en el despliegue, no el invariante.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib


def _publicador():
    ruta = pathlib.Path(__file__).resolve().parents[1] / "ops" / "retire_dead_guides.py"
    spec = importlib.util.spec_from_file_location("retire_dead_guides", ruta)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _contenido(tmp_path: pathlib.Path) -> pathlib.Path:
    raiz = tmp_path / "web" / "content"
    (raiz / "en").mkdir(parents=True)
    (raiz / "fr").mkdir()
    (raiz / "en" / "vieja.md").write_text("topic: fiebre\n", encoding="utf-8")
    (raiz / "en" / "nueva.md").write_text("topic: fiebre\n", encoding="utf-8")
    (raiz / "fr" / "vieille.md").write_text("topic: fiebre\n", encoding="utf-8")
    (raiz / "_redirects.json").write_text(
        json.dumps({"/guides/vieja": "/guides/nueva", "/fr/guides/vieille": "/fr/guides/neuve"}),
        encoding="utf-8",
    )
    return raiz


def test_encuentra_las_que_redirigen_y_respeta_las_vivas(tmp_path: pathlib.Path) -> None:
    raiz = _contenido(tmp_path)
    nombres = sorted(p.name for p in _publicador().muertas(raiz))
    assert nombres == ["vieille.md", "vieja.md"]


def test_el_prefijo_de_idioma_cuenta(tmp_path: pathlib.Path) -> None:
    """El inglés va sin prefijo y las demás lenguas con él.

    Si se equivoca, o no retira nada, o retira la guía viva de otra lengua que se llama igual.
    """
    raiz = _contenido(tmp_path)
    (raiz / "fr" / "vieja.md").write_text("topic: fiebre\n", encoding="utf-8")
    muertas = {p.relative_to(raiz).as_posix() for p in _publicador().muertas(raiz)}
    assert muertas == {"en/vieja.md", "fr/vieille.md"}


def test_sin_fichero_de_redirecciones_no_retira_nada(tmp_path: pathlib.Path) -> None:
    raiz = _contenido(tmp_path)
    (raiz / "_redirects.json").unlink()
    assert _publicador().muertas(raiz) == []
