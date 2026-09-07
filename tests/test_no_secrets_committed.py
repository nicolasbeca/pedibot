"""Ningún secreto puede acabar dentro de lo que git rastrea (7-sep-2026, housekeeping).

Hoy está limpio: se revisaron los 1.311 ficheros rastreados y todo el historial, y no hay ni una
clave. Esto existe para que siga siendo verdad — un secreto commiteado no se puede borrar de
verdad, porque el historial de git lo conserva y cualquiera que haya clonado ya lo tiene.

Los ficheros con secretos de este proyecto viven fuera de git y así deben seguir:

  · `.env`            — claves de DeepSeek, Telegram, el panel
  · `gsc_key.json`    — la cuenta de servicio de Search Console
  · `data/.ops_salt`  — la sal por despliegue de los hashes de IP

Los tres están en `.gitignore`, y este candado también lo comprueba: un `.gitignore` que pierde
una línea no da ningún error, simplemente deja de proteger.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]

#: Lo que NO puede aparecer. Escrito por trozos para que este mismo fichero no case con sus
#: propios patrones — si no, el candado se acusaría a sí mismo en cada ejecución.
PATRONES = {
    "clave de API de Google": re.compile("AIza" + r"[0-9A-Za-z_\-]{30,}"),
    "clave privada PEM": re.compile("-----BEGIN" + r" (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "clave de OpenAI o DeepSeek": re.compile("sk-" + r"[a-zA-Z0-9]{24,}"),
    "token de bot de Telegram": re.compile(r"\b\d{8,10}:AA[0-9A-Za-z_\-]{30,}"),
    "cuenta de servicio de Google": re.compile(r'"type"\s*:\s*"service_account"'),
}

#: Ficheros que enseñan la FORMA de un secreto sin contener ninguno.
EXENTOS = {".env.example", "test_no_secrets_committed.py"}


def _rastreados() -> list[pathlib.Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=RAIZ, capture_output=True, text=True, check=True
    ).stdout
    fuera = []
    for rel in out.split("\0"):
        if not rel:
            continue
        f = RAIZ / rel
        if f.is_file() and f.name not in EXENTOS and f.suffix not in (".png", ".jpg", ".woff2"):
            fuera.append(f)
    return fuera


def test_git_is_available_and_tracking_files() -> None:
    """El candado del candado: si `git ls-files` deja de responder, esto pasaría siempre."""
    assert len(_rastreados()) > 500


def test_no_secret_is_committed() -> None:
    culpables: list[str] = []
    for f in _rastreados():
        try:
            texto = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for que, patron in PATRONES.items():
            m = patron.search(texto)
            if m:
                linea = texto[: m.start()].count("\n") + 1
                culpables.append(f"{f.relative_to(RAIZ)}:{linea} — {que}")
    assert not culpables, (
        "hay secretos dentro de lo que git rastrea:\n  " + "\n  ".join(culpables) + "\n"
        "Un secreto commiteado no se borra: el historial lo conserva. Rótalo, no lo escondas."
    )


@pytest.mark.parametrize("fichero", [".env", "gsc_key.json", "data/.ops_salt"])
def test_the_files_that_hold_secrets_stay_ignored(fichero: str) -> None:
    """Un `.gitignore` que pierde una línea no da ningún error: deja de proteger, y se nota el
    día que ya es tarde."""
    r = subprocess.run(
        ["git", "check-ignore", "-q", fichero], cwd=RAIZ, capture_output=True, text=True
    )
    assert r.returncode == 0, f"{fichero} ya NO está en .gitignore"
