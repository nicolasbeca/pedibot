"""Ningún fichero del proyecto puede llevar caracteres de control invisibles (7-sep-2026).

La lección L14 dice que `\\b` dentro de un heredoc de Python no crudo es un BACKSPACE: al generar
código con `python - <<'EOF'` y cadenas normales, la secuencia de dos caracteres se escribe como
el byte 0x08, invisible en el fichero, y la expresión regular deja de casar **sin ningún error**.

Se escribió esa lección y no se escribió este candado. Hoy ha vuelto a morder, en el detector de
fuentes caducadas: `re.findall(r"<BS>(20\\d\\d)<BS>", texto)` no encontraba un año en ninguna
parte, y el detector habría informado alegremente de que no hay nada caducado. Es la sexta vez que
un fallo de esta familia entra por la misma puerta.

Lo que se comprueba es más ancho que la L14 a propósito: cualquier carácter de control que no sea
un salto de línea o una tabulación no tiene nada que hacer en un fichero de texto, venga de donde
venga. Y se comprueban también el YAML y el Markdown, no solo el Python: un 0x08 dentro del nombre
de una vacuna sería igual de invisible y bastante peor.
"""

from __future__ import annotations

import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]

#: Salto de línea, retorno de carro y tabulador son los únicos controles legítimos aquí.
PERMITIDOS = {0x09, 0x0A, 0x0D}

CARPETAS = ("src", "tests", "ops", "config", "scripts")
EXTENSIONES = (".py", ".yaml", ".yml", ".md", ".toml", ".json", ".sh")


def _ficheros() -> list[pathlib.Path]:
    fuera: list[pathlib.Path] = []
    for carpeta in CARPETAS:
        d = RAIZ / carpeta
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if f.is_file() and f.suffix in EXTENSIONES and "__pycache__" not in f.parts:
                fuera.append(f)
    return sorted(fuera)


def test_there_is_something_to_check() -> None:
    """El candado del candado: si un día no encuentra ficheros, dejó de comprobar nada."""
    assert len(_ficheros()) > 100, "la búsqueda de ficheros se ha quedado corta"


@pytest.mark.parametrize(
    "f", _ficheros(), ids=lambda f: str(f.relative_to(RAIZ)).replace("\\", "/")
)
def test_no_invisible_control_characters(f: pathlib.Path) -> None:
    b = f.read_bytes()
    malos = sorted({c for c in b if c < 0x20 and c not in PERMITIDOS})
    if not malos:
        return
    # decir DÓNDE, que es lo caro de encontrar cuando el carácter no se ve
    primero = malos[0]
    i = b.index(bytes([primero]))
    linea = b[: i + 1].count(b"\n") + 1
    nombres = {0x08: "BACKSPACE (el de la L14)", 0x0C: "FORM FEED", 0x1B: "ESCAPE", 0x00: "NUL"}
    assert not malos, (
        f"{f.relative_to(RAIZ)}: carácter de control 0x{primero:02X} "
        f"[{nombres.get(primero, 'de control')}] en la línea {linea}. "
        "Casi siempre es una secuencia de escape que un heredoc se comió (L14): "
        "escribe el fichero con la herramienta Write, no con `python - <<EOF`."
    )
