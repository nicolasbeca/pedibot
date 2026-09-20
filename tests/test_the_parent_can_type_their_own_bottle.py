"""El padre puede escribir lo que pone en su bote (20-sep-2026).

Hasta hoy la calculadora ofrecía nueve presentaciones y el padre elegía la suya. Si la suya no
estaba, cogía la que más se le parecía — y ése es exactamente el error que casi se comete con
las gotas de Etiopía: 100 mg/5 ml frente a 100 mg/ml, cinco veces
(`tests/test_the_ethiopian_drops.py`).

**No es un caso raro y no se arregla añadiendo países.** Un estudio de 2025 sobre las listas
nacionales de medicamentos esenciales —«Pediatric formulations in national essential medicines
lists»— cuenta **28 formulaciones distintas de paracetamol** repartidas por el mundo, y dice que
es el medicamento con más variedad de todos los que miraron. Perseguirlas una a una es una
carrera que se pierde: cada país que se añade deja a otro fuera.

Con el campo nuevo deja de importar cuántas tengamos en la lista. **El padre tiene el bote en la
mano y lo copia.** Y lo que se calcula con eso es sólo la conversión a mililitros: los
miligramos los sigue decidiendo el servidor a partir del peso, así que equivocarse tecleando
cambia el volumen, no la dosis.

La guarda es la misma idea que la de la cinta del brazo —«eso no parece el brazo de un niño»—:
fuera de 5 a 250 mg/ml no se da ninguna cifra, se le dice que mire si su bote pone mg por ml o
mg por 5 ml, que es justo la confusión de la que va todo esto.
"""

from __future__ import annotations

import re

import pytest

from pedibot.settings import ROOT

CALC = ROOT / "web" / "site" / "src" / "components" / "DoseCalc.astro"
I18N = ROOT / "web" / "site" / "src" / "i18n.ts"

CLAVES = (
    "dose_bottle",
    "dose_bottle_opt",
    "dose_bottle_per5",
    "dose_bottle_perml",
    "dose_bottle_pick",
    "dose_bottle_yours",
    "dose_bottle_odd",
)


@pytest.mark.parametrize("clave", CLAVES)
def test_el_campo_esta_en_las_ocho_lenguas(clave: str) -> None:
    """Una mejora de seguridad que sólo está en inglés no es una mejora de seguridad.

    Ocho, porque son las ocho del sitio: un padre en Adís Abeba lee inglés o árabe, y uno en
    Patna, hindi.
    """
    texto = I18N.read_text(encoding="utf-8")
    n = len(re.findall(rf"\b{clave}:", texto))
    assert n == 8, f"«{clave}» aparece {n} veces y tienen que ser 8"


def test_el_campo_existe_en_la_calculadora() -> None:
    t = CALC.read_text(encoding="utf-8")
    assert 'id="conc"' in t, "no hay campo para la concentración del bote"
    assert 'id="unit"' in t, "no hay selector de mg/ml frente a mg/5 ml"
    assert "dose_bottle_per5" in t and "dose_bottle_perml" in t


def test_no_hay_unidad_preseleccionada() -> None:
    """Lo más importante del campo, y es la corrección de mi primera versión.

    La primera traía «mg por 5 ml» ya puesto, porque es lo que pone la mayoría de los botes. Ahí
    estaba el fallo: un padre en España con Apiretal —100 mg por **ml**— escribe 100, no toca el
    desplegable porque ya viene puesto, y le salen 7,5 ml en vez de 1,5. **Cinco veces de más por
    no tocar nada**, que es exactamente lo que hace todo el mundo con un valor por defecto.

    Y con el número 100 no se puede adivinar cuál quiso decir: las dos lecturas existen de verdad
    —las gotas etíopes son 20 mg/ml y las españolas 100—. Así que elige él, y mientras no elija
    no se le enseña ninguna cifra.
    """
    t = CALC.read_text(encoding="utf-8")
    assert '<option value="" selected>{s.dose_bottle_pick}</option>' in t, (
        "la primera opción tiene que estar vacía y seleccionada"
    )
    opciones = re.findall(r'<option value="([15])">\{s\.(dose_bottle_per\w+)\}', t)
    assert opciones == [("5", "dose_bottle_per5"), ("1", "dose_bottle_perml")], opciones
    # `.value) || 5` y no sólo `|| 5`: lo segundo lo cazaba el comentario que explica por qué no
    # se hace, y una prueba que falla por su propia explicación no sirve para nada.
    assert ".value) || 5" not in t, (
        "un valor por defecto en el código es la misma sobredosis por otra puerta"
    )
    assert "conc > 0 && por > 0" in t, "sin unidad elegida no se calcula nada"


def test_hay_guarda_para_lo_que_no_parece_un_bote_infantil() -> None:
    """Sin ella, un 120 tecleado como «mg por ml» daría 1,2 ml donde tocan 6,2."""
    t = CALC.read_text(encoding="utf-8")
    assert "mgml < 5 || mgml > 250" in t, "falta la banda de plausibilidad"
    assert "S.odd" in t, "fuera de banda hay que decírselo, no dar una cifra"


def test_los_miligramos_no_los_calcula_el_navegador() -> None:
    """La regla 4 de CLAUDE.md: la dosis en mg sale de la tabla, nunca de aquí.

    Lo que el navegador hace con el dato del padre es una división para pasar a mililitros. Si
    algún día alguien calcula aquí los mg a partir del peso, esto tiene que saltar.
    """
    t = CALC.read_text(encoding="utf-8")
    assert "j.mg / mgml" in t, "los mililitros salen de los mg del servidor"
    assert not re.search(r"(kg|weight)\s*\*\s*\d", t), "aquí no se multiplica por el peso"
