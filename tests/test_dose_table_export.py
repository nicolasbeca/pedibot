"""La tabla de dosis de la portada no puede desviarse de la calculadora (11-sep-2026).

La portada lleva un deslizador de peso. Había tres formas de moverlo y dos eran malas:

- **Llamar a `/api/dose` en cada cambio**: el límite es de 20 peticiones por IP cada diez minutos,
  así que un padre jugando con el deslizador se quedaría sin poder preguntar después.
- **Calcularlo en JavaScript**: sería una **segunda implementación de un cálculo clínico**. La
  regla del proyecto es que las dosis salen de tablas fijas y el modelo no multiplica nunca; que
  no multiplique el modelo y sí el navegador no arregla nada, sólo mueve el problema.

Así que la tabla la genera Python con `bot.dose.calculate` y el navegador únicamente consulta.
Esto vigila lo único que puede romperse: que el fichero publicado **siga diciendo lo mismo que la
calculadora**. Si alguien toca `config/drugs.yaml` y no vuelve a exportar, la portada enseñaría
una dosis vieja con toda la confianza del mundo, y esto lo para.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from pedibot.bot.dose import calculate

ROOT = pathlib.Path(__file__).resolve().parents[1]
FICHERO = ROOT / "web" / "site" / "src" / "data" / "dose_table.json"


@pytest.fixture(scope="module")
def tabla() -> dict:
    if not FICHERO.exists():
        pytest.skip("sin dose_table.json en esta copia: hay que ejecutar scripts/export_catalog.py")
    return json.loads(FICHERO.read_text(encoding="utf-8"))


def test_cada_fila_es_la_que_da_la_calculadora(tabla: dict):
    malas = []
    for kg, fila in tabla["rows"].items():
        r = calculate(tabla["drug"], float(kg), None)
        if r.mg != fila["mg"] or r.refer != fila["refer"]:
            malas.append((kg, fila["mg"], r.mg))
            continue
        for pres, ml in fila["ml"].items():
            if r.ml.get(pres) != ml:
                malas.append((kg, pres, ml, r.ml.get(pres)))
    assert not malas, (
        "la tabla publicada ya no dice lo mismo que la calculadora; hay que reexportar "
        f"(scripts/export_catalog.py): {malas[:5]}"
    )


def test_solo_lleva_el_farmaco_que_se_puede_dar_sin_saber_la_edad(tabla: dict):
    """Sin edad, el ibuprofeno devuelve `refer` y no una cifra. Un deslizador de peso no sabe la
    edad, así que si alguna vez entra aquí, esto lo para antes de que salga a la portada."""
    assert tabla["drug"] == "paracetamol"
    r = calculate("ibuprofen", 14.0, None)
    assert r.refer, "si esto cambia, replantear si el ibuprofeno puede ir en la portada"


def test_ninguna_fila_publicada_pide_ir_al_medico_sin_decirlo(tabla: dict):
    """Una fila con `refer` es una que NO debe enseñar cifra. Si aparece alguna, el componente
    tiene que saber tratarla; hoy no hay ninguna y esto avisa el día que la haya."""
    con_refer = [kg for kg, f in tabla["rows"].items() if f["refer"]]
    assert not con_refer, (
        f"pesos que la calculadora deriva al médico y la tabla publica: {con_refer}"
    )


def test_dice_de_donde_sale_y_cada_cuanto(tabla: dict):
    assert "AEPap" in tabla["source"]
    assert tabla["interval_hours"] == [4, 6]
    assert len(tabla["rows"]) > 50, "de 4 a 40 kg en pasos de medio kilo"
