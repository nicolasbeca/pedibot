import collections
import json
import sys

rs = [json.loads(ln) for ln in open(sys.argv[1], encoding="utf-8")]
print(collections.Counter(r.get("ver") for r in rs))
print(collections.Counter(r.get("level") for r in rs))
for r in rs:
    if "error" in r:
        print("ERROR", r["i"], r["q"], r["error"][:200])
        continue
    texto = r["text"].replace("\n", " ")
    fuentes = "; ".join(s[4:50] for s in r["sources"][:2])
    print(
        f"#{r['i']} [{r['lang']} {r['level']} {r['ver']}] {r['q']}\n"
        f"   B: {r['banner'][:120]}\n   T: {texto[:260]}\n   F: {fuentes}"
    )
