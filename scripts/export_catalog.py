"""Export config/fuentes.yaml → web/site/src/data/sources.json (build-time data for the site)."""

import json
import pathlib
import re
import sys

import yaml

# La consola de Windows es cp1252 y estos mensajes llevan flechas y acentos: sin esto el script
# revienta al imprimir, y `make build` no se puede ejecutar en la máquina del operador (en el
# servidor sí funciona, porque allí la salida es UTF-8 — por eso nadie lo había notado).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[1]
docs = yaml.safe_load((ROOT / "config" / "fuentes.yaml").read_text(encoding="utf-8"))["sources"]
_web = ROOT / "config" / "fuentes_web.yaml"
if _web.exists():
    docs += (yaml.safe_load(_web.read_text(encoding="utf-8")) or {}).get("sources", [])
keys = (
    "doc_id",
    "org",
    "org_full",
    "title",
    "year",
    "lang",
    "topic",
    "doc_type",
    "usage",
    "url",
    "notes",
)
out = [{k: d.get(k) for k in keys} for d in docs]
target = ROOT / "web" / "site" / "src" / "data" / "sources.json"
body = json.dumps(out, ensure_ascii=False, indent=1)
target.write_text(body, encoding="utf-8")
# also served as a plain file: it is the provenance of every answer, and other agents buy
# from us precisely because they can check where the material comes from (ACP resource)
public = ROOT / "web" / "site" / "public" / "sources.json"
public.write_text(body, encoding="utf-8")
print(f"{len(out)} sources → {target} + {public}")


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

# ER checklist → web/site/src/data/checklist.json (I-02 static page)
raw = yaml.safe_load((ROOT / "config" / "er_checklist.yaml").read_text(encoding="utf-8"))
target3 = ROOT / "web" / "site" / "src" / "data" / "checklist.json"
target3.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(raw['items'])} checklist items → {target3}")

# same-subject topic pairs → web/site/src/data/same_subject.json
# `topic` is what the language switcher matches on, and the same subject has two keys when the
# English guide was anchored on English sources (constipation/estrenimiento, otitis/ear_infection).
# The generator has always known this; without exporting it the site showed no twins for them.
import sys as _sys  # noqa: E402 — deliberate: it needs ROOT, which is computed above

_sys.path.insert(0, str(ROOT / "src"))
from pedibot.publish.articles import SAME_SUBJECT  # noqa: E402

target_same = ROOT / "web" / "site" / "src" / "data" / "same_subject.json"
target_same.write_text(
    json.dumps([sorted(pair) for pair in SAME_SUBJECT], ensure_ascii=False, indent=1) + "\n",
    encoding="utf-8",
)
print(f"{len(SAME_SUBJECT)} same-subject pairs → {target_same}")

