"""Deja las cifras de uso del sitio donde cualquiera pueda mirarlas (19-sep-2026).

`/api/stats` publicaba sólo lo del chat en siete días. Eso está bien y se queda, pero decir por
ahí «las cifras de uso están publicadas en esa dirección» y que quien la abra vea dos respuestas
es peor que no enseñar nada: parece que se esconde el resto. Y el resto es lo bueno, porque la
mayoría de lo que hace este sitio se contesta sin preguntar nada.

Las visitas salen del registro de Caddy con `journalctl`, que tarda y no puede colgar de una
petición pública. Así que se calculan aquí, cada pocas horas, y la API sólo lee el fichero.

El mismo criterio de siempre: cuenta como persona quien pidió la página y después su hoja de
estilo o su tipo de letra, que es lo que hace un navegador y no hace un robot. Lo descartado se
publica también, en `page_requests`, para que nadie tenga que fiarse de mi filtro.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from pedibot.ops import report
from pedibot.ops.store import OpsStore
from pedibot.settings import get_settings

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "data" / "public_stats.json"

#: Un año es el techo de `web_visits`, y el registro rota antes. Por eso se publica `covers`.
TODO = 0


def reunir() -> dict[str, object]:
    web = report.web_visits(TODO)
    cubre = web.get("covers") or ()
    chat = OpsStore(get_settings().ops_db_path).stats(days=3650)
    return {
        "generated": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "site": {
            # lo que el registro tenía de verdad: ni se llama total a un log rotado, ni se
            # esconde desde cuándo se cuenta
            "covers": list(cubre),
            "visitors": web["visitors"],
            "visits": web.get("visits", 0),
            "views": web["views"],
            "read_more_than_one_page": web.get("returning", 0),
            "sessions_timed": web.get("timed", 0),
            "median_seconds": round(web["median_seconds"]) if web.get("median_seconds") else None,
            "sessions_over_a_minute": web.get("over_a_minute", 0),
            "page_requests_not_counted": web.get("page_requests", 0),
            "top_pages": [{"page": u, "views": n} for u, n in web.get("top", [])],
        },
        "chat_all_time": {
            "answers": chat.get("answers"),
            "by_level": chat.get("by_level"),
            "by_verification": chat.get("by_verification"),
            "cost_usd": chat.get("cost_usd"),
        },
    }


def main() -> int:
    datos = reunir()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sitio = datos["site"]
    assert isinstance(sitio, dict)
    print(
        f"public_stats.json: {sitio['visitors']} visitantes, {sitio['views']} páginas vistas, "
        f"cubriendo {sitio['covers'] or 'nada'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
