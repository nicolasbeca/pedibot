"""Una cita no lleva dos idiomas dentro (20-sep-2026).

59 de los 66 calendarios terminaban su fuente así:

    …WIISE public dataset AD_SCHEDULES, 2025 reporting year (consultado el 18-09-2026)

Una cita en inglés con dos palabras en español, servida igual a un padre en hindi, en árabe y en
ruso. Llevaba semanas en pantalla y no la veía nadie, porque quien mira el fichero de
configuración lee las dos lenguas sin darse cuenta de que está leyendo dos.

La regla que queda: **la cita nombra un documento real y no se traduce**, porque traducirla es
inventarse un documento que no existe; **la coletilla es nuestra y se escribe en el idioma de
quien lee**, porque no está en la fuente, la ponemos nosotros.

Y la fecha, nunca en cifras. «09-18» y «18-09» son el mismo día y dos días distintos según quién
los mire, y esto es un calendario de vacunas.
"""

from __future__ import annotations

import datetime as dt
import re

import pytest
import yaml

from pedibot.bot.vaccines import Vaccines, fecha_comprobada, format_answer
from pedibot.settings import ROOT

IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")

#: Palabras nuestras que no pueden vivir dentro de una cita: son de una lengua concreta y la
#: cita se sirve a las ocho. La lista es corta y cerrada a propósito.
NUESTRAS = ("consultado el", "comprobado el", "checked on", "vérifié le", "geprüft am")


@pytest.fixture(scope="module")
def calendarios() -> dict:
    return yaml.safe_load((ROOT / "config" / "vaccines.yaml").read_text(encoding="utf-8"))[
        "countries"
    ]


def test_ninguna_cita_lleva_nuestra_coletilla_dentro(calendarios: dict) -> None:
    sucias = [
        f"{cc}: …{str(v['source'])[-60:]}"
        for cc, v in calendarios.items()
        if any(p in str(v["source"]).lower() for p in NUESTRAS)
    ]
    assert not sucias, "citas con una frase nuestra dentro:\n" + "\n".join(sucias)


def test_la_fecha_de_consulta_esta_en_su_campo_y_en_iso(calendarios: dict) -> None:
    """En ISO porque es el único formato que no se lee al revés en ningún país."""
    malas = []
    for cc, v in calendarios.items():
        iso = v.get("checked")
        if iso is None:
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(iso)):
            malas.append(f"{cc}: «{iso}» no es una fecha ISO")
            continue
        dia = dt.date.fromisoformat(str(iso))
        if dia > dt.date.today():
            malas.append(f"{cc}: comprobado el {iso}, que todavía no ha pasado")
    assert not malas, "\n".join(malas)


def test_la_mayoria_de_calendarios_dice_cuando_se_comprobo(calendarios: dict) -> None:
    """Los que no lo dicen son transcripciones a mano cuya fecha está dentro del documento."""
    con = [cc for cc, v in calendarios.items() if v.get("checked")]
    assert len(con) >= len(calendarios) - 10


@pytest.mark.parametrize("lang", IDIOMAS)
def test_cada_idioma_escribe_la_fecha_con_el_mes_en_letra(lang: str) -> None:
    """Con el mes escrito no hay forma de leer septiembre como el día dieciocho."""
    texto = fecha_comprobada({"checked": "2026-09-18"}, lang)
    assert texto, f"{lang} no escribe la fecha de consulta"
    assert "2026" in texto
    assert "18" in texto
    assert "09" not in texto, f"{lang} deja el mes en cifras: «{texto}»"


def test_el_calendario_de_kenia_lo_dice_en_las_ocho_lenguas() -> None:
    v = Vaccines(ROOT / "config" / "vaccines.yaml")
    for lang in IDIOMAS:
        respuesta = format_answer(v, "KE", 9, lang)
        assert "2026" in respuesta
        assert "consultado el 18-09" not in respuesta


def test_sin_fecha_no_se_inventa_nada() -> None:
    """Un calendario sin `checked` no gana un paréntesis vacío ni la fecha de hoy."""
    assert fecha_comprobada({}, "es") == ""
    assert fecha_comprobada({"checked": ""}, "es") == ""
    assert fecha_comprobada({"checked": "no es una fecha"}, "es") == ""