# vaccines → web/site/src/data/vaccines.json (VaccinesTool)
vraw = yaml.safe_load((ROOT / "config" / "vaccines.yaml").read_text(encoding="utf-8"))["countries"]
target4 = ROOT / "web" / "site" / "src" / "data" / "vaccines.json"
target4.write_text(json.dumps(vraw, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(vraw)} vaccine schedules → {target4}")


# tablas de crecimiento por país → web/site/src/data/growth_charts.json (páginas /growth/{país})
graw = yaml.safe_load((ROOT / "config" / "growth_charts.yaml").read_text(encoding="utf-8"))["countries"]
target_g = ROOT / "web" / "site" / "src" / "data" / "growth_charts.json"
target_g.write_text(json.dumps(graw, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(graw)} growth-chart countries → {target_g}")


# países con número de emergencia → web/site/src/data/countries.json (el desplegable del chat)
# El desplegable era un array escrito a mano dentro de Chat.astro, y se había quedado corto: los
# números conocían 31 países y el selector ofrecía 29. Perú tenía su número puesto y ningún padre
# peruano podía elegirlo, así que siempre recibía la frase genérica (7-sep-2026). Derivado, no
# copiado: un país nuevo en la configuración aparece solo en la web.
numeros = yaml.safe_load((ROOT / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8"))
paises = sorted(k for k in numeros if k != "default")
target5 = ROOT / "web" / "site" / "src" / "data" / "countries.json"
target5.write_text(json.dumps(paises, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"countries.json: {len(paises)} países con número de emergencia")

# El número, no sólo el código → web/site/src/data/emergency.json (la tira «tu país» de la
# portada, 11-sep-2026). Hasta hoy la web sabía QUÉ países conocemos pero no su número, así que
# la portada no podía decirle a un padre en Delhi ni en El Cairo lo único que de verdad hace
# falta a las tres de la mañana. Mismo fichero de origen, así que no pueden desviarse.
emergencias = {
    k: {
        "emergency": v.get("emergency"),
        "poison": v.get("poison"),
        "mental": v.get("mental"),
        # 18-sep-2026, con África: la letra pequeña y los dos casos que en Europa no se daban.
        # `no_national` es «la fuente dice que no existe número nacional» (RD del Congo, Gambia,
        # Liberia, Sudán del Sur, Congo, Comoras, Guinea) y `unverified` es «no hemos podido
        # verificarlo» (Zambia). No son lo mismo y la página no dice lo mismo en cada caso.
        "note": v.get("note"),
        "no_national": bool(v.get("no_national")),
        "unverified": bool(v.get("unverified")),
        # de dónde sale el número. Los 48 africanos vienen del aviso de viaje del FCDO
        # británico, que NO es la fuente nacional de cada país, y la página tiene que decirlo:
        # es el mismo «fuente o silencio» que gobierna las guías (18-sep-2026).
        "source": v.get("source"),
        "source_url": v.get("source_url"),
    }
    for k, v in numeros.items()
    if k != "default"
}
target8 = ROOT / "web" / "site" / "src" / "data" / "emergency.json"
target8.write_text(json.dumps(emergencias, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
print(f"emergency.json: {len(emergencias)} países con su número")

# idioma → países donde se habla → web/site/src/data/lang_countries.json (17-sep-2026).
#
# La portada enseñaba un desplegable de 35 códigos con «GB» puesto de antemano: quien entraba en
# español tenía que buscarse España dentro de la lista para ver su número. Con esto, cada idioma
# abre con los países en los que se habla, escritos y sin desplegar nada.
idiomas = yaml.safe_load((ROOT / "config" / "lang_countries.yaml").read_text(encoding="utf-8"))
desconocidos = sorted({c for cs in idiomas.values() for c in cs} - set(emergencias))
assert not desconocidos, f"lang_countries.yaml nombra países sin número: {desconocidos}"
target9 = ROOT / "web" / "site" / "src" / "data" / "lang_countries.json"
target9.write_text(json.dumps(idiomas, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
print(f"lang_countries.json: {sum(len(v) for v in idiomas.values())} países en {len(idiomas)} idiomas")


# tema → categoría de la taxonomía → web/site/src/data/topic_category.json
#
# Para los enlaces entre guías (9-sep-2026). `relatedTo` agrupaba por `topic` exacto, y cada tema
# tiene UNA sola guía por idioma, así que el grupo salía siempre vacío y el sustituto eran «las
# tres más recientes» — las mismas para las sesenta guías de la lengua. Medido: 390 de las 483
# guías recibían un único enlace interno (el índice de su idioma) y 24 recibían más de sesenta.
# Search Console lo decía de la guía portuguesa de la meningitis: «no se ha detectado ninguna
# página de referencia».
#
# La categoría sale del mismo clasificador que usa la ingesta, no de una lista nueva: se le pasa
# el tema junto con los títulos que ese tema tiene en castellano e inglés, que es bastante texto
# para que las palabras clave de la taxonomía enganchen.
from pedibot.ingest.classify import Taxonomy  # noqa: E402

tax = Taxonomy(ROOT / "config" / "taxonomia.yaml")
textos: dict[str, list[str]] = {}
for md in sorted((ROOT / "web" / "content").rglob("*.md")):
    cab = md.read_text(encoding="utf-8")[:2000]
    mt = re.search(r"^topic:\s*(.+)$", cab, re.M)
    if not mt:
        continue
    tema = mt.group(1).strip()
    trozos = [tema.replace("_", " ")]
    if md.parent.name in ("es", "en"):
        for campo in ("title", "description"):
            mv = re.search(rf'^{campo}:\s*"?(.+?)"?\s*$', cab, re.M)
            if mv:
                trozos.append(mv.group(1))
    textos.setdefault(tema, []).extend(trozos)

categorias = {}
for tema, trozos in sorted(textos.items()):
    cat = tax.topic_for(" ".join(trozos))
    if cat:
        categorias[tema] = cat
target6 = ROOT / "web" / "site" / "src" / "data" / "topic_category.json"
target6.write_text(json.dumps(categorias, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
sin = sorted(t for t in textos if t not in categorias)
print(f"topic_category.json: {len(categorias)} temas clasificados, {len(sin)} sin categoría")
if sin:
    print("  sin categoría:", ", ".join(sin[:12]))

# ---------------------------------------------------------------------------------------------
# dose_table.json — la dosis de paracetamol por peso, PRECALCULADA con el módulo de verdad.
#
# La portada lleva un deslizador de peso (11-sep-2026). Había tres formas de hacerlo y dos eran
# malas: llamar a `/api/dose` en cada movimiento gasta el límite de 20 peticiones por IP y deja
# al padre sin poder preguntar después; y calcularlo en JavaScript sería una **segunda
# implementación de un cálculo clínico**, que puede desviarse de la primera sin que nadie lo vea.
# Así que la calcula Python con `bot.dose.calculate` y el navegador sólo consulta la tabla.
#
# Sólo paracetamol: sin edad, el ibuprofeno se niega a dar cifra (`refer=True`, `age_unknown`),
# y un deslizador de peso no sabe la edad. Para eso está la calculadora entera, enlazada al lado.
from pedibot.bot.dose import calculate  # noqa: E402

PESOS = [round(4 + 0.5 * i, 1) for i in range(int((40 - 4) / 0.5) + 1)]
PRESENTACIONES = ["jarabe 120 mg/5 ml", "gotas 100 mg/ml"]

filas = {}
for kg in PESOS:
    r = calculate("paracetamol", float(kg), None)
    filas[str(kg)] = {
        "mg": r.mg,
        "ml": {p: r.ml[p] for p in PRESENTACIONES if p in r.ml},
        "refer": r.refer,
    }
target7 = ROOT / "web" / "site" / "src" / "data" / "dose_table.json"
target7.write_text(
    json.dumps(
        {
            "drug": "paracetamol",
            "source": calculate("paracetamol", 10.0, None).drug.source,
            "interval_hours": list(calculate("paracetamol", 10.0, None).interval_hours),
            "presentations": PRESENTACIONES,
            "rows": filas,
        },
        ensure_ascii=False,
        indent=1,
    )
    + "\n",
    encoding="utf-8",
)
print(f"dose_table.json: {len(filas)} pesos de paracetamol, {len(PRESENTACIONES)} presentaciones")
