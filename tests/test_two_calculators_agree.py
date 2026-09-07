"""Las dos calculadoras de dosis tienen que decir lo mismo (7-sep-2026).

PediBot calcula la dosis **dos veces**, con dos códigos distintos:

  · el chat, el API y Telegram → `src/pedibot/bot/dose.py`, con las constantes escritas a mano;
  · las páginas de la web       → `web/site/src/dosepages.ts`, que las lee de `config/drugs.yaml`.

Dos fuentes para el mismo número es el patrón del clon podrido, y aquí el número **es una
instrucción**: cuántos mililitros se le dan a un niño. Si se separan, un padre puede leer una cosa
en la página y otra en el chat, y ninguna de las dos avisaría de nada.

Al compararlas por primera vez la aritmética coincidía **exactamente** —0 desacuerdos en 216
comparaciones, peso a peso y bote a bote—, pero las presentaciones no: el chat conocía tres
concentraciones de paracetamol y el catálogo siete. Quien tuviera gotas de 200 mg/ml (la
presentación brasileña, que está en el catálogo y tiene su página) **no veía su bote en la lista**,
y si cogía por error la línea de las de 100 mg/ml se pasaba al doble.

Este fichero no lee el TypeScript: reproduce su aritmética, que está a la vista en
`weightTable()`, y la compara contra el motor de Python sobre todo el rango de pesos. Lo que
comprueba no es que un código sea correcto, sino que **los dos dicen lo mismo** — que es lo que un
padre necesita.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from pedibot.bot.dose import DRUGS, calculate

RAIZ = pathlib.Path(__file__).resolve().parents[1]
CATALOGO = yaml.safe_load((RAIZ / "config" / "drugs.yaml").read_text(encoding="utf-8"))["drugs"]

#: (clave en el motor, clave en el catálogo)
PAREJAS = [("paracetamol", "paracetamol"), ("ibuprofeno", "ibuprofen")]


@pytest.mark.parametrize(("clave", "en_catalogo"), PAREJAS)
def test_the_numbers_behind_the_dose_are_the_same_on_both_sides(clave: str, en_catalogo: str):
    """Banda, intervalos, topes y mínimos. Si uno se mueve sin el otro, las dos calculadoras
    empiezan a dar dosis distintas sin que nada falle."""
    d, y = DRUGS[clave], CATALOGO[en_catalogo]
    assert [d.mg_per_kg_min, d.mg_per_kg_max] == y["per_dose_mg_per_kg"]
    assert list(d.interval_hours) == y["interval_hours"]
    assert d.max_mg_per_kg_day == y["max_mg_per_kg_day"]
    assert d.max_single_dose_mg == y["max_single_mg"]
    assert d.max_daily_mg == y["max_daily_mg"]
    assert d.min_age_months == y["min_age_months"]
    assert d.min_weight_kg == y["min_weight_kg"]


@pytest.mark.parametrize(("clave", "en_catalogo"), PAREJAS)
def test_the_chat_knows_every_bottle_the_site_lists(clave: str, en_catalogo: str):
    """El fallo que dio origen a este fichero. Un padre tiene que encontrar SU bote."""
    del_motor = sorted(p.mg_per_ml for p in DRUGS[clave].presentations)
    del_catalogo = sorted(float(x) for x in CATALOGO[en_catalogo]["strengths_mg_per_ml"])
    faltan = sorted(set(del_catalogo) - set(del_motor))
    assert not faltan, (
        f"el chat no sabe dar mililitros para {faltan} mg/ml, y la web sí los ofrece. "
        "Quien tenga ese bote no se ve en la lista — y coger otra línea cambia el volumen."
    )


@pytest.mark.parametrize(("clave", "en_catalogo"), PAREJAS)
def test_both_calculators_give_the_same_millilitres(clave: str, en_catalogo: str):
    """La comprobación que da nombre al fichero, sobre los 36 pesos de la tabla de la web.

    La aritmética de `weightTable()` en dosepages.ts, reproducida tal cual:
        mg = min(hi * kg, max_single_mg)
        ml = floor(mg / mg_per_ml * 10) / 10     ← hacia abajo, nunca al más cercano
    """
    y = CATALOGO[en_catalogo]
    _lo, hi = y["per_dose_mg_per_kg"]
    desacuerdos = []
    for kg in range(5, 41):
        r = calculate(clave, float(kg))
        mg_web = min(hi * kg, y["max_single_mg"])
        for p in DRUGS[clave].presentations:
            ml_web = int((mg_web / p.mg_per_ml) * 10) / 10
            if abs(ml_web - r.ml[p.name]) > 1e-9:
                desacuerdos.append(f"{kg} kg, {p.name}: chat {r.ml[p.name]} vs web {ml_web}")
    assert not desacuerdos, "las dos calculadoras no dicen lo mismo:\n  " + "\n  ".join(
        desacuerdos[:10]
    )


@pytest.mark.parametrize(("clave", "en_catalogo"), PAREJAS)
def test_the_volume_never_sits_above_the_milligrams_it_came_from(clave: str, en_catalogo: str):
    """Las dos redondean **hacia abajo** a propósito, y por la misma razón escrita en los dos
    ficheros: redondear al más cercano puede subir el volumen por encima de los miligramos de los
    que sale, y esta es la única página donde un número es una instrucción."""
    for kg in range(5, 41):
        r = calculate(clave, float(kg))
        for p in DRUGS[clave].presentations:
            assert r.ml[p.name] * p.mg_per_ml <= r.mg + 1e-9, (
                f"{clave} {kg} kg {p.name}: {r.ml[p.name]} ml son "
                f"{r.ml[p.name] * p.mg_per_ml} mg, por encima de los {r.mg} mg calculados"
            )


def test_the_typescript_formula_is_still_the_one_mirrored_here() -> None:
    """El candado del candado, y el punto flojo de todo este fichero dicho en voz alta.

    Las comprobaciones de arriba **reproducen** la aritmética de `weightTable()` en Python: no
    ejecutan el TypeScript. Si alguien cambia la fórmula de la web, esta copia no se entera y el
    resto del fichero seguiría en verde comparando el motor contra una fórmula que ya no es la
    que corre en el navegador de nadie.

    Así que se ancla el texto. No es elegante, pero es honesto: si la fórmula cambia, esto falla
    y quien la cambie tiene que venir aquí y actualizar el espejo. Meter node en la suite para
    ejecutar el TypeScript de verdad sería más fuerte y también más frágil — la suite dejaría de
    correr sin `node_modules`.
    """
    ts = (RAIZ / "web" / "site" / "src" / "dosepages.ts").read_text(encoding="utf-8")
    espejadas = [
        # el miligramo del que sale todo: el techo de la banda, con el tope de dosis única
        "const mgMax = Math.min(hi * kg, m.d.max_single_mg);",
        "const mg = mgMax;",
        # hacia abajo, a la décima de mililitro
        "ml: m.forms.map((f) => String(Math.floor((mg / f.mg_per_ml) * 10) / 10)),",
        # el rango de pesos que la tabla cubre
        "for (let kg = 5; kg <= 40; kg++) {",
    ]
    faltan = [linea for linea in espejadas if linea not in ts]
    assert not faltan, (
        "la aritmética de dosepages.ts ha cambiado y el espejo de este fichero no:\n  "
        + "\n  ".join(faltan)
        + "\nActualiza test_two_calculators_agree.py antes de dar por buena la comparación."
    )
