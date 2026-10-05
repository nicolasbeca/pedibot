"""El panel abre en el momento (5-oct-2026).

El operador: «cuando entro en la página de admin tarda muchísimo». Medido en el servidor: 13 a
15 segundos por apertura, y **todo** en `web_visits`, que leía con `journalctl` el registro de
Caddy entero (274 MB, 261.000 líneas: 8,5 s de lectura y 6 de recuento). Las consultas, las
guías y lo demás tardan centésimas.

Y el temporizador `pedibot-stats` ya hacía esa misma lectura cada hora. Ahora deja el resultado
en un fichero y el panel lo lee. «No tengo que tener el dato en tiempo real, pero cuando entro
quiero verlo rápido»: si el fichero se queda viejo se enseña igual, con su hora, y no se vuelve
a leer el registro con el operador esperando. Las 24 horas sí se cuentan al momento: son 3.600
líneas y 0,14 s.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from pedibot import admin
from pedibot.ops import report
from pedibot.ops.store import OpsStore


def _visitas(**cambios) -> dict:
    w = report.count_visits([])
    w.update(cambios)
    return w


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "web_visits.json"
    monkeypatch.setattr(admin, "visits_cache_path", lambda: path)
    return path


def _render(tmp_path: Path, days: int) -> str:
    return admin.render(OpsStore(tmp_path / "ops.db", salt="s").con, days)


def _prohibido(days: int) -> dict:
    raise AssertionError(f"el panel volvió a leer el registro entero (days={days})")


def test_lo_guardado_vuelve_igual(cache: Path):
    w = _visitas(visitors=7, top=[("/vaccines", 3)], covers=("2026-08-25", "2026-10-05"))
    report.save_visits(w, cache)
    leido = report.load_visits(cache)
    assert leido is not None
    assert leido["visitors"] == 7
    assert [tuple(t) for t in leido["top"]] == [("/vaccines", 3)]
    assert tuple(leido["covers"]) == ("2026-08-25", "2026-10-05")
    assert "read_at" in leido


def test_sin_fichero_no_hay_nada(tmp_path: Path):
    assert report.load_visits(tmp_path / "no.json") is None


def test_el_total_sale_del_fichero(cache: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    report.save_visits(_visitas(visitors=4321, covers=("2026-08-25", "2026-10-05")), cache)
    monkeypatch.setattr(report, "web_visits", _prohibido)
    assert "4321" in _render(tmp_path, 0)


def test_noventa_dias_tambien_si_el_registro_no_llega(
    cache: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """El operador entra con `?days=90` guardado; el registro cubre 41 días. Es la misma cifra."""
    report.save_visits(_visitas(visitors=4321, covers=("2026-08-25", "2026-10-05")), cache)
    monkeypatch.setattr(report, "web_visits", _prohibido)
    assert "4321" in _render(tmp_path, 90)


def test_las_24_horas_al_momento(cache: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    report.save_visits(_visitas(visitors=4321, covers=("2026-08-25", "2026-10-05")), cache)
    pedidos: list[int] = []
    monkeypatch.setattr(report, "web_visits", lambda days: pedidos.append(days) or _visitas())
    _render(tmp_path, 1)
    assert pedidos == [1]


def test_viejo_se_enseña_con_su_hora(cache: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    report.save_visits(_visitas(visitors=4321, covers=("2026-08-25", "2026-10-05")), cache)
    leido = report.load_visits(cache)
    assert leido is not None
    hace = dt.datetime.now(dt.UTC) - dt.timedelta(hours=5)
    leido["read_at"] = hace.isoformat(timespec="seconds")
    report.save_visits(leido, cache, read_at=leido["read_at"])
    monkeypatch.setattr(report, "web_visits", _prohibido)
    html = _render(tmp_path, 0)
    assert "4321" in html
    assert "hace 5 h" in html


def test_reciente_dice_cuantos_minutos(
    cache: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    report.save_visits(_visitas(visitors=4321, covers=("2026-08-25", "2026-10-05")), cache)
    monkeypatch.setattr(report, "web_visits", _prohibido)
    assert "hace 0 min" in _render(tmp_path, 0)


def test_sin_fichero_se_cuenta_como_antes(
    cache: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """La primera vez tras desplegar, antes de que corra el temporizador."""
    monkeypatch.setattr(report, "web_visits", lambda days: _visitas(visitors=99))
    assert "99" in _render(tmp_path, 0)


def test_el_temporizador_lo_deja_escrito():
    from pedibot.settings import ROOT

    fuente = (ROOT / "ops" / "publish_stats.py").read_text(encoding="utf-8")
    assert "save_visits(" in fuente
