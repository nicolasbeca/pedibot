"""Download curated public parent-facing pages (NHS OGL, CDC/MedlinePlus public domain, WHO CC BY-NC-SA)
into FUENTES/web/<doc_id>.html and write their catalog entries to config/fuentes_web.yaml.

Idempotent: existing files are not re-downloaded unless --force. Only URLs listed in WEB_SOURCES
are fetched — no crawling. Each entry records organisation, licence and language for the catalog.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import time

import httpx
import yaml
from bs4 import BeautifulSoup
from html import escape as html_escape

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
    # Irlanda del Norte. Licencia leída en su página «Crown copyright» (30-sep-2026): «You may use
    # and re-use the information featured on this website (not including logos) free of charge
    # in any format or medium, under the terms of the Open Government Licence». Su ficha de
    # vacunas del prematuro es el folleto de la UKHSA y el NHS hecho página web.
    "nidirect": {
        "org": "nidirect",
        "org_full": "nidirect (Northern Ireland Government Services)",
        "license": "Open Government Licence v3.0",
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
    # 23-sep-2026. La pregunta que más se repitió en la octava tanda —«vomitó después de tomar
    # el medicamento»— no la contesta ninguna hoja del corpus, y sí la contesta ésta, de los
    # pediatras de atención primaria españoles: «Se podría repetir la dosis si el niño vomita
    # antes de 10 a 15 minutos tras la ingesta».
    #
    # Licencia leída en el pie de sus propias fichas: CC BY-NC-ND 3.0 España. ND = citar sí,
    # reelaborar no, así que entra como `citar_solo`, igual que el Ministério da Saúde: el bot
    # la cita con su enlace y el generador de guías no puede reproducirla.
    # Comité Asesor de Vacunas de la AEP, Manual de Inmunizaciones en línea. Licencia leída en
    # el pie de cada capítulo (30-sep-2026): CC BY-NC-ND 4.0. Sin derivadas: se cita, no se
    # reelabora, así que entra como `citar_solo`, igual que Familia y Salud.
    "cavaep": {
        "org": "CAV-AEP",
        "org_full": "Comité Asesor de Vacunas de la Asociación Española de Pediatría — Manual de Inmunizaciones en línea",
        "license": "CC BY-NC-ND 4.0 (pie de vacunasaep.org)",
        "evidence": "sociedad_cientifica",
        "usage": "citar_solo",
    },
    "fys": {
        "org": "AEPap",
        "org_full": "Familia y Salud — Asociación Española de Pediatría de Atención Primaria",
        "license": "CC BY-NC-ND 3.0 España (pie de familiaysalud.es)",
        "evidence": "sociedad_cientifica",
        "usage": "citar_solo",
    },
    # India, en hindi. Permiso por correo de Vikaspedia (C-DAC) del 1-oct-2026: uso no
    # comercial citando a quien aporta el contenido y con enlace a la página; prefieren un enlace
    # a Vikaspedia «en los sitios apropiados» y el aviso de que no sustituye al consejo médico.
    # Al pie de la letra en ops/PERMISOS.md. Quien aporta cada página va en su título
    # (`vikaspedia_page`), porque el título viaja con la cita a todas partes.
    "vikaspedia": {
        "org": "Vikaspedia",
        "org_full": "Vikaspedia (C-DAC, Government of India)",
        "license": "Written permission from Vikaspedia (C-DAC), 2026-10-01: non-commercial use, citing the content contributor and the Vikaspedia page (conditions in ops/PERMISOS.md)",
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

#: La dirección de Vikaspedia va en devanagari (o en su código hexadecimal), y `doc_id_for`
#: sacaba de ella una cadena vacía. El doc_id sale del número de página de Vikaspedia.
VIKASPEDIA_IDS: dict[str, int] = {}


def _vk(page_id: int, path: str) -> str:
    url = f"https://health.vikaspedia.in/viewcontent{path}?lgn=hi"
    VIKASPEDIA_IDS[url] = page_id
    return url


# (key, url, topic, lang, age_groups)
WEB_SOURCES: list[tuple[str, str, str, str, list[str]]] = [
    # ---------------- Vikaspedia (hindi), 1-oct-2026 ----------------
    # De «बाल स्वास्थ्य» (salud infantil), lo que es para padres. Fuera: los capítulos de manual
    # de psicología del desarrollo, una recopilación que mezcla un periódico (OneIndia), la de
    # los hitos (viene de NDTV) y una que la web sirve vacía.
    # बच्चों में दस्त से होने वाली मौतों से बचाव
    ("vikaspedia", _vk(5791, "/health/child-health/बच्चों-में-दस्\u200dत-से-होने-वाली-मौतों-से-बचाव"), "digestivo", "hi", ["lactante", "preescolar"]),
    # बच्चों को होने वाली आम बीमारियॉं
    ("vikaspedia", _vk(5799, "/health/child-health/92c91a94d91a94b902-91594b-93994b928947-93593e932940-90692e-92c94092e93e93093f92f949902"), "general", "hi", ["todas"]),
    # शिशु तथा बाल पोषण पर राष्ट्रीय दिशा-निर्देश
    ("vikaspedia", _vk(6820, "/health/child-health/93693f936941-92492593e-92c93e932-92a94b937923-92a930-93093e93794d91f94d93094092f-92693f93693e-92893f93094d926947936"), "alimentacion", "hi", ["lactante", "preescolar"]),
    # स्तनपान एवं पोषण
    ("vikaspedia", _vk(7113, "/health/child-health/93894d92492892a93e928-90f935902-92a94b937923"), "alimentacion", "hi", ["lactante"]),
    # स्तनपान : स्वास्थ्यवर्द्धक और जीवनरक्षक पहल
    ("vikaspedia", _vk(7115, "/health/child-health/93894d92492892a93e928-93894d93593e93894d92594d92f93593094d92694d927915-914930-91c94093592893091594d937915-92a939932"), "alimentacion", "hi", ["lactante"]),
    # दमा
    ("vikaspedia", _vk(7255, "/health/child-health/adolescent-health"), "respiratorio", "hi", ["todas"]),
    # प्रतिरक्षण
    ("vikaspedia", _vk(7354, "/health/child-health/immunization"), "vacunas", "hi", ["todas"]),
    # पोलियो की  रोकथाम
    ("vikaspedia", _vk(5583, "/health/child-health/92a94b93293f92f94b/92a94b93293f92f94b-915940-93094b91592593e92e"), "vacunas", "hi", ["lactante", "preescolar"]),
    # पोलियो के बारे में कुछ आधारभूत सवाल-जबाव
    ("vikaspedia", _vk(5585, "/health/child-health/92a94b93293f92f94b/92a94b93293f92f94b-915947-92c93e930947-92e947902-91594191b-90692793e93092d942924-93893593e932-91c92c93e935"), "vacunas", "hi", ["lactante", "preescolar"]),
    # टीकाकरण
    ("vikaspedia", _vk(5143, "/health/child-health/93094b917-92a94d93092493f93091594d937923/91f94091593e915930923"), "vacunas", "hi", ["lactante", "preescolar"]),
    # तीव्र श्वसन रोग
    ("vikaspedia", _vk(5224, "/health/child-health/93094b917-92a94d93092493f93091594d937923/तीव्र-श्\u200dवसन-रोग"), "respiratorio", "hi", ["lactante", "preescolar"]),
    # राष्ट्रीय टीकाकरण कार्यक्रम: रोग प्रतिरक्षण तालिका
    ("vikaspedia", _vk(6545, "/health/child-health/93094b917-92a94d93092493f93091594d937923/93093e93794d91f94d93094092f-91f94091593e915930923-91593e93094d92f91594d93092e-93094b917-92a94d93092493f93091594d937923-92493e93293f91593e"), "vacunas", "hi", ["todas"]),
    # राष्ट्रीय टीकाकरण कार्यक्रम से अलग दिए जाने वाले टीके
    ("vikaspedia", _vk(6546, "/health/child-health/93094b917-92a94d93092493f93091594d937923/93093e93794d91f94d93094092f-91f94091593e915930923-91593e93094d92f91594d93092e-938947-905932917-92693f90f-91c93e928947-93593e932947-91f940915947"), "vacunas", "hi", ["todas"]),
    # रोग प्रतिरक्षण के बारे में कुछ सामान्य प्रश्न तथा भ्रांतियां
    ("vikaspedia", _vk(6614, "/health/child-health/93094b917-92a94d93092493f93091594d937923/93094b917-92a94d93092493f93091594d937923-915947-92c93e930947-92e947902-91594191b-93893e92e93e92894d92f-92a94d93093694d928-92492593e-92d94d93093e90292493f92f93e902"), "vacunas", "hi", ["todas"]),
    # वैक्सीन्स की प्रभावशीलता, सुरक्षा तथा दुष्प्रभाव
    ("vikaspedia", _vk(6764, "/health/child-health/93094b917-92a94d93092493f93091594d937923/93594891594d93894092894d938-915940-92a94d93092d93e93593694093292493e-93894193091594d93793e-92492593e-92694193794d92a94d93092d93e935"), "vacunas", "hi", ["todas"]),
    # सार्वभौमिक टीकाकरण कार्यक्रम : बच्चों व गर्भवती महिलाओं के लिए जीवनरक्षक टीकाकरण
    ("vikaspedia", _vk(422713, "/health/child-health/सार्वभौमिक-टीकाकरण-कार्यक्रम-बच्चों-व-गर्भवती-महिलाओं-के-लिए-जीवनरक्षक-टीकाकरण"), "vacunas", "hi", ["todas"]),
    # किशोर मस्तिष्क को समझना: माता-पिता के लिए एक गाइड
    ("vikaspedia", _vk(421783, "/health/child-health/92694393794d91f93f-91594d93792493f91794d93093894d924-92c91a94d91a94b902-915947-93293f90f-92e93e93094d91792693094d93693f91593e/किशोर-मस्तिष्क-को-समझना-माता-पिता-के-लिए-एक-गाइड"), "crianza", "hi", ["adolescente"]),
    # बच्चे का शारीरिक और मानसिक विकास
    ("vikaspedia", _vk(5785, "/health/child-health/92c91a94d91a947-91593e-93693e93094093093f915-914930-92e93e92893893f915-93593f91593e938"), "desarrollo", "hi", ["todas"]),
    # नवजात शैशवावस्था (जन्म से एक माह तक)
    ("vikaspedia", _vk(5352, "/health/child-health/93694893693593e93593894d92593e-93693e93094093093f915-92a94793694092f-90f935902-93894d92893e92f93593f915-93593f91593e938/92893591c93e924-93694893693593e93593894d92593e-91c92894d92e-938947-90f915-92e93e939-924915"), "recien_nacido", "hi", ["lactante"]),
    # El prematuro (30-sep-2026): vacunas con la edad real, hitos con la corregida.
    (
        "cavaep",
        "https://vacunasaep.org/documentos/manual/cap-10",
        "vacunas",
        "es",
        ["recien_nacido", "lactante"],
    ),
    (
        "nidirect",
        "https://www.nidirect.gov.uk/articles/childhood-immunisation-programme",
        "vacunas",
        "en",
        ["lactante"],
    ),
    (
        "cdc",
        "https://www.cdc.gov/act-early/digital-online-checklist/2-months.html",
        "desarrollo",
        "en",
        ["lactante"],
    ),
    # En un barco, primero el centro médico de a bordo (30-sep-2026): la cita del texto fijo
    # SHIP_FIRST de answer.py, para que esté en el catálogo como las demás.
    ("cdc", "https://wwwnc.cdc.gov/travel/page/cruise-ship", "urgencias", "en", ["todas"]),
    # La vacuna del VPH (2-oct-2026, consulta real desde Reino Unido): «side effects of HPV
    # vaccine… risks and benefits» se quedó sin fuente. No había ni una página en inglés sobre
    # ella. Y la de seguridad de las vacunas, para «he leído que perjudica…».
    ("nhs", "https://www.nhs.uk/vaccinations/hpv-vaccine/", "vacunas", "en", ["escolar", "adolescente"]),
    # Cada vacuna del calendario del NHS (3-oct-2026, la misma consulta real): «should I
    # vaccinate my child polio vaccine?» se contestó con el calendario español. El NHS dice
    # «6-in-1» y no «polio»: sin la página de cada vacuna, la búsqueda no puede unirlas.
    ("nhs", "https://www.nhs.uk/vaccinations/6-in-1-vaccine/", "vacunas", "en", ["lactante"]),
    ("nhs", "https://www.nhs.uk/vaccinations/rotavirus-vaccine/", "vacunas", "en", ["lactante"]),
    (
        "nhs",
        "https://www.nhs.uk/vaccinations/menb-vaccine-for-children/",
        "vacunas",
        "en",
        ["lactante", "preescolar"],
    ),
    ("nhs", "https://www.nhs.uk/vaccinations/pneumococcal-vaccine/", "vacunas", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/vaccinations/hepatitis-b-vaccine/", "vacunas", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/vaccinations/mmrv-vaccine/", "vacunas", "en", ["lactante", "preescolar"]),
    ("nhs", "https://www.nhs.uk/vaccinations/mmr-vaccine/", "vacunas", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/vaccinations/4-in-1-preschool-booster-vaccine/",
        "vacunas",
        "en",
        ["preescolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/vaccinations/td-ipv-vaccine-3-in-1-teenage-booster/",
        "vacunas",
        "en",
        ["adolescente"],
    ),
    ("nhs", "https://www.nhs.uk/vaccinations/menacwy-vaccine/", "vacunas", "en", ["adolescente"]),
    ("nhs", "https://www.nhs.uk/vaccinations/child-flu-vaccine/", "vacunas", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/vaccinations/bcg-vaccine-for-tuberculosis-tb/",
        "vacunas",
        "en",
        ["lactante"],
    ),
    ("nhs", "https://www.nhs.uk/vaccinations/chickenpox-vaccine/", "vacunas", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/polio/", "vacunas", "en", ["todas"]),
    (
        "nhs",
        "https://www.nhs.uk/conditions/vaccinations/why-vaccination-is-safe-and-important/",
        "vacunas",
        "en",
        ["todas"],
    ),
    # Cómo tomar la temperatura, y la madre que está enferma y da el pecho (30-sep-2026): las
    # dos preguntas se contestaban citando fichas que no decían lo contestado.
    (
        "nhs",
        "https://www.nhs.uk/baby/health/how-to-take-your-babys-temperature/",
        "general",
        "en",
        ["lactante", "preescolar"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/baby/breastfeeding-and-bottle-feeding/breastfeeding-and-lifestyle/medicines/",
        "alimentacion",
        "en",
        ["lactante"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/best-start-in-life/baby/feeding-your-baby/breastfeeding/can-i-breastfeed-if-im/having-covid-19-symptoms-or-vaccine/",
        "alimentacion",
        "en",
        ["lactante"],
    ),
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
    # 23-sep-2026. De las 500 preguntas de la octava tanda, 17 se quedaron sin fuente y CINCO
    # eran la misma cosa: el medicamento que ya está en casa y salió mal. «Vomitó después de
    # tomarlo», «se la di dos veces porque mi marido no sabía que ya se la había dado», «dejé de
    # dárselo ayer, ¿reinicio?», «se la di una hora antes», «creo que era otra concentración».
    # El corpus sabía calcular la dosis y no sabía nada de lo que pasa después, que es cuando el
    # padre escribe a las once de la noche.
    #
    # Del paracetamol infantil sólo teníamos la portada, mientras que del ibuprofeno estaban las
    # seis páginas. La amoxicilina entra por la dosis olvidada y por el tratamiento que se deja
    # a medias, que es la otra mitad de las preguntas. Y «medicines for babies and children» es
    # la que dice, con estas palabras, que una cucharilla de cocina no mide una dosis.
    (
        "nhs",
        "https://www.nhs.uk/medicines/amoxicillin/about-amoxicillin/",
        "medicamentos",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/medicines/amoxicillin/how-and-when-to-take-amoxicillin/",
        "medicamentos",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/medicines/amoxicillin/side-effects-of-amoxicillin/",
        "medicamentos",
        "en",
        ["todas"],
    ),
    (
        "nhs",
        "https://www.nhs.uk/medicines/amoxicillin/common-questions-about-amoxicillin/",
        "medicamentos",
        "en",
        ["todas"],
    ),
    (
        "fys",
        "https://www.familiaysalud.es/medicinas/farmacos/antitermicos-para-la-fiebre",
        "medicamentos",
        "es",
        ["todas"],
    ),
    (
        "fys",
        "https://www.familiaysalud.es/medicinas/farmacos/sobre-los-medicamentos/por-que-hay-que-cumplir-los-tratamientos",
        "medicamentos",
        "es",
        ["todas"],
    ),
    (
        "fys",
        "https://www.familiaysalud.es/medicinas/farmacos/sobre-los-medicamentos/hay-que-leer-los-prospectos-de-los-medicamentos",
        "medicamentos",
        "es",
        ["todas"],
    ),
    (
        "fys",
        "https://www.familiaysalud.es/salud-y-escuela/educacion-infantil-0/los-problemas-de-salud/sobre-enfermedades-de-los-ninos/cuales",
        "medicamentos",
        "es",
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
        "https://www.nhs.uk/symptoms/headaches/",
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
    ("nhs", "https://www.nhs.uk/symptoms/snoring/", "orl", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/sleep-apnoea/", "orl", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/night-sweats/", "general", "en", ["todas"]),
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
        "https://www.nhs.uk/symptoms/soiling-child-pooing-their-pants/",
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
    ("nhs", "https://www.nhs.uk/symptoms/double-vision/", "ojos", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/conditions/eye-tests-for-children/", "ojos", "en", ["todas"]),
    ("nhs", "https://www.nhs.uk/symptoms/toothache/", "dental", "en", ["todas"]),
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
        "https://www.nhs.uk/baby/health/medicines-for-babies-and-children/",
        "medicamentos",
        "en",
        ["lactante", "preescolar"],
    ),
    ("nhs", "https://www.nhs.uk/medicines/antibiotics/", "medicamentos", "en", ["todas"]),
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
    # 22-sep-2026, quinta vuelta: «he dejado un biberón preparado fuera dos horas» no tenía
    # fuente y es la pregunta de cualquier noche.
    (
        "nhs",
        "https://www.nhs.uk/baby/breastfeeding-and-bottle-feeding/bottle-feeding/making-up-baby-formula/",
        "alimentacion",
        "en",
        ["lactante"],
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
    # 29-sep-2026: el publicador llevaba días diciendo «no sources for topic tuberculosis» y
    # «hepatitis_b» en inglés. Las dos fichas estaban sólo en árabe y en ruso desde el 3-sep; las
    # guías de esos dos temas no podían escribirse en ninguna de las otras seis lenguas.
    (
        "who",
        "https://www.who.int/news-room/fact-sheets/detail/tuberculosis",
        "respiratorio",
        "en",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/tuberculosis",
        "respiratorio",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/tuberculosis",
        "respiratorio",
        "fr",
        ["todas"],
    ),
    ("who", "https://www.who.int/news-room/fact-sheets/detail/hepatitis-b", "general", "en", ["todas"]),
    (
        "who",
        "https://www.who.int/es/news-room/fact-sheets/detail/hepatitis-b",
        "general",
        "es",
        ["todas"],
    ),
    (
        "who",
        "https://www.who.int/fr/news-room/fact-sheets/detail/hepatitis-b",
        "general",
        "fr",
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
    # 28-sep-2026: las diez gemelas en inglés. La licencia era la misma y estaba aprobada desde el
    # 2-sep; sólo se había traído la mitad francesa. URLs leídas del conmutador de idioma de cada
    # página francesa, mismos temas y edades.
    ("canada", "https://www.canada.ca/en/public-health/services/diseases/respiratory-syncytial-virus-rsv.html", "respiratorio", "en", ["lactante"]),
    ("canada", "https://www.canada.ca/en/public-health/services/diseases/measles.html", "piel", "en", ["todas"]),
    ("canada", "https://www.canada.ca/en/public-health/services/diseases/whooping-cough-pertussis.html", "respiratorio", "en", ["lactante", "todas"]),
    ("canada", "https://www.canada.ca/en/public-health/services/diseases/flu-influenza.html", "respiratorio", "en", ["todas"]),
    ("canada", "https://www.canada.ca/en/public-health/services/diseases/mumps.html", "general", "en", ["todas"]),
    ("canada", "https://www.canada.ca/en/public-health/services/diseases/rubella.html", "piel", "en", ["todas"]),
    ("canada", "https://www.canada.ca/en/public-health/services/diseases/lyme-disease.html", "piel", "en", ["todas"]),
    ("canada", "https://www.canada.ca/en/public-health/services/diseases/concussion-sign-symptoms.html", "accidentes", "en", ["todas"]),
    ("canada", "https://www.canada.ca/en/health-canada/services/sun-safety.html", "accidentes", "en", ["todas"]),
    ("canada", "https://www.canada.ca/en/public-health/services/vaccination-children.html", "vacunas", "en", ["todas"]),
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
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/d/dengue",
        "fiebre",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/s/sarampo",
        "piel",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/c/coqueluche",
        "respiratorio",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/c/caxumba",
        "general",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/r/rubeola",
        "piel",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/t/tuberculose",
        "respiratorio",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/h/hepatites-virais",
        "digestivo",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/r/raiva",
        "accidentes",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/a/aedes-aegypti",
        "fiebre",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/c/chikungunya",
        "fiebre",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/f/febre-amarela",
        "fiebre",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/m/meningite",
        "neurologia",
        "pt",
        ["todas"],
    ),
    (
        "govbr",
        "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/p/poliomielite",
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


#: La firma al pie de cada página de Vikaspedia: «स्त्रोत:» o «स्रोत:» (las dos grafías), a
#: principio de línea y con dos puntos, y el nombre en la misma línea o en la siguiente. La
#: última que haya: «जलस्रोत» (fuente de agua) en mitad del texto no es una firma.
_VK_FIRMA = re.compile(r"^\s*(?:स्त्रोत|स्रोत|source)\s*[:：]\s*(.*)$", re.I | re.M)
_JOINERS = str.maketrans("", "", "‌‍")


def vikaspedia_page(html: str) -> tuple[str, str, str]:
    """Una página de Vikaspedia → (HTML limpio para guardar, título, quién aporta el contenido).

    Vikaspedia es una aplicación Next.js: el HTML trae sólo el título y el texto viene dentro del
    JSON `__NEXT_DATA__`. Se guarda ese contenido envuelto en `<main>` con su título, que es lo
    que el extractor de HTML sabe leer. Quien aporta el contenido es la última firma
    «स्रोत: …» del pie; sin firma, la página es de la propia Vikaspedia.
    """
    soup = BeautifulSoup(html, "html.parser")
    datos = json.loads(soup.find("script", id="__NEXT_DATA__").string)
    pagina = datos["props"]["pageProps"]["ssrPageContent"]
    titulo = " ".join(pagina["title"].translate(_JOINERS).split())
    contenido = pagina["content"]
    texto = BeautifulSoup(contenido, "html.parser").get_text("\n", strip=True).translate(_JOINERS)
    autor = "Vikaspedia"
    firmas = list(_VK_FIRMA.finditer(texto))
    if firmas:
        # la firma puede venir partida en varias etiquetas («WHO», «, », «IAP»): se toma lo que
        # queda hasta el final; si es largo, es que debajo hay texto, y vale sólo la primera línea
        resto = texto[firmas[-1].start(1) :].strip()
        if len(resto) > 250:
            resto = resto.split("\n")[0]
        resto = re.sub(r"\s*,\s*", ", ", " ".join(resto.split()))
        autor = resto.strip(" -–।,") or autor
    actualizada = pagina.get("updated_at") or pagina.get("created_at")
    if isinstance(actualizada, (int, float)):
        actualizada = dt.date.fromtimestamp(actualizada / 1000).isoformat()
    limpio = (
        '<!doctype html><html lang="hi"><head><meta charset="utf-8">'
        f"<title>{html_escape(titulo)}</title>"
        f'<meta name="pedibot-contributor" content="{html_escape(autor)}">'
        f'<meta name="pedibot-updated" content="{html_escape(str(actualizada or ""))[:10]}"></head>'
        f"<body><main><h1>{html_escape(titulo)}</h1>\n{contenido}\n</main></body></html>"
    )
    return limpio, titulo, autor


def saved_contributor(html: str) -> str | None:
    m = BeautifulSoup(html, "html.parser").find("meta", attrs={"name": "pedibot-contributor"})
    return m["content"] if m else None


def saved_year(html: str) -> int | None:
    m = BeautifulSoup(html, "html.parser").find("meta", attrs={"name": "pedibot-updated"})
    y = re.match(r"(20\d\d)", m["content"]) if m else None
    return int(y.group(1)) if y else None


def doc_id_for(key: str, url: str, lang: str) -> str:
    if key == "vikaspedia":
        return f"vikaspedia_{lang}_{VIKASPEDIA_IDS[url]}"
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
                    if key == "vikaspedia":
                        html, _, _ = vikaspedia_page(html)
                    path.write_text(html, encoding="utf-8")
                    ok += 1
                    time.sleep(args.sleep)
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {url}: {e}", file=sys.stderr)
                    failed += 1
                    continue
            title, year = page_meta(html)
            title = TITULOS_CORREGIDOS.get(did, title)
            if key == "vikaspedia":
                # condición del permiso: quien aporta el contenido viaja con la cita
                title = f"{title} — स्रोत: {saved_contributor(html) or 'Vikaspedia'}"
                year = year or saved_year(html)
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
