"""Las respuestas de MetaDAO, comprobadas antes de enviarlas (19-sep-2026).

    uv run python scripts/check_metadao.py

Hace tres cosas, y las tres existen por algo que ya pasó:

1. **Relee todas las cifras** de los ficheros publicados y de lo vivo. Es la regla de la casa
   —ningún número sale fuera sin releerlo— y ya salvó un error: yo había escrito «ocho países
   sin número de emergencias» y son siete, más uno donde no pudimos verificarlo.
2. **Comprueba que caben** en los 8.000 caracteres del formulario.
3. **Busca contradicciones entre respuestas.** Cinco textos escritos en tardes distintas se
   contradicen sin que nadie lo note: cuando el operador decidió que el motor se puede licenciar
   a instituciones, dos frases de dos respuestas distintas («no va a daros dinero», «no tengo
   nada que monetizar») pasaron a ser falsas el mismo minuto.

Y comprueba que no haya formato: el cuadro del formulario es texto plano, así que una viñeta se
queda en un guion suelto y los asteriscos se ven literales.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import urllib.request

import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
FICHERO = RAIZ / "ops" / "METADAO.md"
TOPE = 8000

#: Lo que los textos afirman, y de dónde se relee cada cosa.
CIFRAS = {
    "88 countries": lambda: len(
        [
            k
            for k in yaml.safe_load(
                (RAIZ / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8")
            )
            if k != "default"
        ]
    ),
    "61 countries": lambda: len(
        yaml.safe_load((RAIZ / "config" / "vaccines.yaml").read_text(encoding="utf-8"))["countries"]
    ),
    "69 countries": lambda: len(
        yaml.safe_load((RAIZ / "config" / "growth_charts.yaml").read_text(encoding="utf-8")).get(
            "countries", {}
        )
    ),
    "502 guides": lambda: len(list((RAIZ / "web" / "content").rglob("*.md"))),
    # 19-sep-2026: el texto decía 48 y eran 49. Era la única cifra escrita a mano de todas,
    # y por eso fue la única que se quedó vieja. Aquí se cuenta como las demás.
    "49 African countries": lambda: len(
        [
            c
            for c in [
                "DZ",
                "AO",
                "BJ",
                "BW",
                "BF",
                "BI",
                "CV",
                "CM",
                "CF",
                "TD",
                "KM",
                "CD",
                "CG",
                "CI",
                "DJ",
                "EG",
                "GQ",
                "ER",
                "SZ",
                "ET",
                "GA",
                "GM",
                "GH",
                "GN",
                "GW",
                "KE",
                "LS",
                "LR",
                "LY",
                "MG",
                "MW",
                "ML",
                "MR",
                "MU",
                "MA",
                "MZ",
                "NA",
                "NE",
                "NG",
                "RW",
                "ST",
                "SN",
                "SC",
                "SL",
                "SO",
                "ZA",
                "SS",
                "SD",
                "TZ",
                "TG",
                "TN",
                "UG",
                "ZM",
                "ZW",
            ]
            if c
            in yaml.safe_load(
                (RAIZ / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8")
            )
            and c
            in yaml.safe_load((RAIZ / "config" / "vaccines.yaml").read_text(encoding="utf-8"))[
                "countries"
            ]
        ]
    ),
    "83 red flags": lambda: len(
        yaml.safe_load((RAIZ / "config" / "red_flags.yaml").read_text(encoding="utf-8"))["rules"]
    ),
    "496 documents": lambda: len(
        json.loads((RAIZ / "dataset" / "sources.json").read_text(encoding="utf-8"))
    ),
    "seven countries": lambda: len(
        [
            k
            for k, v in yaml.safe_load(
                (RAIZ / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8")
            ).items()
            if k != "default" and isinstance(v, dict) and v.get("no_national")
        ]
    ),
}

#: Frases que, si aparecen, significan que dos respuestas se contradicen o que se coló formato.
PROHIBIDAS = {
    "nothing to monetise": "contradice licenciar el motor a instituciones",
    "will make you money": "frase vieja: hoy sí hay una vía de ingreso prevista",
    "no data sale, and there will not be": "la promesa se reformuló: lo que no se monetiza es el lado del padre",
}

#: Y las que deben aparecer exactamente una vez en todo el conjunto.
UNA_VEZ = {"three in the morning": "la imagen se gastaba de tanto repetirla"}


def textos() -> dict[str, str]:
    """Sólo lo que se pega en el formulario, no las notas en español."""
    crudo = FICHERO.read_text(encoding="utf-8")
    fuera: dict[str, str] = {}
    for m in re.finditer(r"^## (P\d)[^\n]*\n", crudo, re.M):
        trozo = crudo[m.end() :].split("\n---")[0]
        if ")*" in trozo.split("\n\n")[0]:
            trozo = trozo.split(")*", 1)[1]
        fuera[m.group(1)] = trozo.strip()
    return fuera


def main() -> int:
    if not FICHERO.exists():
        print(f"no encuentro {FICHERO}", file=sys.stderr)
        return 1
    partes = textos()
    problemas: list[str] = []

    print("== las cifras que afirman los textos")
    juntos = "\n".join(partes.values())
    for frase, cuenta in CIFRAS.items():
        if frase not in juntos:
            continue
        dicho = int(re.match(r"\d+", frase).group(0)) if frase[0].isdigit() else 7
        real = cuenta()
        ok = real == dicho
        print(f"   {'ok ' if ok else 'NO '} «{frase}» → fichero: {real}")
        if not ok:
            problemas.append(f"«{frase}» y el fichero dice {real}")

    print("\n== longitud")
    for nombre, cuerpo in partes.items():
        ok = len(cuerpo) <= TOPE
        print(f"   {'ok ' if ok else 'NO '} {nombre}: {len(cuerpo)} de {TOPE}")
        if not ok:
            problemas.append(f"{nombre} se pasa de {TOPE} caracteres")

    print("\n== contradicciones y formato")
    for frase, por_que in PROHIBIDAS.items():
        n = juntos.count(frase)
        print(f"   {'ok ' if n == 0 else 'NO '} «{frase}»: {n}  ({por_que})")
        if n:
            problemas.append(f"aparece «{frase}»: {por_que}")
    for frase, por_que in UNA_VEZ.items():
        n = juntos.count(frase)
        print(f"   {'ok ' if n == 1 else 'NO '} «{frase}»: {n}  ({por_que})")
        if n != 1:
            problemas.append(f"«{frase}» aparece {n} veces y debe aparecer una")
    for marca, que in (("**", "asteriscos"), ("\n- ", "viñetas"), ("\n# ", "encabezados")):
        n = juntos.count(marca)
        print(f"   {'ok ' if n == 0 else 'NO '} {que}: {n}")
        if n:
            problemas.append(f"hay {que} en un cuadro de texto plano")

    print("\n== lo vivo")
    for ruta in ("/api/stats", "/sources", "/legal"):
        try:
            code = urllib.request.urlopen(f"https://pedibot.xyz{ruta}", timeout=20).status
        except Exception:  # noqa: BLE001
            code = 0
        print(f"   {'ok ' if code == 200 else 'NO '} {ruta} → {code}")
        if code != 200:
            problemas.append(f"{ruta} no responde y el texto lo cita")

    print()
    if problemas:
        print(f"{len(problemas)} COSAS QUE ARREGLAR ANTES DE ENVIAR:")
        for p in problemas:
            print("  -", p)
        return 1
    print("todo cuadra: se puede enviar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
