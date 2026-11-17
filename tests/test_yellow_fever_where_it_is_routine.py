"""La fiebre amarilla, donde es vacuna de todos los niños (17-nov-2026).

Muso Health, que trabaja con agentes de salud comunitarios en Malí, contestó a la petición de
revisar la ficha de Malí con su tabla: BCG, polio, pentavalente, neumococo, rotavirus, IPV,
sarampión, meningitis A… y fiebre amarilla, una dosis. Nosotros no la teníamos. Ni en Malí ni en
ningún otro país: el constructor de calendarios de la OMS la tiraba siempre, como si fuera sólo
de viajeros. En Malí, Nigeria, Ghana, Colombia o Perú es la de los 9-15 meses para todo niño, y
la OMS la tiene así, declarada por el propio país. La de viajeros cae por su población.
"""

from __future__ import annotations

import yaml

from pedibot.settings import ROOT


def _paises() -> dict:
    d = yaml.safe_load((ROOT / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    return d.get("countries", d)


def _edades_con_fa(pais: dict) -> list[float]:
    return [s["age"] for s in pais["schedule"] if "Yellow fever" in s["vaccines"]]


def test_mali_gives_yellow_fever_at_nine_months() -> None:
    assert _edades_con_fa(_paises()["ML"]) == [9]


def test_the_big_endemic_countries_have_it() -> None:
    p = _paises()
    for c in ("NG", "GH", "CM", "CD", "SN", "UG", "CO", "PE"):
        assert _edades_con_fa(p[c]), c


def test_countries_without_yellow_fever_still_have_none() -> None:
    p = _paises()
    for c in ("ES", "GB", "IN", "KE", "ZA", "MA", "SA"):
        if c in p:
            assert not _edades_con_fa(p[c]), c


def test_the_script_no_longer_drops_it_but_drops_travellers() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_who_schedules as b

    assert "YF" not in b.VACUNAS_FUERA
    assert "YF" in b.NOMBRES
    assert "TRAVELLERS" in b.POBLACION_FUERA
