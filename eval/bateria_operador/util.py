"""¿Le sirve al padre? Un juez con modelo para las baterías (5-oct-2026).

El revisor de siempre (`revisor.py`) pregunta si la respuesta es segura: alarma bien puesta, sin
relleno, sin veredictos inventados, en la lengua del padre. Las dos respuestas reales del 5-oct a
un padre alemán —vómitos y signos de deshidratación— pasaban todo eso y no servían: no decían qué
hacer y la lista de signos se quedaba en dos. Este juez pregunta lo que faltaba:

- `helps` 0-3: si con esa respuesta el padre sabe qué hacer ahora y qué vigilar;
- `missing`: lo que una enfermera pediátrica esperaría y no está (máximo cuatro puntos);
- `wrong`: errores de hecho o de seguridad;
- `units_ok` / `country_ok`: sus unidades (°F, lb) y su país (sus marcas, su calendario, su
  número), sin darle por suyo lo de otro país.

Y uno sin modelo: en qué lengua están las fuentes citadas, comparada con la de la pregunta.

    uv run --env-file .env python eval/bateria_operador/util.py respuestas.jsonl juicio.jsonl

Lo marcado se lee a mano. El juez es el mismo modelo que escribe: sirve para ordenar la lectura,
no para aprobar nada.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from pedibot.bot.llm import provider_from_settings
from pedibot.bot.retrieval import detect_lang
from pedibot.settings import ROOT

SYSTEM = """You judge answers from a children's health chatbot for parents. It must answer ONLY
from cited official guidance, so it may legitimately leave things out when its sources do not
cover them — but judge what the PARENT gets. You receive the parent's MESSAGE (and earlier turns
if any), the parent's COUNTRY if known, the WARNING LEVEL and BANNER shown above the answer, the
ANSWER TEXT and its SOURCES. Return ONLY a JSON object:
  "helps": 0-3. 3 = after reading it the parent knows what to do now, what to watch for and when
      to get help, for THIS situation. 2 = useful but with a gap. 1 = mostly generic or beside the
      point. 0 = useless or harmful.
  "missing": up to 4 short items a careful paediatric nurse would expect in an answer to THIS
      message and that are absent (e.g. "oral rehydration solution in small frequent sips",
      "signs: no tears, dry mouth, no urine for 8 hours"). [] if none.
  "wrong": short items that are factually wrong or unsafe. [] if none.
  "units_ok": false if the parent used °F, pounds or ounces and the answer ignores them or only
      gives °C/kg without converting; true otherwise.
  "country_ok": false if the answer presents another country's schedule, brands, services or
      emergency number as the parent's own; true otherwise (also when no country is known).
  "urgency_ok": false if the warning level is clearly too low for a dangerous sign or clearly too
      high for something benign; true otherwise.
  "note": one short sentence in Spanish with the main problem, or "".
