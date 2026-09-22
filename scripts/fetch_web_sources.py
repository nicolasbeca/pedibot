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

#: Títulos que la página da mal y hay que corregir a mano. Van AQUÍ y no en el YAML porque
#: `config/fuentes_web.yaml` se **regenera entero** cada vez que corre este guion: el
#: 12-sep-2026 corregí a mano «This page has been removed» —el aviso de redirección que el
#: recolector se trajo por título de una página del NHS con 578 palabras de contenido bueno—
#: y unas horas después, al traerme siete fichas nuevas, el guion lo revirtió sin decir nada.
#: El título es la mitad visible de la cita (L151): un arreglo a mano en un fichero generado
#: no es un arreglo, es una cuenta atrás.
TITULOS_CORREGIDOS = {}


ORGS = {
    "nhs": {
        "org": "NHS",
        "org_full": "NHS (National Health Service, England)",
        "license": "Open Government Licence v3.0",
        "evidence": "organismo_publico",
        "usage": "publico",
    },
    # Brasil. Licencia leída en el pie de sus propias fichas: «Todo o conteúdo deste site está
    # publicado sob a licença Creative Commons Atribuição-SemDerivações 3.0 Não Adaptada».
    # SemDerivações = citar sí, reelaborar no, así que entra como `citar_solo`: el bot lo cita
    # y el generador de guías NO puede reproducirlo. Es la primera fuente en portugués del
    # corpus, que hasta hoy tenía CERO documentos en esa lengua (11-sep-2026).
    "govbr": {
        "org": "Ministério da Saúde",
        "org_full": "Ministério da Saúde (Brasil)",
        "license": "CC BY-ND 3.0 (Atribuição-SemDerivações, Não Adaptada)",
        "evidence": "organismo_publico",
        "usage": "citar_solo",
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
    "rki": {
        "org": "RKI",
        "org_full": "Robert Koch-Institut (Deutschland)",
        "license": "Unveränderte Wiedergabe mit korrekter Quellenangabe erlaubt; kommerzielle Nutzung und Bearbeitung nur mit Zustimmung (Impressum, rki.de)",
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
    # Direcciones revisadas el 6-sep-2026 contra el sitio real: ninguna de las 243 del corpus
    # estaba rota, pero 17 respondían por una redirección y la redirección de hoy es el 404 de
    # mañana. Catorce se actualizaron aquí. Las tres que NO se tocaron cambiaron de TEMA, no de
    # sitio, y eso es una decisión de contenido:
    # mlp bedwetting (lleva a desarrollo infantil) y headaches-in-children (ahora es la general).
    ("nhs", "https://www.nhs.uk/symptoms/fever-in-children/", "fiebre", "en", ["todas"]),
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
    ("nhs", "https://www.nhs.uk/symptoms/diarrhoea-and-vomiting/", "digestivo", "en", ["todas"]),
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
        "https://www.nhs.uk/symptoms/rashes-babies-and-children/",
        "piel",
        "en",
        ["lactante", "preescolar"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/colic/", "lactante", "en", ["lactante"]),
    ("nhs", "https://www.nhs.uk/conditions/reflux-in-babies/", "lactante", "en", ["lactante"]),
    (
        "nhs",
        "https://www.nhs.uk/baby/babys-development/teething/baby-teething-symptoms/",
        "lactante",
        "en",
        ["lactante"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/ear-infections/", "orl", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/glue-ear/", "orl", "en", ["preescolar", "escolar"]),
    ("nhs", "https://www.nhs.uk/symptoms/sore-throat/", "orl", "en", ["todas"]),
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
        "https://www.nhs.uk/vaccinations/nhs-vaccinations-and-when-to-have-them/",
        "vacunas",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/baby/weaning-and-feeding/babys-first-solid-foods/",
        "alimentacion",
        "en",
        ["lactante"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/baby/caring-for-a-newborn/",
        "recien_nacido",
        "en",
        ["lactante"],
    ),
    # 16-sep-2026: «caring for a newborn» y «ibuprofen for children» son PÁGINAS ÍNDICE. Se
    # indexaron enteras y dieron 289 y 633 caracteres: sólo los títulos de sus subpáginas. El
    # contenido —incluido lo único del corpus que explica el color de la caca de un bebé, que
    # es una pregunta real y hasta hoy se contestaba pidiendo aclaración— está en las subpáginas.
    (
        "nhs",
        "https://www.nhs.uk/baby/caring-for-a-newborn/how-to-change-your-babys-nappy/",
        "recien_nacido",
        "en",
        ["lactante"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/baby/caring-for-a-newborn/soothing-a-crying-baby/",
        "lactante",
        "en",
        ["lactante"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/baby/caring-for-a-newborn/helping-your-baby-to-sleep/",
        "desarrollo",
        "en",
        ["lactante"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/baby/caring-for-a-newborn/nappy-rash/",
        "piel",
        "en",
        ["lactante"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/baby/caring-for-a-newborn/washing-and-bathing-your-baby/",
        "crianza",
        "en",
        ["lactante"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/baby/caring-for-a-newborn/sudden-infant-death-syndrome-sids/",
        "recien_nacido",
        "en",
        ["lactante"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/medicines/ibuprofen-for-children/about-ibuprofen-for-children/",
        "medicamentos",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/medicines/ibuprofen-for-children/who-can-and-cannot-take-ibuprofen-for-children/",
        "medicamentos",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/medicines/ibuprofen-for-children/how-and-when-to-give-ibuprofen-for-children/",
        "medicamentos",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/medicines/ibuprofen-for-children/side-effects-of-ibuprofen-for-children/",
        "medicamentos",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/medicines/ibuprofen-for-children/taking-ibuprofen-for-children-with-other-medicines-and-herbal-supplements/",
        "medicamentos",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/medicines/ibuprofen-for-children/common-questions-about-ibuprofen-for-children/",
        "medicamentos",
        "en",
        ["todas"],
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
    ("nhs", "https://www.nhs.uk/conditions/head-lice-and-nits/", "piel", "en", ["escolar"]),
    (
        "nhs",
        "https://www.nhs.uk/symptoms/bedwetting/",
        "desarrollo",
        "en",
        ["preescolar", "escolar"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/growing-pains/", "general", "en", ["escolar"]),
    ("nhs", "https://www.nhs.uk/conditions/cradle-cap/", "piel", "en", ["lactante"]),
    # 21-sep-2026, segunda tanda: los temas que siguieron sin fuente en las baterías del operador
    # (460 preguntas): mareo en el coche, hipo, ganglios, hongos en la uña, bizqueo, terrores
    # nocturnos, llagas y muguet, hernias, manchas de nacimiento y lunares, rechinar de dientes,
    # desmayos, palpitaciones, dolor de oído, cadera irritable, sudor excesivo, pie plano.
    ("nhs", "https://www.nhs.uk/conditions/motion-sickness/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/hiccups/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/swollen-glands/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/fungal-nail-infection/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/squint/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/lazy-eye/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/night-terrors/", "crianza", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/oral-thrush-mouth-thrush/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/mouth-ulcers/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/tongue-tie/", "lactante", "en", ["lactante"]),
    ("nhs", "https://www.nhs.uk/conditions/hernia/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/umbilical-hernia/", "general", "en", ["lactante"]),
    ("nhs", "https://www.nhs.uk/conditions/undescended-testicles/", "general", "en", ["lactante"]),
    ("nhs", "https://www.nhs.uk/conditions/birthmarks/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/moles/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/teeth-grinding/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/fainting/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/heart-palpitations/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/earache/", "orl", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/symptoms/hip-pain-children-irritable-hip/",
        "accidentes",
        "en",
        ["preescolar", "escolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/excessive-sweating-hyperhidrosis/",
        "piel",
        "en",
        ["todas"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/flat-feet/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/athletes-foot/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/warts-and-verrucas/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/cellulitis/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/kawasaki-disease/", "general", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/retinoblastoma/symptoms/",
        "general",
        "en",
        ["lactante"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/type-1-diabetes/symptoms/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/coeliac-disease/", "digestivo", "en", ["todas"]),
    # (bottle-feeding/ es una página índice sin texto propio: 0 pasajes; fuera)
    # 21-sep-2026, tercera tanda: lo que siguió sin fuente tras la última vuelta de la batería
    ("nhs", "https://www.nhs.uk/symptoms/bad-breath/", "general", "en", ["todas"]),
    # «mi hijo de 4 años tiene una erección durante mucho rato»: la fuente de la regla priapism
    (
        "nhs",
        "https://www.nhs.uk/symptoms/priapism-painful-erections/",
        "urgencias",
        "en",
        ["todas"],
    ),
    # 21-sep-2026, cuarta tanda: lo que siguió sin fuente en la batería de 300
    ("nhs", "https://www.nhs.uk/symptoms/vaginal-discharge/", "general", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/mental-health/conditions/trichotillomania/",
        "salud_mental",
        "en",
        ["escolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/mental-health/conditions/selective-mutism/",
        "salud_mental",
        "en",
        ["preescolar", "escolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/autism/signs-in-children/",
        "desarrollo",
        "en",
        ["todas"],
    ),
    ("nhs", "https://www.nhs.uk/symptoms/unintentional-weight-loss/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/dandruff/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/vitiligo/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/scabies/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/earwax-build-up/", "orl", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/glandular-fever/", "general", "en", ["escolar"]),
    ("nhs", "https://www.nhs.uk/symptoms/nail-problems/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/neck-pain-and-stiff-neck/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/foot-pain/heel-pain/", "accidentes", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/tics/", "neurologia", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/stammering/", "desarrollo", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/balanitis/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/phimosis/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/gynaecomastia/", "general", "en", ["escolar"]),
    ("nhs", "https://www.nhs.uk/symptoms/chest-pain/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/chest-infection/", "respiratorio", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/flat-head-syndrome-plagiocephaly-brachycephaly/",
        "lactante",
        "en",
        ["lactante"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/craniosynostosis/", "lactante", "en", ["lactante"]),
    # 21-sep-2026: las preguntas del operador que se quedaron sin fuente porque no había
    # documento, no porque el buscador no lo encontrara: un dedo roto, algo en el ojo, se le cae
    # el pelo, los ojos que lloran, qué no dar a un bebé (cacahuetes, salchichas enteras).
    ("nhs", "https://www.nhs.uk/conditions/broken-finger/", "accidentes", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/broken-arm-or-wrist/", "accidentes", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/sprains-and-strains/", "accidentes", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/eye-injuries/", "accidentes", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/watering-eyes/", "general", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/hair-loss/", "piel", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/ringworm/", "piel", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/baby/weaning-and-feeding/foods-to-avoid-giving-babies-and-young-children/",
        "alimentacion",
        "en",
        ["lactante", "preescolar"],
    ),
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
    # ---------------- 22-sep-2026: los huecos de la batería de 854 preguntas ----------------
    # De las primeras 380 respuestas, 87 salieron «no tengo fuente». No eran preguntas raras: eran
    # el sueño, la conducta, los hitos, los dientes, los ojos, el niño que no come y la medicina
    # que se da mal en casa. El corpus sabía de enfermedades y no sabía de crianza.
    (
        "nhs",
        "https://www.nhs.uk/conditions/sleepwalking/",
        "desarrollo",
        "en",
        ["preescolar", "escolar"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/snoring/", "orl", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/sleep-apnoea/", "orl", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/night-sweats/", "general", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/baby/babys-development/behaviour/temper-tantrums/",
        "crianza",
        "en",
        ["lactante", "preescolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/baby/weaning-and-feeding/fussy-eaters/",
        "alimentacion",
        "en",
        ["lactante", "preescolar"],
    ),
    (
        "mlp",
        "https://medlineplus.gov/ency/patientinstructions/000944.htm",
        "crianza",
        "en",
        ["preescolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/soiling-child-pooing-their-pants/",
        "digestivo",
        "en",
        ["preescolar", "escolar"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/anal-fissure/", "digestivo", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/labial-fusion/",
        "urinario",
        "en",
        ["lactante", "preescolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/short-sightedness/",
        "ojos",
        "en",
        ["preescolar", "escolar"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/double-vision/", "ojos", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/eye-tests-for-children/", "ojos", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/toothache/", "dental", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/dental-abscess/", "dental", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/live-well/healthy-teeth-and-gums/taking-care-of-childrens-teeth/",
        "dental",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/conditions/baby/health/medicines-for-babies-and-children/",
        "medicamentos",
        "en",
        ["lactante", "preescolar"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/antibiotics/", "medicamentos", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/scoliosis/", "desarrollo", "en", ["escolar"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/developmental-dysplasia-of-the-hip/",
        "desarrollo",
        "en",
        ["recien_nacido", "lactante"],
    ),
    ("nhs", "https://www.nhs.uk/conditions/heat-rash-prickly-heat/", "piel", "en", ["todas"]),
    (
        "mlp",
        "https://medlineplus.gov/ency/article/000967.htm",
        "neurologia",
        "en",
        ["lactante", "preescolar"],
    ),
    ("mlp", "https://medlineplus.gov/ency/article/003074.htm", "respiratorio", "en", ["todas"]),
    (
        "mlp",
        "https://medlineplus.gov/ency/article/001922.htm",
        "crianza",
        "en",
        ["lactante", "preescolar"],
    ),
    ("mlp", "https://medlineplus.gov/ency/article/002211.htm", "crianza", "en", ["todas"]),
    (
        "mlp",
        "https://medlineplus.gov/ency/article/001542.htm",
        "crianza",
        "en",
        ["lactante", "preescolar"],
    ),
    (
        "mlp",
        "https://medlineplus.gov/ency/article/002004.htm",
        "desarrollo",
        "en",
        ["recien_nacido"],
    ),
    (
        "mlp",
        "https://medlineplus.gov/ency/article/002010.htm",
        "desarrollo",
        "en",
        ["lactante", "preescolar"],
    ),
    ("mlp", "https://medlineplus.gov/ency/article/002013.htm", "desarrollo", "en", ["preescolar"]),
    ("mlp", "https://medlineplus.gov/ency/article/002002.htm", "desarrollo", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/002011.htm", "desarrollo", "en", ["lactante"]),
    ("mlp", "https://medlineplus.gov/ency/article/002012.htm", "desarrollo", "en", ["preescolar"]),
    (
        "mlp",
        "https://medlineplus.gov/ency/article/000809.htm",
        "desarrollo",
        "en",
        ["preescolar", "escolar"],
    ),
    (
        "mlp",
        "https://medlineplus.gov/ency/article/003209.htm",
        "desarrollo",
        "en",
        ["preescolar", "escolar"],
    ),
    (
        "mlp",
        "https://medlineplus.gov/ency/article/000897.htm",
        "urinario",
        "en",
        ["preescolar", "escolar"],
    ),
    ("mlp", "https://medlineplus.gov/ency/article/003140.htm", "urinario", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/001430.htm", "desarrollo", "en", ["preescolar"]),
    (
        "mlp",
        "https://medlineplus.gov/ency/article/001585.htm",
        "desarrollo",
        "en",
        ["lactante", "preescolar"],
    ),
    ("mlp", "https://medlineplus.gov/ency/article/007213.htm", "accidentes", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/003029.htm", "ojos", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/002084.htm", "ojos", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/002213.htm", "dental", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/002208.htm", "medicamentos", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/002070.htm", "medicamentos", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/003084.htm", "alimentacion", "en", ["todas"]),
    # 22-sep-2026, segunda vuelta de la misma batería: lo que pasa DESPUÉS de una vacuna (el
    # bulto en el brazo, el llanto, el vómito de la vacuna oral) no estaba en inglés ni en
    # castellano — las hojas del CDC sólo se habían traído en árabe y en hindi, para cubrir
    # aquellas lenguas. Y viajar con un niño no estaba en ninguna.
    ("mlp", "https://medlineplus.gov/ency/article/002024.htm", "vacunas", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/007594.htm", "vacunas", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/007603.htm", "vacunas", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/007608.htm", "vacunas", "en", ["lactante"]),
    ("mlp", "https://medlineplus.gov/ency/article/007605.htm", "vacunas", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/002427.htm", "general", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/001925.htm", "general", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/002447.htm", "alimentacion", "en", ["lactante"]),
    # 22-sep-2026, tercera vuelta: la bolita del párpado, el niño que respira por la boca desde
    # una infección y el que se come el papel. Tres preguntas de la batería, tres huecos.
    ("nhs", "https://www.nhs.uk/conditions/stye/", "ojos", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/001006.htm", "ojos", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/001649.htm", "orl", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/001538.htm", "alimentacion", "en", ["todas"]),
    # 22-sep-2026, cuarta vuelta: las vitaminas de la estantería de casa (la D que se olvida un
    # día, el magnesio que alguien probó, la orina fosforita) y el sorbo de café o de bebida
    # energética. Siete preguntas de la batería sin una sola fuente.
    (
        "nhs",
        "https://www.nhs.uk/baby/weaning-and-feeding/vitamins-for-children/",
        "alimentacion",
        "en",
        ["todas"],
    ),
    ("mlp", "https://medlineplus.gov/ency/article/002405.htm", "alimentacion", "en", ["todas"]),
    ("mlp", "https://medlineplus.gov/ency/article/002445.htm", "alimentacion", "en", ["todas"]),
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
    ("mlp", "https://medlineplus.gov/childhoodvaccines.html", "vacunas", "en", ["todas"]),
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
    # 21-sep-2026, el operador: «también descarga temas de alergias». «¿Cómo sé si es alérgico
    # al olivo?» no tenía nada sobre polen ni fiebre del heno, en ninguna lengua.
    ("mlp", "https://medlineplus.gov/spanish/allergy.html", "alergia", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/hayfever.html", "alergia", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/foodallergy.html", "alergia", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/hives.html", "alergia", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/drugreactions.html", "alergia", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/anaphylaxis.html", "alergia", "es", ["todas"]),
    ("mlp", "https://medlineplus.gov/spanish/eczema.html", "piel", "es", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/hay-fever/", "alergia", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/allergies/", "alergia", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/allergic-rhinitis/", "alergia", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/atopic-eczema/", "piel", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/baby/weaning-and-feeding/food-allergies-in-babies-and-young-children/",
        "alergia",
        "en",
        ["lactante", "preescolar"],
    ),
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
        "https://medlineplus.gov/spanish/childhoodvaccines.html",
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
    ("cdc", "https://www.cdc.gov/flu/highrisk/children.html", "respiratorio", "en", ["todas"]),
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
    ("cdc", "https://www.cdc.gov/ear-infection/about/", "orl", "en", ["todas"]),
    ("cdc", "https://www.cdc.gov/common-cold/treatment/", "respiratorio", "en", ["todas"]),
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
    # 19-sep-2026: la guía inglesa de la polio salió citando sólo al RKI alemán, que su
    # lector no puede abrir. La ficha de la OMS ya estaba en ruso y en árabe; faltaba ésta.
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/poliomyelitis",
        "vacunas",
        "en",
        ["todas"],
    ),
    # ---------------- العربية (fase árabe, 3-sep-2026) ----------------
    # Arabic is another of the WHO's six official languages, so the same fact sheets exist
    # under the same licence. All fifteen checked for a 200 before being listed.
    ("who", "https://www.who.int/ar/news-room/fact-sheets/detail/measles", "piel", "ar", ["todas"]),
    ("who", "https://www.who.int/ar/news-room/fact-sheets/detail/rubella", "piel", "ar", ["todas"]),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/pneumonia",
        "respiratorio",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/diarrhoeal-disease",
        "digestivo",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/infant-and-young-child-feeding",
        "alimentacion",
        "ar",
        ["lactante"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/malnutrition",
        "alimentacion",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/adolescent-mental-health",
        "salud_mental",
        "ar",
        ["adolescente"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/immunization-coverage",
        "vacunas",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/meningitis",
        "general",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/poliomyelitis",
        "general",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/hepatitis-b",
        "general",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/tuberculosis",
        "respiratorio",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/drowning",
        "accidentes",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/burns",
        "accidentes",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/falls",
        "accidentes",
        "ar",
        ["todas"],
    ),
    # ---------------- Русский (fase rusa, 3-sep-2026) ----------------
    # The WHO in Russian: one of its six official languages, so the fact sheets exist there
    # under the licence already accepted. Slugs checked for a 200 first — four of the ones
    # used in other languages have no Russian version and are not listed. See FUENTES/RUSO.md.
    ("who", "https://www.who.int/ru/news-room/fact-sheets/detail/measles", "piel", "ru", ["todas"]),
    ("who", "https://www.who.int/ru/news-room/fact-sheets/detail/rubella", "piel", "ru", ["todas"]),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/pneumonia",
        "respiratorio",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/diarrhoeal-disease",
        "digestivo",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/infant-and-young-child-feeding",
        "alimentacion",
        "ru",
        ["lactante"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/malnutrition",
        "alimentacion",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/adolescent-mental-health",
        "salud_mental",
        "ru",
        ["adolescente"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/immunization-coverage",
        "vacunas",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/meningitis",
        "general",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/poliomyelitis",
        "general",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/hepatitis-b",
        "general",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/tuberculosis",
        "respiratorio",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/drowning",
        "accidentes",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/burns",
        "accidentes",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/falls",
        "accidentes",
        "ru",
        ["todas"],
    ),
    # ---------------- Deutsch (fase alemana, 3-sep-2026) ----------------
    # RKI-Ratgeber: the one German public-health corpus whose licence allows reuse. BZgA
    # (kindergesundheit-info), the paediatricians' portal and the AWMF guidelines all require
    # written permission, and there is no German WHO site — see FUENTES/ALEMAN.md.
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Masern.html",
        "piel",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Varizellen.html",
        "piel",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Roeteln.html",
        "piel",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Mumps.html",
        "general",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Pertussis.html",
        "respiratorio",
        "de",
        ["lactante", "todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Streptococcus_pyogenes.html",
        "general",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_RSV.html",
        "respiratorio",
        "de",
        ["lactante"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Influenza_saisonal.html",
        "respiratorio",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Noroviren.html",
        "digestivo",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Rotaviren.html",
        "digestivo",
        "de",
        ["lactante", "todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_HFMK.html",
        "piel",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Meningokokken.html",
        "general",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Pneumokokken.html",
        "respiratorio",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Kopflausbefall.html",
        "piel",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Skabies.html",
        "piel",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Salmonellose.html",
        "digestivo",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Campylobacter.html",
        "digestivo",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_EHEC.html",
        "digestivo",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_HepatitisA.html",
        "digestivo",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_LymeBorreliose.html",
        "piel",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_FSME.html",
        "general",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Adenovirus_Konjunktivitis.html",
        "general",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Tuberkulose.html",
        "respiratorio",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_COVID-19.html",
        "respiratorio",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Poliomyelitis.html",
        "general",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Tetanus.html",
        "accidentes",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Diphtherie.html",
        "respiratorio",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_HaemophilusInfluenzae.html",
        "respiratorio",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Toxoplasmose.html",
        "general",
        "de",
        ["todas"],
    ),
    (
        "rki",
        "https://www.rki.de/DE/Aktuelles/Publikationen/RKI-Ratgeber/Ratgeber/Ratgeber_Zytomegalievirus.html",
        "general",
        "de",
        ["lactante"],
    ),
    # ---------------- Français (fase francesa, opción A del operador, 2-sep-2026) ----------------
    # OMS: espejos en francés de las fichas ya aceptadas (misma licencia CC BY-NC-SA)
    ("who", "https://www.who.int/fr/news-room/fact-sheets/detail/measles", "piel", "fr", ["todas"]),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/pneumonia",
        "respiratorio",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/diarrhoeal-disease",
        "digestivo",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/infant-and-young-child-feeding",
        "alimentacion",
        "fr",
        ["lactante"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/adolescent-mental-health",
        "salud_mental",
        "fr",
        ["adolescente"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/immunization-coverage",
        "vacunas",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/malnutrition",
        "alimentacion",
        "fr",
        ["todas"],
    ),
    # Canada.ca: URLs francesas resueltas desde el conmutador de idioma de cada página y verificadas 200
    (
        "canada",
        "https://www.canada.ca/fr/sante-publique/services/maladies/virus-respiratoire-syncytial-vrs.html",
        "respiratorio",
        "fr",
        ["lactante"],
    ),
    (
        "canada",
        "https://www.canada.ca/fr/sante-publique/services/maladies/rougeole.html",
        "piel",
        "fr",
        ["todas"],
    ),
    (
        "canada",
        "https://www.canada.ca/fr/sante-publique/services/maladies/coqueluche-toux-coquelucheuse.html",
        "respiratorio",
        "fr",
        ["lactante", "todas"],
    ),
    (
        "canada",
        "https://www.canada.ca/fr/sante-publique/services/maladies/grippe-influenza.html",
        "respiratorio",
        "fr",
        ["todas"],
    ),
    (
        "canada",
        "https://www.canada.ca/fr/sante-publique/services/maladies/oreillons.html",
        "general",
        "fr",
        ["todas"],
    ),
    (
        "canada",
        "https://www.canada.ca/fr/sante-publique/services/maladies/rubeole.html",
        "piel",
        "fr",
        ["todas"],
    ),
    (
        "canada",
        "https://www.canada.ca/fr/sante-publique/services/maladies/maladie-lyme.html",
        "piel",
        "fr",
        ["todas"],
    ),
    (
        "canada",
        "https://www.canada.ca/fr/sante-publique/services/maladies/commotions-cerebrales-signes-symptomes.html",
        "accidentes",
        "fr",
        ["todas"],
    ),
    (
        "canada",
        "https://www.canada.ca/fr/sante-canada/services/securite-soleil.html",
        "accidentes",
        "fr",
        ["todas"],
    ),
    (
        "canada",
        "https://www.canada.ca/fr/sante-publique/services/vaccinations-pour-enfants.html",
        "vacunas",
        "fr",
        ["todas"],
    ),
    # ---------------- OMS: lote del 11-sep-2026 ----------------
    # 23 fichas en cinco idiomas (115 documentos). Salen de atacar en serio India y los países
    # árabes: el corpus estaba hecho de pediatría europea y no tenía malaria, dengue, tifoidea,
    # anemia, mordedura de serpiente, lombrices, sarna, agua potable, difteria ni tétanos — que
    # es lo que mata donde el proyecto quiere llegar. Misma licencia CC BY-NC-SA 3.0 IGO ya
    # aceptada en agosto. Las 115 direcciones se comprobaron con un 200 antes de listarlas.
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/malaria",
        "fiebre",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/dengue-and-severe-dengue",
        "fiebre",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/typhoid",
        "digestivo",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/hepatitis-a",
        "digestivo",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/preterm-birth",
        "recien_nacido",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/anaemia",
        "alimentacion",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/asthma",
        "respiratorio",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/epilepsy",
        "neurologia",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/autism-spectrum-disorders",
        "desarrollo",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/sepsis",
        "urgencias",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/snakebite-envenoming",
        "accidentes",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/road-traffic-injuries",
        "accidentes",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/food-safety",
        "digestivo",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/drinking-water",
        "digestivo",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/soil-transmitted-helminth-infections",
        "digestivo",
        "ar",
        ["todas"],
    ),
    ("who", "https://www.who.int/ar/news-room/fact-sheets/detail/scabies", "piel", "ar", ["todas"]),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/obesity-and-overweight",
        "alimentacion",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/influenza-(seasonal)",
        "respiratorio",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/rabies",
        "accidentes",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/tetanus",
        "vacunas",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/hiv-aids",
        "general",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/diphtheria",
        "vacunas",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/oral-health",
        "dental",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/dengue-and-severe-dengue",
        "fiebre",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/typhoid",
        "digestivo",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/hepatitis-a",
        "digestivo",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/preterm-birth",
        "recien_nacido",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/anaemia",
        "alimentacion",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/asthma",
        "respiratorio",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/epilepsy",
        "neurologia",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/autism-spectrum-disorders",
        "desarrollo",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/sepsis",
        "urgencias",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/snakebite-envenoming",
        "accidentes",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/road-traffic-injuries",
        "accidentes",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/food-safety",
        "digestivo",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/drinking-water",
        "digestivo",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/soil-transmitted-helminth-infections",
        "digestivo",
        "en",
        ["todas"],
    ),
    ("who", "https://www.who.int/news-room/fact-sheets/detail/scabies", "piel", "en", ["todas"]),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/obesity-and-overweight",
        "alimentacion",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/influenza-(seasonal)",
        "respiratorio",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/rabies",
        "accidentes",
        "en",
        ["todas"],
    ),
    ("who", "https://www.who.int/news-room/fact-sheets/detail/tetanus", "vacunas", "en", ["todas"]),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/hiv-aids",
        "general",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/diphtheria",
        "vacunas",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/oral-health",
        "dental",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/malaria",
        "fiebre",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/dengue-and-severe-dengue",
        "fiebre",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/typhoid",
        "digestivo",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/hepatitis-a",
        "digestivo",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/preterm-birth",
        "recien_nacido",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/anaemia",
        "alimentacion",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/asthma",
        "respiratorio",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/epilepsy",
        "neurologia",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/autism-spectrum-disorders",
        "desarrollo",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/sepsis",
        "urgencias",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/snakebite-envenoming",
        "accidentes",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/road-traffic-injuries",
        "accidentes",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/food-safety",
        "digestivo",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/drinking-water",
        "digestivo",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/soil-transmitted-helminth-infections",
        "digestivo",
        "es",
        ["todas"],
    ),
    ("who", "https://www.who.int/es/news-room/fact-sheets/detail/scabies", "piel", "es", ["todas"]),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/obesity-and-overweight",
        "alimentacion",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/influenza-(seasonal)",
        "respiratorio",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/rabies",
        "accidentes",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/tetanus",
        "vacunas",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/hiv-aids",
        "general",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/diphtheria",
        "vacunas",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/oral-health",
        "dental",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/malaria",
        "fiebre",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/dengue-and-severe-dengue",
        "fiebre",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/typhoid",
        "digestivo",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/hepatitis-a",
        "digestivo",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/preterm-birth",
        "recien_nacido",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/anaemia",
        "alimentacion",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/asthma",
        "respiratorio",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/epilepsy",
        "neurologia",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/autism-spectrum-disorders",
        "desarrollo",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/sepsis",
        "urgencias",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/snakebite-envenoming",
        "accidentes",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/road-traffic-injuries",
        "accidentes",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/food-safety",
        "digestivo",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/drinking-water",
        "digestivo",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/soil-transmitted-helminth-infections",
        "digestivo",
        "fr",
        ["todas"],
    ),
    ("who", "https://www.who.int/fr/news-room/fact-sheets/detail/scabies", "piel", "fr", ["todas"]),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/obesity-and-overweight",
        "alimentacion",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/influenza-(seasonal)",
        "respiratorio",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/rabies",
        "accidentes",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/tetanus",
        "vacunas",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/hiv-aids",
        "general",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/diphtheria",
        "vacunas",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/oral-health",
        "dental",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/malaria",
        "fiebre",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/dengue-and-severe-dengue",
        "fiebre",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/typhoid",
        "digestivo",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/hepatitis-a",
        "digestivo",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/preterm-birth",
        "recien_nacido",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/anaemia",
        "alimentacion",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/asthma",
        "respiratorio",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/epilepsy",
        "neurologia",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/autism-spectrum-disorders",
        "desarrollo",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/sepsis",
        "urgencias",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/snakebite-envenoming",
        "accidentes",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/road-traffic-injuries",
        "accidentes",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/food-safety",
        "digestivo",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/drinking-water",
        "digestivo",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/soil-transmitted-helminth-infections",
        "digestivo",
        "ru",
        ["todas"],
    ),
    ("who", "https://www.who.int/ru/news-room/fact-sheets/detail/scabies", "piel", "ru", ["todas"]),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/obesity-and-overweight",
        "alimentacion",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/influenza-(seasonal)",
        "respiratorio",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/rabies",
        "accidentes",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/tetanus",
        "vacunas",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/hiv-aids",
        "general",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/diphtheria",
        "vacunas",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/oral-health",
        "dental",
        "ru",
        ["todas"],
    ),
    # ---------------- Ministério da Saúde (Brasil), 11-sep-2026 ----------------
    # Las catorce que respondieron 200 con texto servido (11.000-17.500 caracteres). Las
    # otras doce que probé dan 404: su «Saúde de A a Z» no cubre desnutrición, anemia,
    # lactancia ni verminosis, que hay que buscar por otra vía.
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/dengue",
        "fiebre",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/sarampo",
        "piel",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/coqueluche",
        "respiratorio",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/caxumba",
        "general",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/rubeola",
        "piel",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/tuberculose",
        "respiratorio",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/hepatites-virais",
        "digestivo",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/raiva",
        "accidentes",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/aedes-aegypti",
        "fiebre",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/chikungunya",
        "fiebre",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/febre-amarela",
        "fiebre",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/meningite",
        "neurologia",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/poliomielite",
        "vacunas",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/vacinacao",
        "vacunas",
        "pt",
        ["todas"],
    ),
    # ---------------- OMS: lote del 12-sep-2026 ----------------
    # Siete fichas en cinco idiomas (35 documentos), elegidas por lo que pesa en India y en
    # el Golfo y no por completar una lista. La contaminación del aire DENTRO de casa es la
    # que la OMS señala como causa principal de neumonía infantil donde se cocina con
    # biomasa, y la neumonía es lo que más mata a menores de cinco años en la India; no
    # teníamos nada. La drepanocitosis y el plomo tienen prevalencia alta allí —y el plomo
    # no da síntomas hasta que el daño está hecho—; la sordera y la ceguera son cribado del
    # recién nacido y déficit de vitamina A; del tabaco, lo que le toca al niño es el humo de
    # segunda mano. Misma licencia CC BY-NC-SA 3.0 IGO. Las 35 direcciones, comprobadas.
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/household-air-pollution-and-health",
        "respiratorio",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/household-air-pollution-and-health",
        "respiratorio",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/household-air-pollution-and-health",
        "respiratorio",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/household-air-pollution-and-health",
        "respiratorio",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/household-air-pollution-and-health",
        "respiratorio",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/sickle-cell-disease",
        "general",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/sickle-cell-disease",
        "general",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/sickle-cell-disease",
        "general",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/sickle-cell-disease",
        "general",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/sickle-cell-disease",
        "general",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/lead-poisoning-and-health",
        "intoxicacion",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/lead-poisoning-and-health",
        "intoxicacion",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/lead-poisoning-and-health",
        "intoxicacion",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/lead-poisoning-and-health",
        "intoxicacion",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/lead-poisoning-and-health",
        "intoxicacion",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/deafness-and-hearing-loss",
        "orl",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/deafness-and-hearing-loss",
        "orl",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/deafness-and-hearing-loss",
        "orl",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/deafness-and-hearing-loss",
        "orl",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/deafness-and-hearing-loss",
        "orl",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/blindness-and-visual-impairment",
        "ojos",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/blindness-and-visual-impairment",
        "ojos",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/blindness-and-visual-impairment",
        "ojos",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/blindness-and-visual-impairment",
        "ojos",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/blindness-and-visual-impairment",
        "ojos",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/tobacco",
        "respiratorio",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/tobacco",
        "respiratorio",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/tobacco",
        "respiratorio",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/tobacco",
        "respiratorio",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/tobacco",
        "respiratorio",
        "ru",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/child-maltreatment",
        "salud_mental",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/child-maltreatment",
        "salud_mental",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/child-maltreatment",
        "salud_mental",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/child-maltreatment",
        "salud_mental",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/child-maltreatment",
        "salud_mental",
        "ru",
        ["todas"],
    ),
    # ---------------- Percentiles: qué significan y qué tabla se usa (13-sep-2026) ----------------
    # El operador pidió el tema de los percentiles en todas las lenguas y países posibles. Las
    # preguntas y respuestas de la OMS sobre sus patrones de crecimiento existen en inglés,
    # castellano, francés, ruso y árabe (la portuguesa da 404), con la misma licencia que sus
    # fichas; la del NHS explica los centiles del Red Book para padres. La de MedlinePlus en
    # castellano NO entra: es un artículo de A.D.A.M. con derechos, no del NLM.
    (
        "who",
        "https://www.who.int/news-room/questions-and-answers/item/child-growth-standards",
        "desarrollo",
        "en",
        ["lactante", "preescolar"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/questions-and-answers/item/child-growth-standards",
        "desarrollo",
        "es",
        ["lactante", "preescolar"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/questions-and-answers/item/child-growth-standards",
        "desarrollo",
        "fr",
        ["lactante", "preescolar"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/questions-and-answers/item/child-growth-standards",
        "desarrollo",
        "ru",
        ["lactante", "preescolar"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/questions-and-answers/item/child-growth-standards",
        "desarrollo",
        "ar",
        ["lactante", "preescolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/baby/babys-development/height-weight-and-reviews/baby-height-and-weight/",
        "desarrollo",
        "en",
        ["lactante", "preescolar"],
    ),
    # 13-sep-2026: la ictericia del recién nacido, para la regla `neonatal_jaundice`: sin ficha para
    # padres, el bebé amarillo salía como rutina en las ocho lenguas.
    (
        "nhs",
        "https://www.nhs.uk/conditions/jaundice-in-babies/",
        "recien_nacido",
        "en",
        ["recien_nacido"],
    ),
    # 18-sep-2026, fase 2 de África: el cólera era la única de las enfermedades que matan niños
    # en el continente que no tenía ni una ficha en el corpus. Sin ficha no puede haber regla de
    # alarma —cada alarma de este proyecto cita un documento que existe— y «diarrea como agua de
    # arroz», que es la frase con la que se reconoce, salía como rutina en todos los idiomas.
    # La OMS no publica esta ficha en portugués; en las otras cinco sí, y las cinco dan 200.
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/cholera",
        "digestivo",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/cholera",
        "digestivo",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/cholera",
        "digestivo",
        "fr",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ar/news-room/fact-sheets/detail/cholera",
        "digestivo",
        "ar",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/ru/news-room/fact-sheets/detail/cholera",
        "digestivo",
        "ru",
        ["todas"],
    ),
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
        last in ("index", "about", "detail", "symptoms") and len(parts) >= 2
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
    # Some sites open with a skip-navigation heading: the RKI's first <h1> is literally
    # "Navigation und Service", which named all thirty German documents the same thing.
    CHROME = ("navigation und service", "navigation", "hauptmenü", "menu", "skip to content")
    title = ""
    for h1 in soup.find_all("h1"):
        candidate = h1.get_text(" ", strip=True)
        if candidate and candidate.lower() not in CHROME:
            title = candidate
            break
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    title = title.strip()
    title = re.sub(r"\s*[-|–]\s*(NHS|MedlinePlus|CDC|RKI).*$", "", title)
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
        headers={"User-Agent": UA, "Accept-Language": "en,es,fr,de"},
        follow_redirects=True,
        timeout=30,
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
            title = TITULOS_CORREGIDOS.get(did, title)
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
                    # La fecha es la del FICHERO, no la de hoy. Sellar con hoy un documento
                    # servido de la caché ponía «fetched» de hoy en 426 entradas que no se
                    # habían vuelto a descargar, y esa fecha se le enseña al lector en
                    # /sources como «cuándo se comprobó» (20-sep-2026).
                    "notes": (
                        f"licence: {org['license']}; fetched "
                        + dt.date.fromtimestamp(path.stat().st_mtime).isoformat()
                    ),
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
