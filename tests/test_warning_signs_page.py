"""Las señales de alarma del chat, publicadas en una página por idioma (I-17, 29-sep-2026).

Hasta hoy las 96 reglas sólo se veían cuando saltaban; /emergency enseña las 34 de la hoja de la
SEUP. La página nueva las enseña todas, por síntoma y con su fuente. Nada se redacta: el texto es
el motivo de cada regla, el mismo que sale en el chat. Lo que se vigila aquí es que no se quede
ninguna fuera, que ninguna esté dos veces y que cada una diga de dónde sale.
"""

from __future__ import annotations

import json

import yaml

from pedibot.settings import ROOT

LANGS = ("es", "en", "fr", "de", "ru", "ar", "pt", "hi")
CONFIG = ROOT / "config"


def _reglas() -> list[dict]:
    return yaml.safe_load((CONFIG / "red_flags.yaml").read_text(encoding="utf-8"))["rules"]


def _grupos() -> dict:
    return yaml.safe_load((CONFIG / "warning_signs.yaml").read_text(encoding="utf-8"))


def test_cada_regla_esta_en_un_grupo_y_solo_en_uno():
    ids = [r["id"] for r in _reglas()]
    puestas = [i for lista in _grupos()["rules"].values() for i in lista]
    assert sorted(set(ids) - set(puestas)) == [], "reglas sin grupo en config/warning_signs.yaml"
    assert sorted(set(puestas) - set(ids)) == [], "grupos con reglas que ya no existen"
    repetidas = sorted({i for i in puestas if puestas.count(i) > 1})
    assert repetidas == [], f"reglas en dos grupos: {repetidas}"


def test_cada_grupo_tiene_nombre_en_las_ocho_lenguas():
    g = _grupos()
    assert set(g["rules"]) == set(g["categories"])
    for cat, nombres in g["categories"].items():
        assert all(nombres.get(lang) for lang in LANGS), cat


def test_el_dato_exportado_lleva_todas_con_su_fuente():
    datos = json.loads(
        (ROOT / "web" / "site" / "src" / "data" / "warning_signs.json").read_text(encoding="utf-8")
    )
    senales = [s for grupo in datos["groups"] for s in grupo["signs"]]
    assert len(senales) == len(_reglas())
    for s in senales:
        assert all(s["reason"].get(lang) for lang in LANGS), s["id"]
        assert s["source"]["title"] and s["source"]["org"], f"{s['id']} sin fuente"


def test_la_pagina_construida_existe_en_las_ocho_lenguas():
    dist = ROOT / "web" / "site" / "dist"
    if not dist.exists():
        return
    for lang in LANGS:
        ruta = dist / ("" if lang == "en" else lang) / "warning-signs" / "index.html"
        assert ruta.exists(), ruta
        html = ruta.read_text(encoding="utf-8")
        assert html.count('class="sign ') == len(_reglas()), lang


def test_se_llega_desde_el_menu_el_pie_y_el_chat():
    """«Que no se te escapen estos detalles» (el operador, 29-sep-2026): una página a la que no
    se llega desde donde está el padre no existe para él."""
    src = ROOT / "web" / "site" / "src"
    base = (src / "layouts" / "Base.astro").read_text(encoding="utf-8")
    chat = (src / "components" / "Chat.astro").read_text(encoding="utf-8")
    assert base.count("/warning-signs") >= 2, "falta en el desplegable o en el pie"
    assert "/warning-signs" in chat, "falta bajo el cuadro del chat"
    for herramienta in ("/guides", "/dose", "/emergency"):
        assert herramienta in chat.split('class="legal"', 1)[1][:900], herramienta
