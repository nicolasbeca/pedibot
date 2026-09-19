"""Una guía que vive en una dirección redirigida está muerta: se retira antes de subirla.

19-sep-2026. El publicador hace lo correcto: al regenerar una guía con mejor título, redirige la
dirección vieja y borra el fichero viejo. Lo que la resucitaba era el despliegue. `--no-pull`
significa «manda la copia local», así que los ficheros que el servidor había retirado meses atrás
volvían a subir en cada despliegue, uno detrás de otro, hasta 61.

No se notaba porque la redirección gana: quien abría la dirección vieja llegaba bien a la nueva.
Lo que sí se notaba era el recuento. El sitio decía tener 568 guías y las que un lector podía
abrir eran 507, y esa cifra se estaba usando fuera, en una solicitud de financiación.

Por eso se retira aquí, en el despliegue, y no sólo en un test: el test mira esta copia, y lo que
importa es lo que sale hacia el servidor.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENIDO = ROOT / "web" / "content"


def muertas(contenido: Path = CONTENIDO) -> list[Path]:
    """Ficheros de guía cuya dirección el sitio redirige a otra parte."""
    fichero = contenido / "_redirects.json"
    if not fichero.exists():
        return []
    try:
        redirecciones = json.loads(fichero.read_text(encoding="utf-8"))
    except ValueError:
        return []
    fuera = []
    for carpeta in sorted(p for p in contenido.iterdir() if p.is_dir()):
        prefijo = "" if carpeta.name == "en" else f"/{carpeta.name}"
        for md in sorted(carpeta.glob("*.md")):
            if f"{prefijo}/guides/{md.stem}" in redirecciones:
                fuera.append(md)
    return fuera


def main() -> int:
    sobran = muertas()
    for md in sobran:
        # el contenido no se pierde: la redirección lleva a la guía que la sustituyó, y el
        # fichero sigue en el historial de git
        md.unlink()
        print(f"   - guía retirada (su dirección redirige a otra): {md.as_posix()}")
    if sobran:
        print(f"   {len(sobran)} retirada(s); quedan {len(list(CONTENIDO.rglob('*.md')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
