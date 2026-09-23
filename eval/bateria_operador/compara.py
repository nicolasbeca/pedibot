import collections
import json
import sys

a = {r["i"]: r for r in map(json.loads, open(sys.argv[1], encoding="utf-8"))}
b = {r["i"]: r for r in map(json.loads, open(sys.argv[2], encoding="utf-8"))}
print("antes:", collections.Counter(r.get("ver") for r in a.values()))
print("ahora:", collections.Counter(r.get("ver") for r in b.values()))
print("antes:", collections.Counter(r.get("level") for r in a.values()))
print("ahora:", collections.Counter(r.get("level") for r in b.values()))
for i in sorted(b):
    x, y = a.get(i, {}), b[i]
    if (x.get("level"), x.get("ver")) != (y.get("level"), y.get("ver")):
        print(
            f"#{i} {x.get('level')}/{x.get('ver')} → {y.get('level')}/{y.get('ver')}  {y['q'][:80]}"
        )
