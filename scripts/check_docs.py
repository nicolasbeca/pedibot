"""¿Qué documento dice una cifra que ya no es verdad? (21-sep-2026)

Medido el día que el operador dijo que los `.md` se contradecían: **107 cifras escritas a mano**
que no cuadraban con los ficheros de datos. APP.md decía 88 países en tres sitios y 61
calendarios en cinco; WEB.md, 44 reglas de alarma cuando son 83 y 419 documentos cuando son 497.

Esto las relee de donde salen y dice dónde no cuadran, con el número de línea.

**Lo que NO señala, y es la mitad de la regla:**

- `LESSONS.md`, `STATE.md` e `IDEAS.md` son diarios. Una cifra de hace un mes ahí no es un error,
  es lo que pasó ese día, y perseguirla convertiría el historial en una mentira ordenada.
- `ops/METADAO.md` lleva el texto **tal y como se envió** el 20-sep-2026. Reescribirlo sería
  falsificar lo enviado; su nota de cabecera ya dice qué cifras se quedaron cortas.
- `PRD.md` es el plan original, y las cifras de su sección de alcance describen lo que había al
  escribirlo.

    uv run python scripts/check_docs.py          # lista lo que no cuadra
    uv run python scripts/check_docs.py --fix    # enseña el sed que lo arreglaría
"""

from __future__ import annotations

import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]

#: Los que pueden llevar cifras viejas a propósito, y por qué.
DIARIOS = {
    "LESSONS.md": "diario de fallos: la cifra es la del día que ocurrió",
    "STATE.md": "diario de estado: cada entrada es de su fecha",
    "IDEAS.md": "cuaderno de ideas fechadas",
    "METADAO.md": "el texto tal y como se envió; reescribirlo sería falsificarlo",
    "PRD.md": "el plan original: sus cifras describen lo que había al escribirlo",
    "DATOS.md": "es el generado",
}

#: Lo que marca una cifra como HISTÓRICA, y por tanto legítima aunque ya no cuadre. Sin esta
#: salida, el candado obligaría a borrar frases verdaderas —«390 de las 483 guías de entonces
#: colgaban de un solo enlace»— o a mentir cambiándoles el número. Las dos son peores que el
#: problema que resuelve.
#: «cuando son» y «recontad…» entran por un caso que apareció al afinar esto: la nota que
#: explica un fallo dice a la vez la cifra vieja y la buena —«decía 288 documentos cuando son
#: 497»— y es la frase más honesta del fichero. Perseguirla obligaría a borrar la explicación
#: del error para que el detector del error se calle.
HISTORICA = re.compile(
    r"de entonces|al escribir esto|por entonces|en aquel momento|hasta entonces"
    r"|contado el \d|medido el \d|\(\d{1,2}-[a-z]{3}-\d{4}\)|eran \d+ al|back then"
    r"|cuando son \d|recontad|se recontaron|dec[íi]a \d+ [a-záéíóúñ]+ cuando",
    re.I,
)

#: cifra de DATOS.md → cómo aparece escrita en la prosa, y qué palabras en la MISMA FRASE
#: significan que ese número es de otra fila y hay que dejarlo en paz.
#:
#: Lo tercero hizo falta el mismo día: «For Africa that means all 54 countries have their
#: emergency number» es verdad —son los 54 del continente— y el candado la señalaba como si
#: dijera que hay 54 países en total. Antes el descarte miraba 40 caracteres **después** del
#: número, y ahí «África» iba delante. Un candado que grita cuando la frase es correcta se acaba
#: ignorando, y entonces deja de servir para lo que se hizo.
#:
#: Y el fallo contrario, el mismo día: `ops/SHOW_HN.md` decía «a corpus of 288 **published**
#: documents from 18 bodies» —son 497 y 21— y el candado no lo vio, porque el patrón pedía el
#: número pegado al sustantivo y ahí había un adjetivo en medio. Un candado silencioso es peor
#: que no tener candado, porque además da confianza. De ahí `_ADJ`: hasta dos palabras entre la
#: cifra y el sustantivo, que es lo que cabe en «497 documentos públicos catalogados».
_ADJ = r"(?:\s+[a-záéíóúñ]+){0,2}\s*"

