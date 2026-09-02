"""Download curated public parent-facing pages (NHS OGL, CDC/MedlinePlus public domain, WHO CC BY-NC-SA)
into FUENTES/web/<doc_id>.html and write their catalog entries to config/fuentes_web.yaml.

Idempotent: existing files are not re-downloaded unless --force. Only URLs listed in WEB_SOURCES
are fetched — no crawling. Each entry records organisation, licence and language for the catalog.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sys
import time

import httpx
import yaml
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "FUENTES" / "web"
CATALOG = ROOT / "config" / "fuentes_web.yaml"
UA = "Mozilla/5.0 (compatible; PediBot-source-fetch/1.0; +https://pedibot.xyz)"

ORGS = {
    "nhs": {
        "org": "NHS",
        "org_full": "NHS (National Health Service, England)",
        "license": "Open Government Licence v3.0",
        "evidence": "organismo_publico",
        "usage": "publico",
    },
    "mlp": {
        "org": "MedlinePlus",
        "org_full": "MedlinePlus (U.S. National Library of Medicine)",
        "license": "Public domain (U.S. Government work; health-topic summaries)",
        "evidence": "organismo_publico",
        "usage": "publico",
    },
    "cdc": {
        "org": "CDC",
        "org_full": "Centers for Disease Control and Prevention (USA)",
        "license": "Public domain (U.S. Government work)",
        "evidence": "organismo_publico",
        "usage": "publico",
    },
    "canada": {
        "org": "Gouvernement du Canada",
        "org_full": "Gouvernement du Canada / Government of Canada (santé publique)",
        "license": "Reproduction non commerciale autorisée sans permission, avec exactitude, titre, auteur et URL d'origine (Avis, canada.ca)",
        "evidence": "organismo_publico",
        "usage": "publico",
    },
    "who": {
        "org": "WHO",
        "org_full": "World Health Organization",
        "license": "CC BY-NC-SA 3.0 IGO",
        "evidence": "organismo_publico",
        "usage": "publico",
    },
}

# (key, url, topic, lang, age_groups)
WEB_SOURCES: list[tuple[str, str, str, str, list[str]]] = [
    # ---------------- NHS (England) ----------------
    ("nhs", "https://www.nhs.uk/conditions/fever-in-children/", "fiebre", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/bronchiolitis/", "respiratorio", "en", ["lactante"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/croup/",
        "respiratorio",
        "en",
        ["lactante", "preescolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/febrile-seizures/",
        "neurologia",
        "en",
        ["lactante", "preescolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/head-injury-and-concussion/",
        "accidentes",
        "en",
        ["todas"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/diarrhoea-and-vomiting/", "digestivo", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/constipation/", "digestivo", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/dehydration/", "digestivo", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/norovirus/", "digestivo", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/chickenpox/", "piel", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/hand-foot-mouth-disease/",
        "piel",
        "en",
        ["lactante", "preescolar"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/meningitis/", "urgencias", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/sepsis/", "urgencias", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/rashes-babies-and-children/",
        "piel",
        "en",
        ["lactante", "preescolar"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/colic/", "lactante", "en", ["lactante"]),
    ("nhs", "https://www.nhs.uk/conditions/reflux-in-babies/", "lactante", "en", ["lactante"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/baby/babys-development/teething/baby-teething-symptoms/",
        "lactante",
        "en",
        ["lactante"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/ear-infections/", "orl", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/glue-ear/", "orl", "en", ["preescolar", "escolar"]),
    ("nhs", "https://www.nhs.uk/conditions/sore-throat/", "orl", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/tonsillitis/", "orl", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/scarlet-fever/",
        "piel",
        "en",
        ["preescolar", "escolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/slapped-cheek-syndrome/",
        "piel",
        "en",
        ["preescolar", "escolar"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/impetigo/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/molluscum-contagiosum/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/roseola/", "piel", "en", ["lactante", "preescolar"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/threadworms/",
        "digestivo",
        "en",
        ["preescolar", "escolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/urinary-tract-infections-utis/",
        "general",
        "en",
        ["todas"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/burns-and-scalds/", "accidentes", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/poisoning/", "intoxicacion", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/asthma/", "respiratorio", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/respiratory-syncytial-virus-rsv/",
        "respiratorio",
        "en",
        ["lactante"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/pneumonia/", "respiratorio", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/flu/", "respiratorio", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/whooping-cough/", "respiratorio", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/measles/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/mumps/", "general", "en", ["escolar"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/vaccinations/nhs-vaccinations-and-when-to-have-them/",
        "vacunas",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/baby/weaning-and-feeding/babys-first-solid-foods/",
        "alimentacion",
        "en",
        ["lactante"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/baby/caring-for-a-newborn/",
        "recien_nacido",
        "en",
        ["lactante"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/anaphylaxis/", "alergia", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/food-allergy/", "alergia", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/hives/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/conjunctivitis/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/nosebleed/", "accidentes", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/heat-exhaustion-heatstroke/",
        "accidentes",
        "en",
        ["todas"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/sunburn/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/insect-bites-and-stings/", "piel", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/headaches-in-children/",
        "neurologia",
        "en",
        ["escolar", "adolescente"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/breath-holding-in-babies-and-children/",
        "neurologia",
        "en",
        ["lactante", "preescolar"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/head-lice-and-nits/", "piel", "en", ["escolar"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/bedwetting/",
        "desarrollo",
        "en",
        ["preescolar", "escolar"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/growing-pains/", "general", "en", ["escolar"]),
    ("nhs", "https://www.nhs.uk/conditions/cradle-cap/", "piel", "en", ["lactante"]),
    (
        "nhs",
        "https://www.nhs.uk/medicines/paracetamol-for-children/",
        "medicamentos",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/medicines/ibuprofen-for-children/",
        "medicamentos",
        "en",
        ["todas"],
    ),
    # ---------------- MedlinePlus EN ----------------
    ("mlp", "https://medlineplus.gov/fever.html", "fiebre", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/commoncold.html", "respiratorio", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/cough.html", "respiratorio", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/croup.html", "respiratorio", "en", ["lactante", "preescolar"]),
    ("mlp", "https://medlineplus.gov/gastroenteritis.html", "digestivo", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/diarrhea.html", "digestivo", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/dehydration.html", "digestivo", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/constipation.html", "digestivo", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/seizures.html", "neurologia", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/headinjuries.html", "accidentes", "en", ["todas"]),
    (
        "mlp",
        "https://medlineplus.gov/concussion.html",
        "accidentes",
        "en",
        ["escolar", "adolescente"],
    ),
    ("mlp", "https://medlineplus.gov/choking.html", "accidentes", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/burns.html", "accidentes", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/poisoning.html", "intoxicacion", "en", ["todas"]),
    (
        "mlp",
        "https://medlineplus.gov/infantandnewborncare.html",
        "recien_nacido",
        "en",
        ["lactante"],
    ),
    (
        "mlp",
        "https://medlineplus.gov/infantandnewbornnutrition.html",
        "alimentacion",
        "en",
        ["lactante"],
    ),
    ("mlp", "https://medlineplus.gov/breastfeeding.html", "alimentacion", "en", ["lactante"]),
    ("mlp", "https://medlineplus.gov/childdevelopment.html", "desarrollo", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/childhoodimmunization.html", "vacunas", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/earinfections.html", "orl", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/sorethroat.html", "orl", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/chickenpox.html", "piel", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/rashes.html", "piel", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/asthmainchildren.html", "respiratorio", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/toddlerhealth.html", "crianza", "en", ["preescolar"]),
    ("mlp", "https://medlineplus.gov/childsafety.html", "accidentes", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/heatillness.html", "accidentes", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/foodallergy.html", "alergia", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/allergy.html", "alergia", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/pneumonia.html", "respiratorio", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/whoopingcough.html", "respiratorio", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/measles.html", "piel", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/meningitis.html", "urgencias", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/urinarytractinfections.html", "general", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/eczema.html", "piel", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/pinkeye.html", "general", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/headlice.html", "piel", "en", ["escolar"]),
    ("mlp", "https://medlineplus.gov/sunexposure.html", "piel", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/insectbitesandstings.html", "piel", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/autismspectrumdisorder.html", "desarrollo", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/teenmentalhealth.html", "salud_mental", "en", ["adolescente"]),
    ("mlp", "https://medlineplus.gov/suicide.html", "salud_mental", "en", ["adolescente"]),
    ("mlp", "https://medlineplus.gov/selfharm.html", "salud_mental", "en", ["adolescente"]),
    ("mlp", "https://medlineplus.gov/eatingdisorders.html", "salud_mental", "en", ["adolescente"]),
    ("mlp", "https://medlineplus.gov/childrenshealth.html", "crianza", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/headache.html", "neurologia", "en", ["todas"]),
    (
        "mlp",
        "https://medlineplus.gov/fainting.html",
        "neurologia",
        "en",
        ["escolar", "adolescente"],
    ),
    ("mlp", "https://medlineplus.gov/impetigo.html", "piel", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/pinworms.html", "digestivo", "en", ["preescolar", "escolar"]),
    (
        "mlp",
        "https://medlineplus.gov/bedwetting.html",
        "desarrollo",
        "en",
        ["preescolar", "escolar"],
    ),
    # ---------------- MedlinePlus ES (LatAm-friendly Spanish) ----------------
    ("mlp", "https://medlineplus.gov/spanish/fever.html", "fiebre", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/commoncold.html", "respiratorio", "es", ["todas"]),
    (
        "mlp",
        "https://medlineplus.gov/spanish/croup.html",
        "respiratorio",
        "es",
        ["lactante", "preescolar"],
    ),
    ("mlp", "https://medlineplus.gov/spanish/gastroenteritis.html", "digestivo", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/diarrhea.html", "digestivo", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/dehydration.html", "digestivo", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/headinjuries.html", "accidentes", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/choking.html", "accidentes", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/burns.html", "accidentes", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/poisoning.html", "intoxicacion", "es", ["todas"]),
    (
        "mlp",
        "https://medlineplus.gov/spanish/infantandnewborncare.html",
        "recien_nacido",
        "es",
        ["lactante"],
    ),
    (
        "mlp",
        "https://medlineplus.gov/spanish/infantandnewbornnutrition.html",
        "alimentacion",
        "es",
        ["lactante"],
    ),
    (
        "mlp",
        "https://medlineplus.gov/spanish/breastfeeding.html",
        "alimentacion",
        "es",
        ["lactante"],
    ),
    (
        "mlp",
        "https://medlineplus.gov/spanish/childhoodimmunization.html",
        "vacunas",
        "es",
        ["todas"],
    ),
    ("mlp", "https://medlineplus.gov/spanish/earinfections.html", "orl", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/chickenpox.html", "piel", "es", ["todas"]),
    (
        "mlp",
        "https://medlineplus.gov/spanish/asthmainchildren.html",
        "respiratorio",
        "es",
        ["todas"],
    ),
    ("mlp", "https://medlineplus.gov/spanish/toddlerhealth.html", "crianza", "es", ["preescolar"]),
    ("mlp", "https://medlineplus.gov/spanish/childsafety.html", "accidentes", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/heatillness.html", "accidentes", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/measles.html", "piel", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/meningitis.html", "urgencias", "es", ["todas"]),
    (
        "mlp",
        "https://medlineplus.gov/spanish/teenmentalhealth.html",
        "salud_mental",
        "es",
        ["adolescente"],
    ),
    ("mlp", "https://medlineplus.gov/spanish/childrenshealth.html", "crianza", "es", ["todas"]),
    # ---------------- CDC ----------------
    (
        "cdc",
        "https://www.cdc.gov/vaccines/imz-schedules/child-easyread.html",
        "vacunas",
        "en",
        ["todas"],
    ),
    ("cdc", "https://www.cdc.gov/rsv/about/index.html", "respiratorio", "en", ["lactante"]),
    (
        "cdc",
        "https://www.cdc.gov/rsv/infants-young-children/index.html",
        "respiratorio",
        "en",
        ["lactante"],
    ),
    (
        "cdc",
        "https://www.cdc.gov/hand-foot-mouth/about/index.html",
        "piel",
        "en",
        ["lactante", "preescolar"],
    ),
    ("cdc", "https://www.cdc.gov/flu/highrisk/children.htm", "respiratorio", "en", ["todas"]),
    (
        "cdc",
        "https://www.cdc.gov/heads-up/about/index.html",
        "accidentes",
        "en",
        ["escolar", "adolescente"],
    ),
    (
        "cdc",
        "https://www.cdc.gov/heads-up/signs-symptoms/index.html",
        "accidentes",
        "en",
        ["escolar", "adolescente"],
    ),
    (
        "cdc",
        "https://www.cdc.gov/act-early/milestones/index.html",
        "desarrollo",
        "en",
        ["lactante", "preescolar"],
    ),
    ("cdc", "https://www.cdc.gov/drowning/prevention/index.html", "accidentes", "en", ["todas"]),
    (
        "cdc",
        "https://www.cdc.gov/infant-toddler-nutrition/index.html",
        "alimentacion",
        "en",
        ["lactante", "preescolar"],
    ),
    (
        "cdc",
        "https://www.cdc.gov/child-development/positive-parenting-tips/index.html",
        "crianza",
        "en",
        ["todas"],
    ),
    ("cdc", "https://www.cdc.gov/rotavirus/about/index.html", "digestivo", "en", ["lactante"]),
    ("cdc", "https://www.cdc.gov/norovirus/about/index.html", "digestivo", "en", ["todas"]),
    ("cdc", "https://www.cdc.gov/pertussis/about/index.html", "respiratorio", "en", ["todas"]),
    ("cdc", "https://www.cdc.gov/measles/signs-symptoms/index.html", "piel", "en", ["todas"]),
    ("cdc", "https://www.cdc.gov/chickenpox/about/index.html", "piel", "en", ["todas"]),
    ("cdc", "https://www.cdc.gov/lice/about/index.html", "piel", "en", ["escolar"]),
    ("cdc", "https://www.cdc.gov/antibiotic-use/ear-infection.html", "orl", "en", ["todas"]),
    ("cdc", "https://www.cdc.gov/antibiotic-use/colds.html", "respiratorio", "en", ["todas"]),
    # ---------------- WHO ----------------
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/infant-and-young-child-feeding",
        "alimentacion",
        "en",
        ["lactante"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/infant-and-young-child-feeding",
        "alimentacion",
        "es",
        ["lactante"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/diarrhoeal-disease",
        "digestivo",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/diarrhoeal-disease",
        "digestivo",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/pneumonia",
        "respiratorio",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/pneumonia",
        "respiratorio",
        "es",
        ["todas"],
    ),
    ("who", "https://www.who.int/news-room/fact-sheets/detail/measles", "piel", "en", ["todas"]),
    ("who", "https://www.who.int/es/news-room/fact-sheets/detail/measles", "piel", "es", ["todas"]),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/immunization-coverage",
        "vacunas",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/immunization-coverage",
        "vacunas",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/malnutrition",
        "alimentacion",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/adolescent-mental-health",
        "salud_mental",
        "en",
        ["adolescente"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/adolescent-mental-health",
        "salud_mental",
        "es",
        ["adolescente"],
    ),
    ("who", "https://www.who.int/news-room/fact-sheets/detail/malaria", "general", "en", ["todas"]),
    # ---------------- Français (fase francesa, opción A del operador, 2-sep-2026) ----------------
    # OMS: espejos en francés de las fichas ya aceptadas (misma licencia CC BY-NC-SA)
    ("who", "https://www.who.int/fr/news-room/fact-sheets/detail/measles", "piel", "fr", ["todas"]),
    ("who", "https://www.who.int/fr/news-room/fact-sheets/detail/pneumonia", "respiratorio", "fr", ["todas"]),
    ("who", "https://www.who.int/fr/news-room/fact-sheets/detail/diarrhoeal-disease", "digestivo", "fr", ["todas"]),
    ("who", "https://www.who.int/fr/news-room/fact-sheets/detail/infant-and-young-child-feeding", "alimentacion", "fr", ["lactante"]),
    ("who", "https://www.who.int/fr/news-room/fact-sheets/detail/adolescent-mental-health", "salud_mental", "fr", ["adolescente"]),
    ("who", "https://www.who.int/fr/news-room/fact-sheets/detail/immunization-coverage", "vacunas", "fr", ["todas"]),
    ("who", "https://www.who.int/fr/news-room/fact-sheets/detail/malnutrition", "alimentacion", "fr", ["todas"]),
    # Canada.ca: URLs francesas resueltas desde el conmutador de idioma de cada página y verificadas 200
    ("canada", "https://www.canada.ca/fr/sante-publique/services/maladies/virus-respiratoire-syncytial-vrs.html", "respiratorio", "fr", ["lactante"]),
    ("canada", "https://www.canada.ca/fr/sante-publique/services/maladies/rougeole.html", "piel", "fr", ["todas"]),
    ("canada", "https://www.canada.ca/fr/sante-publique/services/maladies/coqueluche-toux-coquelucheuse.html", "respiratorio", "fr", ["lactante", "todas"]),
    ("canada", "https://www.canada.ca/fr/sante-publique/services/maladies/grippe-influenza.html", "respiratorio", "fr", ["todas"]),
    ("canada", "https://www.canada.ca/fr/sante-publique/services/maladies/oreillons.html", "general", "fr", ["todas"]),
    ("canada", "https://www.canada.ca/fr/sante-publique/services/maladies/rubeole.html", "piel", "fr", ["todas"]),
    ("canada", "https://www.canada.ca/fr/sante-publique/services/maladies/maladie-lyme.html", "piel", "fr", ["todas"]),
    ("canada", "https://www.canada.ca/fr/sante-publique/services/maladies/commotions-cerebrales-signes-symptomes.html", "accidentes", "fr", ["todas"]),
    ("canada", "https://www.canada.ca/fr/sante-canada/services/securite-soleil.html", "accidentes", "fr", ["todas"]),
    ("canada", "https://www.canada.ca/fr/sante-publique/services/vaccinations-pour-enfants.html", "vacunas", "fr", ["todas"]),
]

_DATE_PATTERNS = [
    re.compile(
        r"(?:Page last reviewed|Last reviewed|Última revisión|Last updated|Page last updated)[:\s]*([0-9]{1,2}\s+\w+\s+20\d\d|\w+\s+[0-9]{1,2},\s+20\d\d|20\d\d-\d\d-\d\d)",
        re.I,
    ),
]


def doc_id_for(key: str, url: str, lang: str) -> str:
    parts = [p for p in url.rstrip("/").split("/")[3:] if p]
    last = parts[-1].replace(".html", "").replace(".htm", "")
    if (
        last in ("index", "about", "detail") and len(parts) >= 2
    ):  # cdc .../rsv/about/index.html → rsv_about
        last = (
            "_".join(
                p.replace(".html", "")
                for p in parts[-3:-1]
                if p not in ("news-room", "fact-sheets", "detail")
            )
            + "_"
            + last
        )
    slug = re.sub(r"[^a-z0-9]+", "_", last.lower()).strip("_")
    return f"{key}_{lang}_{slug}"[:70]


def page_meta(html: str) -> tuple[str, int | None]:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = (
        h1.get_text(" ", strip=True)
        if h1
        else (soup.title.get_text(strip=True) if soup.title else "")
    ).strip()
    title = re.sub(r"\s*[-|–]\s*(NHS|MedlinePlus|CDC).*$", "", title)
    text = soup.get_text(" ", strip=True)
    year = None
    for rx in _DATE_PATTERNS:
        m = rx.search(text)
        if m:
            y = re.search(r"20\d\d", m.group(1))
            if y:
                year = int(y.group(0))
                break
    return title, year


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.7)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    ok = skipped = failed = 0
    with httpx.Client(
        headers={"User-Agent": UA, "Accept-Language": "en,es"}, follow_redirects=True, timeout=30
    ) as client:
        for key, url, topic, lang, ages in WEB_SOURCES:
            org = ORGS[key]
            did = doc_id_for(key, url, lang)
            path = OUT / f"{did}.html"
            if path.exists() and not args.force:
                html = path.read_text(encoding="utf-8")
                skipped += 1
            else:
                try:
                    r = client.get(url)
                    r.raise_for_status()
                    html = r.text
                    path.write_text(html, encoding="utf-8")
                    ok += 1
                    time.sleep(args.sleep)
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {url}: {e}", file=sys.stderr)
                    failed += 1
                    continue
            title, year = page_meta(html)
            entries.append(
                {
                    "doc_id": did,
                    "file": f"web/{did}.html",
                    "org": org["org"],
                    "org_full": org["org_full"],
                    "title": title or did,
                    "year": year,
                    "lang": lang,
                    "topic": topic,
                    "doc_type": "hoja_padres",
                    "evidence": org["evidence"],
                    "usage": org["usage"],
                    "age_groups": ages,
                    "url": url,
                    "notes": f"licence: {org['license']}; fetched {dt.date.today().isoformat()}",
                }
            )
    CATALOG.write_text(
        "# GENERATED by scripts/fetch_web_sources.py — curated public web pages. Edit the script, not this file.\n"
        + yaml.safe_dump({"sources": entries}, allow_unicode=True, sort_keys=False, width=200),
        encoding="utf-8",
    )
    print(
        f"downloaded {ok}, cached {skipped}, failed {failed} → {CATALOG} ({len(entries)} entries)"
    )
    return 1 if failed and not entries else 0


if __name__ == "__main__":
    raise SystemExit(main())
