"""Los países de renta baja y media-baja, del Banco Mundial (20-sep-2026).

**Por qué existe este fichero.** Probando la web viva como un padre de Nairobi —«my baby is 7
months and has watery diarrhoea since yesterday»— la respuesta era correcta y segura pero no
mencionaba el zinc. En Kenia, en Nigeria, en Etiopía y en la India el zinc no es un detalle: es
la mitad del tratamiento estándar de la diarrea infantil.

Lo que hay detrás no es una opinión mía, y ése es el punto. **La fuente acota ella misma dónde
aplica.** El documento de la OMS que ya está en el corpus dice, literalmente:

    «Diarrhoea due to infection is widespread throughout developing countries. In low-income
    countries, children under 3 years old experience on average three episodes of diarrhoea
    every year.»

y pone el suero de rehidratación y el zinc juntos como las medidas clave de tratamiento. Falta
sólo traducir «low-income countries» a una lista, y de eso hay una publicada, anual, descargable
y citable: **la clasificación por renta del Banco Mundial**. Renta baja (LIC) y media-baja (LMC).

La alternativa era escribir a mano «los africanos y los del sur de Asia», que suena razonable y
es exactamente lo que no se hizo con las marcas de Etiopía y del Congo. Plausible no es una
fuente.

    uv run python scripts/build_income_levels.py     # rehace config/income_levels.json
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "config" / "income_levels.json"

API = "https://api.worldbank.org/v2/country?format=json&per_page=400"
FUENTE = "World Bank — Country income classification (API v2, /country)"
FUENTE_URL = "https://datahelpdesk.worldbank.org/knowledgebase/articles/906519"

#: Renta baja y renta media-baja. Son las dos categorías que corresponden a lo que la OMS llama
#: «low-income countries» y «developing countries» en su hoja de enfermedades diarreicas.
BAJAS = ("LIC", "LMC")


def descarga() -> list[dict]:
    with urllib.request.urlopen(API, timeout=90) as r:  # noqa: S310 — URL fija y https
        datos = json.loads(r.read())
    # el primer elemento es la paginación; el segundo, las filas
    filas = datos[1]
    # el Banco Mundial mezcla países con agregados («África subsahariana»), y los agregados
    # llevan la región «NA». Namibia tiene iso2 «NA» pero su región es «SSF», así que el filtro
    # es por región y no por código, que es donde estaría el fallo fácil.
    return [c for c in filas if (c.get("region") or {}).get("id") != "NA"]


def main() -> int:
    paises = descarga()
    bajos = sorted(
        {c["iso2Code"].upper() for c in paises if (c["incomeLevel"] or {}).get("id") in BAJAS}
    )
    if len(bajos) < 50:
        print(f"sólo {len(bajos)} países: algo ha cambiado en la API, no se escribe nada")
        return 1
    salida = {
        "_": "Generado por scripts/build_income_levels.py. No se edita a mano.",
        "por_que": (
            "La OMS acota su recomendación de suero y zinc a los países de renta baja; esta es "
            "la lista con la que se traduce esa frase a códigos de país."
        ),
        "fuente": FUENTE,
        "fuente_url": FUENTE_URL,
        "descargado": dt.datetime.now(dt.UTC).date().isoformat(),
        "categorias": list(BAJAS),
        "paises_totales": len(paises),
        "low_and_lower_middle_income": bajos,
    }
    DESTINO.write_text(
        json.dumps(salida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"{len(bajos)} países de renta baja o media-baja -> {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
