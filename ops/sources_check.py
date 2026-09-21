"""Fuentes rotas o caducadas → data/sources_check.json, que enseña el panel (domingos).

Iba dentro del informe semanal de Telegram. El 21-sep-2026 el operador quitó los informes
(«tengo el panel para entrar cuando quiera»), y esto no se podía ir con ellos: un enlace de fuente
que da 404 es la promesa de la web rota, y el del Ministerio de Sanidad llevó 404 semanas sin que
lo vigilara nadie. Tarda minutos, por eso no se hace al abrir el panel.
"""

from __future__ import annotations

import datetime as dt
import json

from pedibot.ops.sources_alive import report_lines
from pedibot.settings import ROOT

OUT = ROOT / "data" / "sources_check.json"


def main() -> int:
    lines = report_lines(ROOT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {"checked": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "lines": lines},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print("\n".join(lines) or "fuentes: nada que contar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
