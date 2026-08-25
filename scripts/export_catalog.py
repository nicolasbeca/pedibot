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


# drugs → web/site/src/data/drugs.json (I-29 static dose pages)
from pedibot.bot.dose import DRUGS  # noqa: E402
from pedibot.bot.drugs import DrugCatalog  # noqa: E402

cat = DrugCatalog(ROOT / "config" / "drugs.yaml")
drugs_out = {}
for key, info in cat.drugs.items():
    d = DRUGS[key]
    drugs_out[key] = {
        "generic": info.generic,
        "notes": info.notes,
        "source": info.source,
        "per_dose_mg_per_kg": [d.mg_per_kg_min, d.mg_per_kg_max],
        "interval_hours": list(d.interval_hours),
        "max_mg_per_kg_day": d.max_mg_per_kg_day,
        "max_single_mg": d.max_single_dose_mg,
        "max_daily_mg": d.max_daily_mg,
        "min_age_months": d.min_age_months,
        "min_weight_kg": d.min_weight_kg,
        "presentations": [{"name": p.name, "mg_per_ml": p.mg_per_ml} for p in d.presentations],
        "brands": [
            {
                "name": b.name,
                "slug": b.name.lower().split(" ")[0].split("/")[0],
                "countries": list(b.countries),
                "forms": [{"label": f, "mg_per_ml": c} for f, c in b.strengths_mg_per_ml()],
            }
            for b in info.brands
        ],
    }
target2 = ROOT / "web" / "site" / "src" / "data" / "drugs.json"
target2.write_text(json.dumps(drugs_out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(drugs_out)} drugs → {target2}")
