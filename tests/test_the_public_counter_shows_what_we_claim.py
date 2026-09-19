"""El contador público enseña lo que decimos por ahí que enseña (19-sep-2026).

La solicitud de MetaDAO dice, en la respuesta de tracción, «las cifras de uso están publicadas en
https://pedibot.xyz/api/stats». Quien abría esa dirección veía dos respuestas del chat en siete
días, que es verdad y es la peor mitad de la verdad: el chat es una herramienta de siete, y lo
que la gente abre son los calendarios, las urgencias y las curvas, donde no se pregunta nada.

Enseñar una cifra cierta de forma que parezca que escondes el resto cuesta más credibilidad que
no enseñar nada, y este proyecto no tiene otra cosa que su credibilidad. Así que el endpoint
sirve también las visitas, que calcula aparte `ops/publish_stats.py` porque leer el registro de
Caddy tarda demasiado para una petición pública.
"""

from __future__ import annotations

import json


def test_sirve_las_visitas_cuando_estan_publicadas(app_con_familia, tmp_path, monkeypatch) -> None:
    from pedibot import api as api_mod

    publicado = tmp_path / "data" / "public_stats.json"
    publicado.parent.mkdir(parents=True)
    publicado.write_text(
        json.dumps({"site": {"visitors": 337, "views": 1943, "covers": ["2026-08-25"]}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(api_mod, "ROOT", tmp_path)

    datos = app_con_familia.get("/api/stats").json()
    assert datos["site"]["visitors"] == 337
    assert datos["site"]["views"] == 1943
    # y sin perder lo del chat, que es lo que ya servía
    assert "answers" in datos


def test_sin_fichero_sigue_sirviendo_lo_de_siempre(app_con_familia, tmp_path, monkeypatch) -> None:
    """En una copia recién clonada no hay registro de Caddy que leer, y eso no puede tumbar nada."""
    from pedibot import api as api_mod

    monkeypatch.setattr(api_mod, "ROOT", tmp_path)
    r = app_con_familia.get("/api/stats")
    assert r.status_code == 200
    assert "answers" in r.json()
    assert "site" not in r.json()


def test_el_publicador_aguanta_no_poder_leer_el_registro(tmp_path, monkeypatch) -> None:
    """Sin `journalctl` (en el PC del operador, por ejemplo) escribe ceros, no revienta.

    Importa que no reviente y importa que no invente: un cero es una cifra que se puede leer y
    corregir; una excepción a mitad deja el fichero anterior en su sitio diciendo lo de ayer.
    """
    import importlib.util
    import pathlib

    ruta = pathlib.Path(__file__).resolve().parents[1] / "ops" / "publish_stats.py"
    spec = importlib.util.spec_from_file_location("publish_stats", ruta)
    assert spec and spec.loader
    publicador = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publicador)

    datos = publicador.reunir()
    assert set(datos) == {"generated", "site", "chat_all_time"}
    assert datos["site"]["covers"] == []
    assert datos["site"]["visitors"] == 0
