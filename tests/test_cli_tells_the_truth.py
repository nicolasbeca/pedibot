"""La CLI tiene que decir la verdad con el código de salida y con lo que imprime (11-sep-2026).

Medidos los diecinueve comandos y sus caminos de error, uno por uno, en vez de leer el fichero.
Tres cosas estaban mal, y las tres son de la misma familia: **lo que la herramienta dice no es
lo que ha pasado**.

1. **`ingest` con una ruta que no existe fallaba los 422 documentos y salía con código 0.**
   Imprimía `ingest: {'error': 422}`, reconstruía el índice con los JSONL viejos y devolvía
   éxito. Cualquier automatismo que mire `$?` —y este proyecto tiene doce timers— habría dado
   la ingesta por buena. Es la L127 por el otro lado: allí conté un código de salida como si
   fuera un resultado; aquí el código de salida no cuenta el resultado.

2. **Un error del usuario salía como una traza de Python de veinte líneas.** `dose noexiste 14`
   escupía el `Traceback` con el código fuente pintado. El programa no está roto: le han pedido
   un fármaco que no existe, y eso se dice en una línea.

3. **La primera línea de casi todos los comandos era un aviso de PyMuPDF** («the `fitz` API is
   deprecated»), que no es del proyecto y tapa la línea que sí importa. Llevaba toda la sesión
   saliendo, y he estado filtrándolo a mano en cada medición en lugar de quitarlo.

Y faltaba lo más básico de una herramienta que se despliega: **`--version`**, para saber qué
código está corriendo de verdad.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from pedibot.settings import ROOT

BASE = [sys.executable, "-m", "pedibot.cli"]
ENTORNO = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(ROOT / "src")}


def corre(*args: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*BASE, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=ROOT,
        env=ENTORNO,
    )


def salida(r: subprocess.CompletedProcess[str]) -> str:
    return (r.stdout or "") + (r.stderr or "")


def test_hay_version():
    """Lo primero que se pregunta de algo desplegado: qué versión está corriendo."""
    r = corre("--version")
    assert r.returncode == 0, salida(r)
    assert any(c.isdigit() for c in salida(r)), f"--version no dice ninguna versión: {salida(r)!r}"


ERRORES_DE_USUARIO = [
    ("dose", "noexiste", "14"),
    ("dose", "paracetamol", "900"),
]


@pytest.mark.parametrize("args", ERRORES_DE_USUARIO)
def test_un_error_del_usuario_no_es_una_traza(args: tuple[str, ...]):
    r = corre(*args)
    out = salida(r)
    assert "Traceback" not in out, (
        f"«{' '.join(args)}» imprime una traza de Python; no está roto el programa, "
        f"le han pedido algo que no existe:\n{out[:400]}"
    )
    assert r.returncode != 0, "un error del usuario no puede salir con éxito"
    assert len(out.strip().splitlines()) <= 4, f"el mensaje debería caber en pocas líneas:\n{out}"


def test_el_error_dice_que_hacer():
    """Un mensaje que no dice la alternativa obliga a abrir el código."""
    out = salida(corre("dose", "noexiste", "14")).lower()
    assert "paracetamol" in out and "ibuprofen" in out, (
        f"el error no dice cuáles son los fármacos que sí hay: {out!r}"
    )


#: Los tres primeros no tocan PyMuPDF y por eso pasaban ya: los que hay que mirar son los
#: que SÍ lo importan, `search` y `doctor`, que era donde salía el aviso. La primera vez
#: lo «arreglé» con `warnings.filterwarnings` y no sirvió de nada — PyMuPDF escribe en
#: stderr, no lanza un warning—, y el candado dio verde porque no miraba esos dos.
COMANDOS_SILENCIOSOS = [
    ("dose", "paracetamol", "14"),
    ("triage", "fiebre alta"),
    ("flagged",),
    ("search", "fiebre", "--k", "1"),
    ("doctor",),
]


@pytest.mark.parametrize("args", COMANDOS_SILENCIOSOS)
def test_ningun_comando_escupe_avisos_de_dependencias(args: tuple[str, ...]):
    out = salida(corre(*args))
    assert "fitz" not in out and "deprecated" not in out.lower(), (
        f"«{' '.join(args)}» empieza por un aviso de una dependencia, que tapa lo que importa:\n"
        f"{out[:300]}"
    )


def test_una_ingesta_que_falla_entera_no_sale_con_exito():
    """Doce timers miran `$?`. Una ingesta de 422 errores no puede devolver éxito."""
    r = corre("ingest", "no/existe/de/verdad", "--no-index", timeout=900)
    assert r.returncode != 0, (
        "la ingesta falló todos los documentos y devolvió éxito; cualquier automatismo "
        f"la habría dado por buena:\n{salida(r)[-400:]}"
    )


def test_un_numero_de_resultados_imposible_se_rechaza():
    r = corre("search", "fiebre", "--k", "-3")
    assert r.returncode != 0, (
        "un `--k` negativo llega al LIMIT del FTS y vuelca el índice entero: 1.091 líneas "
        f"por una errata. {salida(r)[:200]}"
    )
