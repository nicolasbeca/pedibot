"""El watchdog tiene que poder ver una avería del buscador (8-sep-2026).

Todo lo que vigilaba miraba NUESTRA infraestructura: el proceso, el saldo, el disco, las
unidades de systemd. Ninguna de esas preguntas es la que le importa a quien pregunta —si una
consulta funciona— y la diferencia costó cara: un «112» sin comillas en `synonyms.yaml` tuvo el
buscador devolviendo un 500 en inglés con `/api/health` en verde todo el tiempo, porque el
proceso estaba perfectamente en pie.

`selfcheck.revisa` recorre el camino de verdad —expansión, taxonomía, índice— con el modelo
desconectado, así que no cuesta nada y puede correr cada diez minutos.

Lo que se comprueba aquí no es que hoy vaya bien: es que **sabría verlo si fuera mal**. Un
vigilante que nunca ha detectado nada y un vigilante roto se leen igual.
"""

from __future__ import annotations

import pathlib
import shutil
import tempfile

import pytest

from pedibot.ops.selfcheck import PREGUNTAS, revisa
from pedibot.settings import get_settings

RAIZ = pathlib.Path(__file__).resolve().parents[1]
INDICE = RAIZ / "index" / "pedibot.db"

pytestmark = pytest.mark.skipif(
    not INDICE.exists(), reason="sin índice construido (make ingest)"
)


def test_every_supported_language_has_a_question() -> None:
    """Un idioma sin pregunta aquí es un idioma que el vigilante no mira."""
    from pedibot.bot.answer import SUPPORTED_LANGS

    cubiertos = {k.split("_")[0] for k in PREGUNTAS}
    faltan = sorted(set(SUPPORTED_LANGS) - cubiertos)
    assert not faltan, f"idiomas sin pregunta de vigilancia: {faltan}"


def test_it_says_nothing_when_everything_works() -> None:
    """La otra mitad: un vigilante que se queja siempre se acaba silenciando."""
    s = get_settings()
    assert revisa(s.index_db_path, s.config_dir) == []


def test_it_notices_a_missing_index() -> None:
    s = get_settings()
    fallos = revisa(RAIZ / "index" / "no_existe.db", s.config_dir)
    assert fallos and "no se puede ni construir" in fallos[0]


def test_it_notices_configuration_that_does_not_load() -> None:
    s = get_settings()
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        for n in ("synonyms.yaml", "drugs.yaml", "taxonomia.yaml"):
            shutil.copy(s.config_dir / n, tmp / n)
        (tmp / "taxonomia.yaml").write_text("esto: [no es\n  yaml valido", encoding="utf-8")
        fallos = revisa(s.index_db_path, tmp)
    assert fallos and "no se puede ni construir" in fallos[0]


def test_it_notices_a_language_left_without_a_bridge() -> None:
    """La avería silenciosa: el buscador funciona, no lanza nada, y una lengua deja de llegar al
    corpus. Es lo que le pasó al francés hasta hoy, y nadie lo habría visto nunca."""
    s = get_settings()
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        for n in ("synonyms.yaml", "drugs.yaml", "taxonomia.yaml"):
            shutil.copy(s.config_dir / n, tmp / n)
        (tmp / "synonyms.yaml").write_text("en: {}\n", encoding="utf-8")
        fallos = revisa(s.index_db_path, tmp)
    assert len(fallos) >= 3, f"solo vio {len(fallos)} idiomas sin fuentes"
    assert all("Sin fuentes" in f for f in fallos)
