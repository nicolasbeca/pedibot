"""La calculadora tiene que ofrecer el bote que el padre tiene en la mano (11-sep-2026).

Las concentraciones viven **en dos sitios**: `config/drugs.yaml` (`strengths_mg_per_ml`, que es
lo que la web publica y lo que valida el catálogo) y una tupla escrita a mano en
`bot/dose.py`, con un comentario que dice «todas las del catálogo». Era verdad el 7 de
septiembre. Es el patrón del clon podrido que este proyecto ya tiene nombrado: se añade una
concentración en un lado, el otro no se entera y **nada falla** — simplemente el padre que tiene
ese bote no lo ve en la lista, y si coge por error la línea de al lado se pasa de dosis.

Lo destapó ampliar el catálogo a India y al mundo árabe: **125 mg/5 ml no estaba**. Es la
presentación estándar del jarabe de paracetamol infantil en India (Crocin, Dolo, Metacin,
Pyrigesic) y en Egipto (Cetal), o sea que un padre indio no podía seleccionar su propio bote.

La regla: las dos listas dicen lo mismo, en los dos sentidos. Una concentración que la web
publica y la calculadora no ofrece es un padre que no encuentra su bote; una que la calculadora
ofrece y el catálogo no conoce es una cifra sin respaldo.
"""

from __future__ import annotations

import pytest
import yaml

from pedibot.bot.dose import DRUGS
from pedibot.settings import ROOT

#: la clave del YAML → la clave de la calculadora
PAREJAS = {"paracetamol": "paracetamol", "ibuprofen": "ibuprofeno"}


def _catalogo() -> dict:
    return yaml.safe_load((ROOT / "config" / "drugs.yaml").read_text(encoding="utf-8"))["drugs"]


@pytest.mark.parametrize(("clave_yaml", "clave_calc"), sorted(PAREJAS.items()))
def test_la_calculadora_ofrece_todas_las_del_catalogo(clave_yaml: str, clave_calc: str):
    del_catalogo = {float(x) for x in _catalogo()[clave_yaml]["strengths_mg_per_ml"]}
    de_la_calculadora = {p.mg_per_ml for p in DRUGS[clave_calc].presentations}
    faltan = sorted(del_catalogo - de_la_calculadora)
    assert not faltan, (
        f"[{clave_yaml}] la web publica estas concentraciones y la calculadora no las ofrece, "
        f"así que ese padre no encuentra su bote: {faltan} mg/ml"
    )


@pytest.mark.parametrize(("clave_yaml", "clave_calc"), sorted(PAREJAS.items()))
def test_y_ninguna_de_su_cosecha(clave_yaml: str, clave_calc: str):
    del_catalogo = {float(x) for x in _catalogo()[clave_yaml]["strengths_mg_per_ml"]}
    de_la_calculadora = {p.mg_per_ml for p in DRUGS[clave_calc].presentations}
    sobran = sorted(de_la_calculadora - del_catalogo)
    assert not sobran, (
        f"[{clave_yaml}] la calculadora ofrece concentraciones que el catálogo no conoce, "
        f"así que no tienen fuente detrás: {sobran} mg/ml"
    )


def test_la_presentacion_india_se_puede_elegir():
    """125 mg/5 ml: el jarabe infantil más vendido de India, y el de Egipto."""
    ofrecidas = {p.mg_per_ml for p in DRUGS["paracetamol"].presentations}
    assert 25.0 in ofrecidas, "no se puede seleccionar 125 mg/5 ml, que es el bote indio"
