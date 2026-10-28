"""El VPH de República Dominicana, corregido con lo que vio Frank Brightwell (28-oct-2026).

Frank (Somos Amigos Medical Missions, clínica en la República Dominicana rural) revisó con su
equipo clínico las páginas del país y encontró una cosa desfasada: el fichero de la OMS (WIISE,
año 2025) aún decía «VPH tetravalente (niñas)». Desde el 11-mar-2026 el Ministerio de Salud
Pública pone la **nonavalente**, gratis, a **niñas y niños de 9 a 14 años**, en **una sola
dosis** (dos sólo para inmunocomprometidos). Lo dicen el anuncio del ministro Víctor Atallah y la
prensa dominicana que lo recoge (Listín Diario, 10-mar-2026; El Caribe; El Nacional).

Se fija aquí para que una recarga del fichero de la OMS no devuelva el «sólo niñas»: a un padre
de un niño de 10 años le diría que a su hijo no le toca.
"""

from __future__ import annotations

import pathlib

import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DO = yaml.safe_load((RAIZ / "config" / "vaccines.yaml").read_text(encoding="utf-8"))[
    "countries"
]["DO"]
NOMBRES = yaml.safe_load((RAIZ / "config" / "vaccine_names.yaml").read_text(encoding="utf-8"))[
    "names"
]
LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


def _vph():
    return [v for fila in DO["schedule"] for v in fila["vaccines"] if "HPV" in v]


def test_el_vph_es_nonavalente_y_para_ninos_tambien():
    assert _vph() == ["HPV, 9-valent (girls and boys, 1 dose)"]


def test_ya_no_dice_solo_ninas():
    assert not any("girls)" in v for v in _vph())


def test_el_nombre_nuevo_existe_en_las_ocho_lenguas():
    nombre = NOMBRES.get("HPV, 9-valent (girls and boys, 1 dose)") or {}
    assert set(LANGS) <= set(nombre)


def test_la_nota_cuenta_el_cambio_en_las_ocho_lenguas():
    for lang in LANGS:
        assert "2026" in DO["note"][lang], lang
