"""Publica guías todos los días, repartiendo entre los ocho idiomas (11-sep-2026).

Encargo del operador: «tenemos que publicar constantemente cosas». Hasta hoy no había **ningún**
timer que generase guías —la última era del 5 de septiembre— y, debajo de eso, el plan de temas
estaba agotado: `pending_topics` devolvía cero en las ocho lenguas, así que un timer habría
corrido cada día sin escribir nada y sin decirlo.

Elige la lengua por **antigüedad de su guía más reciente**, no por orden fijo: así la que lleva
más tiempo sin nada escribe antes, y si un idioma se queda sin temas las demás siguen. Un orden
fijo deja al octavo esperando ocho días aunque sea el que va más atrasado.

**No sindica.** La cuenta de Bluesky habla inglés (decisión del operador), y el generador escribe
un día en hindi y otro en árabe; lo que sale a Bluesky lo deciden `pedibot-social-*`, que son
otros dos timers y saben en qué lengua hablan.

    uv run python ops/publish_daily.py            # 2 guías, las dos lenguas más atrasadas
    uv run python ops/publish_daily.py --n 4
    uv run python ops/publish_daily.py --dry-run  # dice a quién le tocaría y no escribe
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "web" / "content"
LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")
SITE = os.environ.get("SITE_URL", "https://pedibot.xyz")


def newest(lang: str) -> dt.date:
    """La fecha de la guía más reciente de esta lengua, o una muy vieja si no tiene ninguna."""
    d = CONTENT / lang
    fechas = []
    for md in d.glob("*.md") if d.exists() else []:
        m = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", md.read_text(encoding="utf-8")[:600], re.M)
        if m:
            fechas.append(dt.date.fromisoformat(m.group(1)))
    return max(fechas) if fechas else dt.date(2000, 1, 1)


def pendientes(lang: str) -> int:
    sys.path.insert(0, str(ROOT / "src"))
    from pedibot.publish.articles import pending_topics

    return len(pending_topics(CONTENT, lang))


def turno(n: int) -> list[str]:
    """Las `n` lenguas más atrasadas que además tengan algo que escribir."""
    con_cola = [x for x in LANGS if pendientes(x) > 0]
    return sorted(con_cola, key=newest)[:n]


def cuantas(lang: str) -> int:
    d = CONTENT / lang
    return len(list(d.glob("*.md"))) if d.exists() else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=2, help="cuántas guías (una por lengua)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    elegidas = turno(a.n)
    if not elegidas:
        # que se note: una cola vacía es la avería que dejó el sitio seis días sin publicar
        print("!! NO QUEDA NADA QUE PUBLICAR en ninguna lengua: hay que ampliar TOPIC_PLAN")
        print("PUBLISH-FIN escritas=0 cola_vacia=1")
        return 0

    antes = {lang: cuantas(lang) for lang in elegidas}
    for lang in elegidas:
        print(f"-> {lang} (última guía {newest(lang)}, {pendientes(lang)} temas por escribir)")
        if a.dry_run:
            continue
        # en proceso, no por subproceso: lanzarlo aparte le daba otro entorno, se quedaba sin
        # clave del modelo y volvía con código 0 habiendo escrito nada — y yo contaba ese código
        # como una guía. Ahora se cuentan los ficheros, que es lo único que prueba algo
        from pedibot.cli import publish as _publish

        try:
            _publish(topic=None, lang=lang, n=1, fake=False, site_url=SITE, social=False)
        except Exception as e:  # noqa: BLE001 — una lengua rota no puede llevarse a las demás
            print(f"   !! {lang}: {type(e).__name__}: {e}")

    escritas = sum(cuantas(lang) - antes[lang] for lang in elegidas)

    # Una guía escrita en disco no está publicada: el sitio es estático y hay que rehacerlo, o
    # la guía espera al siguiente despliegue. Con esto sale el mismo día, y a las 07:15 IndexNow
    # ya la encuentra en el sitemap.
    construido = False
    if escritas and not a.dry_run:
        import subprocess

        # Antes de rehacer, volver a exportar los datos del catálogo. Un tema NUEVO llega
        # al sitio sin categoría de taxonomía hasta que alguien corre `export_catalog.py` a
        # mano, y sin categoría la guía enlaza mal y se busca peor — en silencio, porque la
        # página se construye igual. Pasó el 11-sep-2026 con «ahogamiento», el primer tema
        # publicado por el timer: lo destapó un candado, no el proceso que lo causó.
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "export_catalog.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        )
        r = subprocess.run(
            "npm run build",
            cwd=ROOT / "web" / "site",
            shell=True,
            capture_output=True,
            text=True,
            timeout=900,
            env={**os.environ, "SITE_URL": SITE},
        )
        construido = r.returncode == 0
        print((r.stdout or r.stderr).strip()[-200:])

    # la firma va al final y sólo se imprime al llegar: su ausencia es la prueba de que murió (L117)
    print(
        f"PUBLISH-FIN escritas={escritas} pedidas={len(elegidas)} sitio_rehecho={int(construido)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
