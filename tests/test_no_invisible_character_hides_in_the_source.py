"""El carácter invisible que rompe una expresión regular sin que se vea (18-sep-2026).

L14 lo dejó escrito el primer mes del proyecto: «`\\b` dentro de un heredoc de Python no crudo es
un BACKSPACE». Se escribe `\\b` con la intención de poner un borde de palabra y lo que queda en el
fichero es el carácter 0x08, que no se ve en ningún editor, no rompe la sintaxis y convierte la
expresión en una que no casa nunca.

Hoy ha vuelto a pasar **cinco veces**, y la última costó media hora de depuración: la guarda de
las preguntas causales llevaba `r"\\s*je\\b"` y en el fichero había `\\s*je` + 0x08. Todo se
comprobaba a mano y daba verdadero, la función devolvía falso, y `sed` mostraba la línea
perfecta. Sólo `cat -A` lo enseñó.

La lección decía además qué hacer: «comprobar `'\\x08' not in text` tras generar código». Esto es
esa comprobación, puesta donde no se olvide.

Se miran todos los caracteres de control salvo el salto de línea, el tabulador y el retorno de
carro, porque ninguno tiene nada que hacer en un fichero fuente de este proyecto.
"""

from __future__ import annotations

import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
#: Los sitios donde vive el código y los datos que el código lee.
CARPETAS = ("src", "config", "tests", "scripts", "ops", "prompts")
#: .py, .yaml y los demás textos que se editan a mano o se generan con scripts.
SUFIJOS = {".py", ".yaml", ".yml", ".json", ".md", ".sh", ".ts", ".astro"}
#: Lo que sí puede aparecer: el salto de línea, el tabulador y el retorno de carro de Windows.
PERMITIDOS = {0x09, 0x0A, 0x0D}


def _ficheros() -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for carpeta in CARPETAS:
        raiz = RAIZ / carpeta
        if not raiz.exists():
            continue
        out += [
            f
            for f in raiz.rglob("*")
            if f.is_file() and f.suffix in SUFIJOS and "__pycache__" not in f.parts
        ]
    return sorted(out)


FICHEROS = _ficheros()


def test_there_is_something_to_look_at() -> None:
    assert len(FICHEROS) > 100, f"sólo {len(FICHEROS)} ficheros: no se está mirando el proyecto"


@pytest.mark.parametrize("fichero", FICHEROS, ids=lambda f: f.name)
def test_no_control_character_sneaked_into_the_file(fichero: pathlib.Path) -> None:
    texto = fichero.read_text(encoding="utf-8", errors="replace")
    malos = [(i, ord(c)) for i, c in enumerate(texto) if ord(c) < 0x20 and ord(c) not in PERMITIDOS]
    if not malos:
        return
    i, code = malos[0]
    linea = texto[:i].count("\n") + 1
    alrededor = texto[max(0, i - 40) : i + 10].replace("\n", "⏎")
    pista = " (es un \\b escrito en un heredoc, L14)" if code == 0x08 else ""
    assert not malos, (
        f"{fichero.relative_to(RAIZ)}:{linea} tiene el carácter de control 0x{code:02X}{pista}. "
        f"Son {len(malos)} en total. Alrededor: «{alrededor}»"
    )
