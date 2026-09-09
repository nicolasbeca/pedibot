"""Los temas de temporada tienen que existir (9-sep-2026).

`config/seasonal.yaml` dice qué asuntos priorizar cada mes —bronquiolitis en enero, golpe de
calor en julio— y `publish/articles.py` los usa para ordenar qué guía se escribe antes. Si un
nombre está mal escrito o se renombra el tema, la entrada **no hace nada y no avisa**: el fichero
sigue diciendo «en enero, la laringitis» y el generador sigue publicando por orden alfabético.

Había dos así, `croup` y `ors_hydration`, que no existían en `TOPIC_PLAN`. Ninguno perdía nada
—en cada mes donde aparecían estaba ya el tema real— pero llevaban ahí desde el principio sin
que nadie lo supiera, que es el problema de fondo.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from pedibot.publish.articles import TOPIC_PLAN

RAIZ = pathlib.Path(__file__).resolve().parents[1]
MESES = yaml.safe_load((RAIZ / "config" / "seasonal.yaml").read_text(encoding="utf-8"))["north"]


def test_there_are_twelve_months() -> None:
    assert sorted(int(m) for m in MESES) == list(range(1, 13))


@pytest.mark.parametrize("mes", sorted(MESES, key=int))
def test_every_seasonal_topic_exists_in_the_plan(mes: str) -> None:
    fantasma = [t for t in MESES[mes] if t not in TOPIC_PLAN]
    assert not fantasma, (
        f"mes {mes}: temas que no existen en TOPIC_PLAN y que el ordenador ignora en "
        f"silencio: {fantasma}"
    )


@pytest.mark.parametrize("mes", sorted(MESES, key=int))
def test_no_month_is_left_empty(mes: str) -> None:
    assert len(MESES[mes]) >= 4, f"mes {mes} se ha quedado con {len(MESES[mes])} temas"
