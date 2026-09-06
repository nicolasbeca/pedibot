"""Refresca lo que el panel enseña de Google. Diario, por temporizador.

La lógica vive en pedibot.ops.search; esto es el cable, como ops/daily_review.py.

El panel NO llama a Google: una llamada de red dentro de un render convierte una página de 200 ms
en una que a veces tarda diez segundos y a veces falla, y entonces se deja de abrir. Aquí se
escribe `data/gsc.json` una vez al día y la página lee el fichero.

    python3 ops/gsc_refresh.py           # 28 días
    python3 ops/gsc_refresh.py --days 90
"""

from __future__ import annotations

import argparse
import sys

from pedibot.ops.search import collect, key_path, save


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    a = ap.parse_args()

    if not key_path().exists():
        # sin clave no hay nada que hacer, y no es un error: el panel ya dice que no hay datos
        print(f"no hay clave en {key_path()} — nada que refrescar", file=sys.stderr)
        return 0

    data = collect(a.days)
    save(data)
    print(
        f"{data['from']} → {data['to']}: {data['clicks']} clics · "
        f"{data['impressions']} impresiones · posición {data['position']} · "
        f"{len(data['queries'])} consultas · {len(data['close'])} empujables"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
