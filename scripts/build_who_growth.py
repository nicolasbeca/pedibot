"""Convierte las tablas LMS de la OMS a `config/who_growth.json`.

    uv run --with openpyxl python scripts/build_who_growth.py <carpeta con los xlsx>

Las catorce tablas (niños y niñas) son las «expanded tables» que la OMS publica para construir
carnés de salud: peso para la edad, longitud/talla para la edad y peso para la longitud/talla
de los Patrones de Crecimiento Infantil (2006, 0–5 años, por día o por milímetro), y talla para
la edad, IMC para la edad (5–19) y peso para la edad (5–10) de la Referencia de Crecimiento
2007 (por mes). Sólo se guardan la clave y L, M, S: las columnas SD se recalculan con ellas y
son las que comprueba la prueba.
"""

from __future__ import annotations

import json
import pathlib
import sys

import openpyxl

FICHEROS = {
    "wfa_m": ("wfa_boys.xlsx", "day"),
    "wfa_f": ("wfa_girls.xlsx", "day"),
    "lhfa_m": ("lhfa_boys.xlsx", "day"),
    "lhfa_f": ("lhfa_girls.xlsx", "day"),
    "wfl_m": ("wfl_boys.xlsx", "length_cm"),
    "wfl_f": ("wfl_girls.xlsx", "length_cm"),
    "wfh_m": ("wfh_boys.xlsx", "height_cm"),
    "wfh_f": ("wfh_girls.xlsx", "height_cm"),
    "hfa519_m": ("hfa519_boys.xlsx", "month"),
    "hfa519_f": ("hfa519_girls.xlsx", "month"),
    "bmi519_m": ("bmi519_boys.xlsx", "month"),
    "bmi519_f": ("bmi519_girls.xlsx", "month"),
    "wfa510_m": ("wfa510_boys.xlsx", "month"),
    "wfa510_f": ("wfa510_girls.xlsx", "month"),
}

META = {
    "source": [
        "WHO Child Growth Standards (2006), 0–5 years: weight-for-age, length/height-for-age, "
        "weight-for-length/height — https://www.who.int/tools/child-growth-standards/standards",
        "WHO Growth Reference (2007), 5–19 years: height-for-age, BMI-for-age; weight-for-age 5–10 "
        "— https://www.who.int/tools/growth-reference-data-for-5to19-years",
    ],
    "method": "LMS; z restringido más allá de ±3 en los indicadores de peso (WHO Anthro)",
    "downloaded": "2026-09-13",
}


def main(carpeta: pathlib.Path) -> None:
    tablas: dict[str, dict[str, object]] = {}
    for nombre, (fichero, clave) in FICHEROS.items():
        ws = openpyxl.load_workbook(carpeta / fichero, read_only=True).active
        filas = list(ws.iter_rows(values_only=True))
        cab = [str(c).strip().upper() for c in filas[0]]
        iL, iM, iS = cab.index("L"), cab.index("M"), cab.index("S")
        rows = []
        for r in filas[1:]:
            if r[0] is None:
                continue
            rows.append([float(r[0]), float(r[iL]), float(r[iM]), float(r[iS])])
        rows.sort()
        tablas[nombre] = {"x": clave, "rows": rows}
        print(f"  {nombre}: {len(rows)} filas, {rows[0][0]:g}–{rows[-1][0]:g} {clave}")
    # CDC 2000, 2–20 años (dominio público): la carpeta `cdc/` junto a la de la OMS, con los CSV
    # tal como los publica cdc.gov/growthcharts/cdc-data-files.htm. Sexo 1 = niño, 2 = niña;
    # la edad va en meses con el medio mes (24,5 = de 24 a 24,99), salvo el 24 exacto.
    cdc = carpeta.parent / "cdc"
    if cdc.exists():
        import csv

        for fichero, nombre in (("wtage.csv", "cdc_wfa"), ("statage.csv", "cdc_hfa"), ("bmiagerev.csv", "cdc_bmi")):
            filas: dict[str, list[list[float]]] = {"m": [], "f": []}
            for r in csv.DictReader((cdc / fichero).open(encoding="utf-8")):
                if not r.get("Sex") or not r["Sex"].strip().isdigit():
                    continue
                s = "m" if r["Sex"].strip() == "1" else "f"
                filas[s].append([float(r["Agemos"]), float(r["L"]), float(r["M"]), float(r["S"])])
            for s, rows in filas.items():
                rows.sort()
                tablas[f"{nombre}_{s}"] = {"x": "month", "rows": rows}
                print(f"  {nombre}_{s}: {len(rows)} filas, {rows[0][0]:g}–{rows[-1][0]:g} month")
        META["source"].append(
            "CDC Growth Charts (2000), 2–20 years: weight-for-age, stature-for-age, BMI-for-age "
            "— https://www.cdc.gov/growthcharts/cdc-data-files.htm (public domain)"
        )
    out = pathlib.Path(__file__).resolve().parents[1] / "config" / "who_growth.json"
    out.write_text(
        json.dumps({"meta": META, "tables": tablas}, separators=(",", ":")), encoding="utf-8"
    )
    print(f"-> {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
