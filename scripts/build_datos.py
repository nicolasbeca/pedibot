"""DATOS.md: todas las cifras del proyecto, contadas y nunca tecleadas (21-sep-2026).

El operador, repasando los `.md`: «a veces tienen poca consistencia, hay contradicciones entre
ellos». Medido antes de opinar: **107 cifras escritas a mano no cuadraban** con lo que dicen los
ficheros de datos. APP.md decía 88 países en tres sitios y 61 calendarios en cinco; WEB.md, 44
reglas de alarma cuando son 83 y 419 documentos cuando son 497.

Ninguno de esos números estaba mal el día que se escribió. Lo que pasa es que **una cifra
tecleada no discute con nadie**: el fichero de datos cambia y la frase se queda, y cuanto más
útil es el documento más veces se copia la frase.

Así que las cifras dejan de vivir en la prosa. Viven aquí, contadas al generar, y los demás
documentos apuntan a este en vez de repetirlas. Es la misma regla que ya sigue `/memo`, que
cuenta sus once cifras al construirse, y la misma que hizo falta para poder enviar una solicitud
de financiación sin mentir por descuido.

    uv run python scripts/build_datos.py          # reescribe DATOS.md
    uv run python scripts/check_docs.py           # dice qué .md contradice a DATOS.md
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess

import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "DATOS.md"

#: Los países del continente, para poder decir cuánto de cada cosa es África sin contarlo a ojo.
AFRICA = set(
    "DZ AO BJ BW BF BI CV CM CF TD KM CD CG CI DJ EG GQ ER SZ ET GA GM GH GN GW KE LS LR LY "
    "MG MW ML MR MU MA MZ NA NE NG RW ST SN SC SL SO ZA SS SD TZ TG TN UG ZM ZW".split()
)


def _cfg(nombre: str):
    return yaml.safe_load((RAIZ / "config" / nombre).read_text(encoding="utf-8"))


def cifras() -> dict[str, dict]:
    """Cada cifra, con de dónde sale. El «de dónde» es tan importante como el número: es lo que
    permite comprobarla sin preguntarle a nadie."""
    em = _cfg("emergency_numbers.yaml")
    paises_em = [k for k in em if k != "default"]
    va = _cfg("vaccines.yaml")["countries"]
    gr = _cfg("growth_charts.yaml").get("countries", {})
    rf = _cfg("red_flags.yaml")["rules"]
    dr = _cfg("drugs.yaml")["drugs"]
    nombres_vac = _cfg("vaccine_names.yaml").get("names", {})
    cat = json.loads((RAIZ / "dataset" / "sources.json").read_text(encoding="utf-8"))
    interno = json.loads(
        (RAIZ / "web" / "site" / "src" / "data" / "sources.json").read_text(encoding="utf-8")
    )
    guias = list((RAIZ / "web" / "content").rglob("*.md"))
    marcas = [b for m in dr.values() for b in m["brands"]]
    paises_marca = {c for b in marcas for c in b["countries"]}
    sin_numero = [
        k
        for k, v in em.items()
        if k != "default" and isinstance(v, dict) and (v.get("no_national") or v.get("unverified"))
    ]
    idiomas_guias = {
        d.name: len(list(d.glob("*.md")))
        for d in sorted((RAIZ / "web" / "content").iterdir())
        if d.is_dir()
    }

    return {
        "países con número de emergencia": {
            "n": len(paises_em),
            "de": "config/emergency_numbers.yaml",
        },
        "de ellos, sin número nacional": {
            "n": len(sin_numero),
            "de": "los marcados `no_national` o `unverified`",
        },
        "calendarios de vacunas": {"n": len(va), "de": "config/vaccines.yaml"},
        "tablas de crecimiento por país": {"n": len(gr), "de": "config/growth_charts.yaml"},
        "reglas de alarma": {"n": len(rf), "de": "config/red_flags.yaml"},
        "marcas de medicamento": {"n": len(marcas), "de": "config/drugs.yaml"},
        "países con alguna marca": {"n": len(paises_marca), "de": "los `countries` de esas marcas"},
        "nombres de vacuna traducidos": {"n": len(nombres_vac), "de": "config/vaccine_names.yaml"},
        "documentos del catálogo público": {"n": len(cat), "de": "dataset/sources.json (CC0)"},
        "documentos del catálogo interno": {
            "n": len(interno),
            "de": "incluye los que no se pueden redistribuir",
        },
        "guías publicadas": {"n": len(guias), "de": "web/content/*/*.md"},
        "pruebas automáticas": {"n": _tests(), "de": "`uv run pytest --collect-only`"},
        "África: países con número": {
            "n": len(AFRICA & set(paises_em)),
            "de": "los 54 del continente",
        },
        "África: con calendario": {"n": len(AFRICA & set(va)), "de": "los 54 del continente"},
        "África: con curva": {"n": len(AFRICA & set(gr)), "de": "los 54 del continente"},
        "África: con alguna marca": {
            "n": len(AFRICA & paises_marca),
            "de": "los 54 del continente",
        },
        "guías: idiomas": {"n": len(idiomas_guias), "de": "una carpeta por lengua en web/content"},
    }


def _tests() -> int:
    """Las pruebas que hay, preguntándoselo a pytest. Si no se puede, se devuelve 0 y el
    documento lo dice: mejor un hueco declarado que un número de hace tres semanas."""
    try:
        salida = subprocess.run(
            ["uv", "run", "pytest", "-q", "--collect-only"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=300,
        ).stdout
    except Exception:  # noqa: BLE001
        return 0
    import re

    m = re.search(r"(\d+) tests? collected", salida)
    return int(m.group(1)) if m else 0


CABECERA = """# DATOS.md — las cifras del proyecto, contadas

> **Este fichero se genera. No se edita a mano.**
> `uv run python scripts/build_datos.py` lo reescribe leyendo los ficheros de datos de verdad.
>
> Existe porque el 21-sep-2026 se midió cuántas cifras escritas a mano en los `.md` ya no eran
> verdad: **107**. Ninguna estaba mal el día que se escribió. Una cifra tecleada no discute con
> nadie: el dato cambia y la frase se queda, y cuanto más útil es el documento más veces se ha
> copiado esa frase.
>
> **La regla, desde hoy:** ningún documento vuelve a escribir una de estas cifras. Se enlaza
> aquí. `scripts/check_docs.py` comprueba que nadie la repita mal, y la suite lo ejecuta.
>
> Lo que sí puede llevar cifras viejas, a propósito: `LESSONS.md`, `STATE.md` e `IDEAS.md`, que
> son diarios. Una cifra de hace un mes ahí no es un error, es lo que pasó ese día.

"""


def main() -> int:
    datos = cifras()
    hoy = dt.date.today().isoformat()
    lineas = [CABECERA, f"Contado el **{hoy}**.\n", "| | cifra | de dónde sale |", "|---|---:|---|"]
    for nombre, d in datos.items():
        n = f"{d['n']:,}".replace(",", ".") if d["n"] else "—"
        lineas.append(f"| {nombre} | **{n}** | {d['de']} |")
    lineas.append("")
    lineas.append(
        "Si una de estas cifras te parece mal, el fallo está en el fichero de datos que la "
        "alimenta, no aquí. Ésa es la idea."
    )
    DESTINO.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"DATOS.md: {len(datos)} cifras contadas → {DESTINO}")
    for nombre, d in datos.items():
        print(f"   {d['n']:>6}  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
