"""Un nombre de país dentro de una palabra corriente (18-sep-2026).

L177 se escribió hoy, con África, por «Gana» —que es Ghana en portugués y el verbo de «mi bebé no
gana peso»—. Al repasar con esa lección en la mano apareció lo que ya estaba puesto desde antes, y
era peor, porque llevaba meses en producción:

    «catar»  dentro de «catarro» y de «se acatarra»   → una pregunta por un catarro leía Catar
    «inde»   dentro de «Windeln», que es «pañales»    → «sie macht kaum Windeln nass», que es una
                                                        frase de deshidratación del golden, leía
                                                        India
    «usa»    dentro de «causa», «usar» y «no usa»     → «mi hija no usa el orinal» leía EE. UU.
    «riad»   dentro de «resfriado»                    → «o bebé está resfriado» leía Arabia Saudí

La señal es mecánica y no hace falta adivinarla: si el nombre casa **dentro** de una palabra más
larga —con una letra pegada delante o detrás— no se ha leído un país, se ha leído un trozo de otra
cosa. Eso es lo que mide esta prueba, sobre el corpus del propio proyecto y no sobre frases
inventadas para la ocasión.

Y deja escritas las excepciones que sí son legítimas, que son las tres formas adjetivas: «francesa»
lleva «france» dentro y habla de Francia; «kuwaití» lleva «kuwait» dentro y habla de Kuwait.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest
import yaml

from pedibot.bot.vaccines import COUNTRY_IN_TEXT

RAIZ = pathlib.Path(__file__).resolve().parents[1]
LETRA = re.compile(r"[^\W\d_]", re.UNICODE)

#: Lo que sí puede ir pegado a otra letra, porque la palabra larga habla del mismo país.
PERMITIDO = {("FR", "france"), ("FR", "frança"), ("FR", "francia"), ("KW", "kuwait")}


#: El vocabulario corriente de una consulta pediátrica, en las ocho lenguas: las palabras dentro
#: de las cuales se escondía un país. Va escrito aquí y no sólo en el golden porque el golden no
#: tiene por qué contener «catarro», y una prueba que sólo mira donde no está el problema es una
#: prueba dormida (L146): la primera versión de este fichero pasaba con el fallo puesto.
PALABRAS_DE_TODOS_LOS_DIAS = [
    "mi hijo tiene un catarro fuerte y mocos",
    "desde que va a la guardería se acatarra todos los meses",
    "el niño está acatarrado y no duerme",
    "o bebé está resfriado desde ontem",
    "mi hija no usa el orinal todavía",
    "hay que usar el termómetro rectal en los bebés",
    "la causa exacta no se sabe",
    "sie macht kaum Windeln nass seit gestern",
    "das Kind hat die Windeln voll",
    "la niña es muy independiente para comer",
    "my son has a malignant tumour",
    "il a une tumeur maligne",
    "mi bebé no gana peso desde hace un mes",
    "my child was bitten by a guinea pig",
    "вместо того чтобы спать, он плачет",
    "ребёнок вдохнул чад на пожаре",
    "поражение органа",
    "ребёнок ел малину и у него сыпь",
    "нужен индивидуальный подход",
    "الوضع المالي للأسرة صعب",
    "كم قطرة من الشراب أعطيه",
    "الجنسية المصرية",
    "टीका लगवाना है",
]


def _corpus() -> list[str]:
    """Texto real del producto: lo que preguntan los padres y lo que el triaje escribe."""
    frases: list[str] = list(PALABRAS_DE_TODOS_LOS_DIAS)
    for nombre in ("golden.jsonl", "flagged.jsonl"):
        f = RAIZ / "eval" / nombre
        if not f.exists():
            continue
        for linea in f.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            try:
                d = json.loads(linea)
            except json.JSONDecodeError:
                continue
            for clave in ("question", "q", "pregunta", "text"):
                if isinstance(d.get(clave), str) and len(d[clave]) > 8:
                    frases.append(d[clave])
                    break
    reglas = yaml.safe_load((RAIZ / "config" / "red_flags.yaml").read_text(encoding="utf-8"))
    for regla in reglas.get("rules", reglas if isinstance(reglas, list) else []):
        if not isinstance(regla, dict):
            continue
        for valor in regla.values():
            if isinstance(valor, dict):
                frases += [v for v in valor.values() if isinstance(v, str) and len(v) > 8]
            elif isinstance(valor, list):
                frases += [v for v in valor if isinstance(v, str) and len(v) > 8]
            elif isinstance(valor, str) and len(valor) > 8:
                frases.append(valor)
    return frases


CORPUS = _corpus()


def test_the_corpus_is_not_empty() -> None:
    """Si un día no se lee nada, esta prueba pasaría sin mirar nada (L146)."""
    assert len(CORPUS) > 200, f"sólo {len(CORPUS)} frases: el corpus no se está leyendo"


@pytest.mark.parametrize("code", sorted(COUNTRY_IN_TEXT))
def test_no_country_name_is_read_inside_a_longer_word(code: str) -> None:
    pillados: list[str] = []
    for nombre in COUNTRY_IN_TEXT[code]:
        if (code, nombre) in PERMITIDO:
            continue
        for frase in CORPUS:
            low = frase.lower()
            i = low.find(nombre)
            while i >= 0:
                antes = low[i - 1] if i > 0 else " "
                despues = low[i + len(nombre)] if i + len(nombre) < len(low) else " "
                if LETRA.match(antes) or LETRA.match(despues):
                    palabra = re.search(r"[^\W\d_]*" + re.escape(nombre) + r"[^\W\d_]*", low)
                    pillados.append(
                        f"«{nombre}» ({code}) dentro de «{palabra.group(0) if palabra else nombre}»"
                        f" — {frase[:60]}"
                    )
                    break
                i = low.find(nombre, i + 1)
    assert not pillados, (
        "estos nombres de país se leen dentro de otra palabra; o llevan frontera de palabra en "
        f"COUNTRY_SHORT, o se quitan: {sorted(set(pillados))[:6]}"
    )
