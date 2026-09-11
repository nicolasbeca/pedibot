"""`pedibot doctor`: una orden que dice si la instalación está sana (11-sep-2026).

Cada fallo de esta sesión se descubrió por casualidad o por un candado que corre en el PC, y
ninguno de los dos sirve en el VPS a las 06:30. La lista de lo que se rompió sola es siempre la
misma familia: **una pieza deja de casar con otra y nada falla**.

- Cuatro documentos indexados sin entrada de catálogo, o sea sin licencia registrada (L131).
- Dos reglas de alarma citando un documento inexistente (L137).
- Las concentraciones del catálogo y las de la calculadora, separadas (L142).
- Cuatro países servidos sin número de emergencias.
- La cola de publicación vacía, con el timer corriendo cada mañana sin escribir nada (L126).

`doctor` junta esas comprobaciones en un sitio, las imprime en una pantalla y —lo que importa—
**sale con código distinto de cero cuando algo está mal**, que es lo que permite colgarlo de un
timer y que el operador se entere sin mirar.

Lo que este fichero fija: que exista, que sea rápido, que **compruebe todo lo que dice
comprobar** y que el código de salida no mienta.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

from pedibot.settings import ROOT

BASE = [sys.executable, "-m", "pedibot.cli", "doctor"]
ENTORNO = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(ROOT / "src")}


def corre(*args: str) -> tuple[int, str, float]:
    t0 = time.time()
    r = subprocess.run(
        [*BASE, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        cwd=ROOT,
        env=ENTORNO,
    )
    return r.returncode, (r.stdout or "") + (r.stderr or ""), time.time() - t0


#: Lo que tiene que mirar. La clave es un trozo de lo que imprime; el porqué, la lección.
COMPROBACIONES = {
    "índice": "existe y con cuántos documentos",
    "huérfanos": "indexado sin entrada de catálogo = sin licencia registrada (L131)",
    "alarmas": "toda regla cita un documento que existe (L137)",
    "dosis": "las concentraciones del catálogo y las de la calculadora coinciden (L142)",
    "emergencias": "todo país servido tiene número",
    "cola": "queda materia que publicar, o el timer es decorativo (L126)",
    "sitio": "está construido y de cuándo",
}


def test_doctor_existe_y_es_rapido():
    codigo, salida, seg = corre()
    assert "No such command" not in salida, "no hay orden `doctor`"
    assert seg < 90, f"tarda {seg:.0f} s; una revisión que se hace esperar no se corre"
    assert codigo in (0, 1), f"código raro {codigo}:\n{salida[-400:]}"


def test_mira_todo_lo_que_dice_mirar():
    _, salida, _ = corre()
    bajo = salida.lower()
    faltan = [k for k in COMPROBACIONES if k not in bajo]
    assert not faltan, (
        "la revisión no comprueba " + ", ".join(f"«{k}» ({COMPROBACIONES[k]})" for k in faltan)
    )


def test_en_esta_copia_esta_todo_bien():
    """Si aquí falla, es que algo está roto de verdad: es el sitio donde se mira."""
    codigo, salida, _ = corre()
    assert codigo == 0, f"la revisión encuentra problemas en esta copia:\n{salida}"


def test_el_codigo_de_salida_no_miente():
    """La única razón de existir: que un timer pueda colgarse de `$?`."""
    codigo, salida, _ = corre()
    malas = [x for x in salida.splitlines() if x.strip().startswith(("✗", "x "))]
    assert bool(malas) == (codigo != 0), (
        f"hay {len(malas)} líneas de fallo y el código es {codigo}:\n{salida}"
    )


def test_no_imprime_secretos():
    """Dice si hay clave, nunca cuál: esto se pega en un chat de operaciones."""
    _, salida, _ = corre()
    clave = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    if len(clave) > 8:
        assert clave not in salida, "la revisión imprime la clave del modelo"
    assert "sk-" not in salida, "hay algo con pinta de clave en la salida"


def test_y_cuando_algo_esta_roto_lo_dice_y_falla():
    """Una revisión que nunca ha fallado no está probada: se le rompe algo a propósito.

    Se apunta el índice a una ruta que no existe. Tiene que salir la línea de fallo Y el código
    de salida tiene que ser 1 — que es lo único por lo que esta orden existe.
    """
    entorno = {**ENTORNO, "INDEX_DB_PATH": "no/existe/de/verdad.db"}
    r = subprocess.run(
        BASE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        cwd=ROOT,
        env=entorno,
    )
    salida = (r.stdout or "") + (r.stderr or "")
    assert "✗" in salida, f"no avisa de que el índice no está: {salida}"
    assert r.returncode == 1, f"lo ve y sale con {r.returncode}: un timer no se enteraría"
