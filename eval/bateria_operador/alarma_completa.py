"""¿Llega entera la lista de «cuándo consultar»? (8-oct-2026)

Al preparar el ejemplo para el BIÖG salió que el redactor recorta su lista de «Wann bei Erbrechen
ein Arztbesuch dringend ist»: de siete motivos, en cada tirada se caían uno o tres distintos. El
prompt v12 pide «when to get help: one sentence», y siete motivos no caben en una frase.

Este juez lee, para cada respuesta de una batería, el pasaje de signos de alarma que tuvo delante
el redactor (`is_red_flag` entre sus `chunk_ids`) y cuenta qué motivos de ese pasaje aplican a ESTE
niño y cuáles llegaron a la respuesta. Y de paso, si la respuesta suaviza lo que dice la guía
(«oft harmlose Ursachen» → «meist harmlos»).

    uv run python eval/bateria_operador/alarma_completa.py r69_reglas.jsonl a69.jsonl
    uv run python eval/bateria_operador/alarma_completa.py --resumen a69.jsonl
"""

from __future__ import annotations

import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from pedibot.bot.llm import provider_from_settings

SYSTEM = """You check whether an answer to a parent kept the "when to get medical help" list of its source.

You get the parent's MESSAGE, the WARNING PASSAGE the writer had (a list of reasons to see a doctor or go to the emergency department, from an official guideline), and the ANSWER.

1. List every distinct reason to get medical help that the passage gives (a sign, a situation, an age).
2. For each, say whether it can apply to THIS child, given what the message says (age, symptoms). "Is under 3 months" cannot apply to a 4-year-old; a sign about a different symptom than the one asked about still applies if the passage is about the same illness. When in doubt, it applies.
3. For each, say whether the ANSWER conveys it (same meaning, any wording or language).
4. Say whether the answer SOFTENS anything the passage or its guideline says: makes a risk sound smaller ("often" -> "usually", "may be serious" -> "rarely serious"), turns "go now" into "if it continues", or adds reassurance the passage does not give.

Reply with JSON only:
{"items": [{"reason": "<short, English>", "applies": true|false, "in_answer": true|false}], "softens": true|false, "softens_quote": "<the answer's words, or empty>"}"""

_CANDADO = threading.Lock()
_IX = None


def _indice():  # noqa: ANN202
    global _IX
    if _IX is None:
        from pedibot.index.store import Index
        from pedibot.settings import get_settings

        _IX = Index(get_settings().index_db_path)
    return _IX


def pasaje_de_alarma(ids: list[str]) -> str | None:
    with _CANDADO:
        for cid in ids:
            c = _indice().get(cid)
            if c is not None and c.is_red_flag:
                return f"{c.org} — {c.doc_title} — {c.section}:\n{c.text[:2500]}"
    return None


def juzga(llm, r: dict) -> dict | None:  # noqa: ANN001
    if r.get("error") or not r.get("chunk_ids"):
        return None
    p = pasaje_de_alarma(r["chunk_ids"])
    if p is None:
        return None
    user = f"MESSAGE:\n{r['q']}\n\nWARNING PASSAGE:\n{p}\n\nANSWER:\n{(r.get('text') or '')[:3000]}"
    try:
        res = llm.complete(SYSTEM, user, temperature=0.0, max_tokens=900)
        m = re.search(r"\{.*\}", res.text or "", re.S)
        j = json.loads(m.group(0)) if m else {"error": "sin json"}
    except Exception as e:  # noqa: BLE001
        j = {"error": repr(e)}
    return {"i": r["i"], "q": r["q"], "level": r.get("level"), "alarma": j}


def resumen(path: str) -> dict:
    rs = [json.loads(ln) for ln in open(path, encoding="utf-8")]
    ok = [r for r in rs if "items" in r["alarma"]]
    aplican = [[x for x in r["alarma"]["items"] if x.get("applies")] for r in ok]
    con_lista = [a for a in aplican if a]
    total = sum(len(a) for a in con_lista)
    dichos = sum(sum(1 for x in a if x.get("in_answer")) for a in con_lista)
    incompletas = sum(1 for a in con_lista if not all(x.get("in_answer") for x in a))
    suaviza = sum(1 for r in ok if r["alarma"].get("softens"))
    out = {
        "juzgadas": len(ok),
        "con_motivos_que_aplican": len(con_lista),
        "motivos": total,
        "motivos_dichos": dichos,
        "pct_dichos": round(100 * dichos / total, 1) if total else None,
        "respuestas_incompletas": incompletas,
        "suavizan": suaviza,
    }
    print(json.dumps(out, ensure_ascii=False))
    return out


def main() -> int:
    if sys.argv[1] == "--resumen":
        for p in sys.argv[2:]:
            print(p, end=": ")
            resumen(p)
        return 0
    entrada, salida = sys.argv[1], sys.argv[2]
    rs = [json.loads(ln) for ln in open(entrada, encoding="utf-8")]
    llm = provider_from_settings()
    with ThreadPoolExecutor(8) as ex, open(salida, "w", encoding="utf-8") as f:
        for out in ex.map(lambda r: juzga(llm, r), rs):
            if out is not None:
                f.write(json.dumps(out, ensure_ascii=False) + "\n")
    resumen(salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
