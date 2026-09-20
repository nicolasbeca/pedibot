"""La nota de urgencias, en el idioma del que lee (20-sep-2026).

Veinticinco países llevan una nota debajo de su número, y es la frase más consecuente de toda la
página: dice si va a venir alguien o si hay que buscarse la vida. «Fuera de Cotonú puede que no
acuda nadie; lo más probable es que tengas que organizar tú el transporte». Estaban en inglés y
salían así dentro de respuestas en español, en árabe y en hindi. **Veintitrés de las veinticinco
son de países africanos**, que es a donde va este proyecto.

A diferencia de la cita —que nombra un documento y no se traduce— esto sí se traduce: es un
resumen nuestro de lo que dice la fuente, escrito por nosotros.

De paso salió un error de datos que llevaba ahí desde que se transcribió: la nota de **Sudán del
Sur** hablaba de Sudán. Con Sudán ahora también en la tabla, esa nota decía la verdad sobre el
país de al lado.
"""

from __future__ import annotations

import pytest
import yaml

from pedibot.bot.emergency_question import format_numbers
from pedibot.settings import ROOT

IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


@pytest.fixture(scope="module")
def tabla() -> dict:
    return yaml.safe_load((ROOT / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8"))


def test_ninguna_nota_se_queda_en_un_solo_idioma(tabla: dict) -> None:
    sueltas = [
        cc
        for cc, v in tabla.items()
        if cc != "default" and isinstance(v, dict) and isinstance(v.get("note"), str)
    ]
    assert not sueltas, f"notas en una sola lengua, que saldrá en las ocho: {sueltas}"


def test_ninguna_nota_se_deja_una_lengua(tabla: dict) -> None:
    """A una nota sin hindi no le pasa nada visible: cae al inglés y nadie se entera."""
    incompletas = {
        cc: sorted(set(IDIOMAS) - set(v["note"]))
        for cc, v in tabla.items()
        if cc != "default" and isinstance(v, dict) and isinstance(v.get("note"), dict)
        if set(IDIOMAS) - set(v["note"])
    }
    assert not incompletas, f"notas a las que les falta alguna lengua: {incompletas}"


def test_los_numeros_de_la_nota_no_se_traducen(tabla: dict) -> None:
    """«Llama al 80093030121» tiene que decir lo mismo en las ocho: un número no es una palabra."""
    import re

    fallos = []
    for cc, v in tabla.items():
        if cc == "default" or not isinstance(v, dict) or not isinstance(v.get("note"), dict):
            continue
        cifras = {lg: sorted(re.findall(r"\d{3,}", texto)) for lg, texto in v["note"].items()}
        base = cifras["en"]
        for lg, suyas in cifras.items():
            if suyas != base:
                fallos.append(f"{cc}/{lg}: {suyas} ≠ {base}")
    assert not fallos, "\n".join(fallos)


def test_la_nota_de_sudan_del_sur_habla_de_sudan_del_sur(tabla: dict) -> None:
    """Decía «Sudan does not have…» bajo SS. Con Sudán en la tabla desde hoy, eso ya no es un
    descuido de redacción: es una frase verdadera sobre el país equivocado."""
    nota = tabla["SS"]["note"]["en"]
    assert nota.startswith("South Sudan"), nota
    assert tabla["SD"]["note"]["en"] != nota


@pytest.mark.parametrize("lang", IDIOMAS)
def test_la_respuesta_elige_la_nota_de_su_lengua(tabla: dict, lang: str) -> None:
    datos = dict(tabla["NG"])
    texto = format_numbers(datos, "Nigeria", lang)
    assert datos["note"][lang] in texto
    for otro in IDIOMAS:
        if otro != lang and datos["note"][otro] != datos["note"][lang]:
            assert datos["note"][otro] not in texto


def test_una_nota_que_siguiera_siendo_una_cadena_no_rompe_nada() -> None:
    """Por si alguien añade un país deprisa: sale en inglés, pero sale."""
    texto = format_numbers({"emergency": "112", "note": "Only in English"}, "Nowhere", "es")
    assert "Only in English" in texto
