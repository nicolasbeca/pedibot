"""Export config/fuentes.yaml → web/site/src/data/sources.json (build-time data for the site)."""
import json
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
docs = yaml.safe_load((ROOT / "config" / "fuentes.yaml").read_text(encoding="utf-8"))["sources"]
keys = ("doc_id", "org", "org_full", "title", "year", "lang", "topic", "doc_type", "usage", "url")
out = [{k: d.get(k) for k in keys} for d in docs]
target = ROOT / "web" / "site" / "src" / "data" / "sources.json"
target.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(out)} sources → {target}")