Be strict about usefulness and concrete about what is missing. Do not rewrite the answer."""

#: Lo que no es una respuesta de salud y no se juzga aquí: preguntas sobre PediBot, aclaraciones
#: pedidas, fuera de tema y lo que no encontró fuente (eso ya se cuenta aparte).
SIN_JUICIO = ("about", "clarify", "off_topic")


def _titulos(sources: list[str]) -> list[str]:
    # `correr.py` corta cada fuente a 90 caracteres: el título puede quedarse sin comilla de cierre
    return [m.group(1) for s in sources for m in [re.search(r"[\"“”]([^\"“”]{4,})(?:[\"“”]|$)", s)] if m]


def _normal(t: str) -> str:
    return re.sub(r"\W+", "", t.replace("­", "")).lower()


#: La lengua de cada fuente sale del catálogo, por su título: adivinarla por el título se
#: equivoca con los cortos («Norovirus-Gastroenteritis» del RKI salía inglés).
_CATALOGO = {
    _normal(s["title"]): s["lang"]
    for s in json.load(open(ROOT / "dataset" / "sources.json", encoding="utf-8"))
}


def _lengua(titulo: str) -> str:
    t = _normal(titulo)
    for k, lang in _CATALOGO.items():
        if k == t or (len(t) > 12 and k.startswith(t[:40])):
            return lang
    return detect_lang(titulo)


def lengua_fuentes(r: dict) -> dict[str, object]:
    """Cuántas fuentes citadas están en la lengua de la pregunta."""
    titulos = _titulos(r.get("sources") or [])
    lenguas = [_lengua(t) for t in titulos]
    return {"src_langs": lenguas, "own_lang_src": sum(1 for x in lenguas if x == r.get("lang"))}


def juzga(llm, r: dict, antes: list[dict]) -> dict:  # noqa: ANN001
    extra = lengua_fuentes(r)
    if r.get("error") or r.get("ver") in SIN_JUICIO:
        return {**r, **extra, "util": {"skip": True}}
    previas = "".join(f"EARLIER MESSAGE: {a['q']}\nEARLIER ANSWER: {a.get('text', '')[:800]}\n\n" for a in antes)
    user = (
        f"{previas}MESSAGE:\n{r['q']}\n\nCOUNTRY: {r.get('pais') or 'unknown'}\n"
        f"WARNING LEVEL: {r.get('level')}\nBANNER: {r.get('banner') or '(none)'}\n\n"
        f"ANSWER TEXT:\n{(r.get('text') or '')[:3000]}\n\nSOURCES:\n" + "\n".join(r.get("sources") or [])
    )
    try:
        res = llm.complete(SYSTEM, user, temperature=0.0, max_tokens=500)
        m = re.search(r"\{.*\}", res.text or "", re.S)
        util = json.loads(m.group(0)) if m else {"error": "sin json"}
    except Exception as e:  # noqa: BLE001
        util = {"error": repr(e)}
    return {**r, **extra, "util": util}


def main() -> int:
    entrada, salida = sys.argv[1], sys.argv[2]
    rs = [json.loads(ln) for ln in open(entrada, encoding="utf-8")]
    llm = provider_from_settings()
    trabajos = []
    for k, r in enumerate(rs):
        antes = []
        j = k
        while r.get("sigue") and j > 0 and rs[j - 1]["i"] == r["i"]:
            j -= 1
            antes.insert(0, rs[j])
            if not rs[j].get("sigue"):
                break
        trabajos.append((r, antes))
    with ThreadPoolExecutor(8) as ex, open(salida, "w", encoding="utf-8") as f:
        for out in ex.map(lambda t: juzga(llm, *t), trabajos):
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
    resumen(salida)
    return 0


def resumen(path: str) -> None:
    rs = [json.loads(ln) for ln in open(path, encoding="utf-8")]
    juzgadas = [r for r in rs if not r["util"].get("skip") and "error" not in r["util"]]
    print(f"respuestas: {len(rs)} · juzgadas: {len(juzgadas)}")
    print("por verificación:", dict(collections.Counter(r.get("ver") for r in rs)))
    notas = collections.Counter(r["util"].get("helps") for r in juzgadas)
    print("helps:", dict(sorted(notas.items(), key=lambda kv: str(kv[0]))))
    for campo in ("units_ok", "country_ok", "urgency_ok"):
        print(f"{campo} = false:", sum(1 for r in juzgadas if r["util"].get(campo) is False))
    print("con algo 'wrong':", sum(1 for r in juzgadas if r["util"].get("wrong")))
    por_lengua: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rs:
        por_lengua[r.get("lang") or "?"].append(r)
    print("\nlengua  n  helps≤1  sin_fuente  sin_fuente_propia")
    for lang, grupo in sorted(por_lengua.items(), key=lambda kv: -len(kv[1])):
        j = [r for r in grupo if r in juzgadas]
        flojas = sum(1 for r in j if (r["util"].get("helps") or 0) <= 1)
        sin = sum(1 for r in grupo if r.get("ver") == "no_source")
        ajena = sum(1 for r in grupo if r.get("sources") and not r.get("own_lang_src"))
        print(f"{lang:6} {len(grupo):3} {flojas:7} {sin:10} {ajena:16}")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        resumen(sys.argv[1])
    else:
        raise SystemExit(main())