PATRONES: list[tuple[str, str, str]] = [
    (
        "países con número de emergencia",
        rf"(\d{{2,3}}){_ADJ}(?:países|paises|countries)",
        r"vacun|calendar|schedul|curva|chart|marca|brand|africa|áfrica|continente|continent"
        r"|gu[íi]a|guide|documento|document",
    ),
    (
        "calendarios de vacunas",
        rf"(\d{{1,3}}){_ADJ}(?:calendarios|vaccination schedules)"
        rf"|(?:vaccination schedules?|calendarios de vacunas)\s*(?:for|de|para)\s*(\d{{1,3}})",
        r"africa|áfrica",
    ),
    (
        "tablas de crecimiento por país",
        rf"(\d{{2,3}}){_ADJ}(?:curvas|growth charts|tablas de crecimiento)",
        r"africa|áfrica",
    ),
    ("reglas de alarma", rf"(\d{{2,3}}){_ADJ}(?:reglas de alarma|red flags|reglas fijas)", r""),
    (
        "documentos del catálogo público",
        rf"(\d{{3,4}}){_ADJ}(?:documentos|documents)",
        r"interno|internal|pasaje|passage",
    ),
    ("guías publicadas", rf"(\d{{3,4}}){_ADJ}(?:guías|guides|guias)", r""),
    (
        "marcas de medicamento",
        rf"(\d{{2,3}}){_ADJ}(?:marcas|brands)",
        r"africa|áfrica|país|countries",
    ),
]


def _frase(texto: str, ini: int, fin: int) -> str:
    """La frase que contiene el número, para poder mirar también lo que va delante."""
    abre = max(texto.rfind(".", 0, ini), texto.rfind("\n\n", 0, ini)) + 1
    cierra = texto.find(".", fin)
    return texto[abre : cierra if cierra != -1 else fin + 120]


def _verdades() -> dict[str, int]:
    from scripts.build_datos import cifras  # noqa: PLC0415

    return {k: v["n"] for k, v in cifras().items()}


def revisa(verdades: dict[str, int] | None = None) -> list[str]:
    """Las cifras que no cuadran, una por línea, con fichero y número de línea."""
    if verdades is None:
        sys.path.insert(0, str(RAIZ))
        verdades = _verdades()
    fuera: list[str] = []
    ficheros = sorted(RAIZ.glob("*.md")) + sorted((RAIZ / "ops").glob("*.md"))
    for f in ficheros:
        if f.name in DIARIOS:
            continue
        texto = f.read_text(encoding="utf-8")
        for clave, patron, ajenas in PATRONES:
            real = verdades.get(clave)
            if not real:
                continue
            for m in re.finditer(patron, texto, re.I):
                # algunos patrones tienen dos formas («66 calendarios» / «schedules for 66»), y la
                # que no ha casado deja su grupo a None.
                capturado = next((g for g in m.groups() if g), None)
                if capturado is None:
                    continue
                dicho = int(capturado)
                if dicho == real:
                    continue
                # ¿la frase habla de otra fila —África, el catálogo interno— y no de ésta?
                if ajenas and re.search(ajenas, _frase(texto, m.start(), m.end()), re.I):
                    continue
                # ¿la frase dice que esa cifra es de otro momento? Entonces es historia.
                alrededor = texto[max(0, m.start() - 90) : m.end() + 90]
                if HISTORICA.search(alrededor):
                    continue
                linea = texto[: m.start()].count("\n") + 1
                trozo = " ".join(texto[max(0, m.start() - 50) : m.end() + 20].split())
                fuera.append(
                    f"{f.relative_to(RAIZ).as_posix()}:{linea}  {clave}: dice {dicho}, "
                    f"son {real}\n    …{trozo}…"
                )
    return fuera


def main() -> int:
    sys.path.insert(0, str(RAIZ))
    verdades = _verdades()
    problemas = revisa(verdades)
    if not problemas:
        print("los .md no contradicen a los datos: nada que corregir")
        return 0
    print(f"{len(problemas)} cifras que ya no son verdad:\n")
    for p in problemas:
        print(" ", p)
    print("\nRegenera con `uv run python scripts/build_datos.py` y corrige la prosa, o")
    print("enlaza a DATOS.md en vez de repetir el número.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
