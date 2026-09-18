"""Calendarios de vacunación a partir de los datos de la OMS (17-sep-2026).

Los ocho calendarios que ya había se transcribieron a mano del documento nacional. Para el Golfo
eso no se puede: las condiciones de uso del portal del Ministerio de Salud saudí prohíben copiar
su contenido (leídas el 16-sep-2026; sólo permiten enlazar). Pero la OMS publica, COMO DATOS, el
calendario que cada país le reporta, en su almacén público WIISE, y esa licencia —CC BY-NC-SA 3.0
IGO— es la que este proyecto ya usa para las fichas de la OMS.

    uv run python scripts/build_who_schedules.py SAU ARE EGY QAT KWT      # enseña el YAML
    uv run python scripts/build_who_schedules.py SAU --write              # lo añade a config

Antes de fiarme de estos datos los contrasté con lo que ya tenía transcrito a mano: para INDIA la
OMS reproduce el calendario del UIP casilla por casilla (BCG, OPV-0 y hepatitis B al nacer;
pentavalente, fIPV, PCV y rotavirus a las 6, 10 y 14 semanas; MR a los 9 meses; refuerzos a los
16-24 meses; DPT a los 5-6 años; Td a los 10 y 16). Donde falla es en ESPAÑA, porque el detalle
autonómico lo marca como subnacional. Para el Golfo, donde no hay documento que se pueda copiar,
es la mejor fuente disponible y encima es la que el propio país firma.

Qué se deja fuera, y por qué:

- lo que no es de la infancia: el tétanos materno, la gripe y la covid de adultos, los viajeros,
  los sanitarios y los grupos de riesgo. Un calendario infantil que mezcle eso no se entiende;
- lo que la OMS marca como PLANNED, que es lo que el país piensa introducir y todavía no pone;
- las edades que no se pueden fechar («1st contact»), porque una fila que no dice cuándo no ayuda.

Y dos cosas que sí se hacen, porque si no el resultado engañaría:

- cuando dos productos ocupan la MISMA casilla —Emiratos reporta PCV15 y PCV20 a los 2, 4 y 18
  meses; Kuwait, hexavalente y pentavalente a los 2, 4 y 6— se imprimen como una sola línea
  unida por «or». Son alternativas para un pinchazo, no dos pinchazos;
- las dosis que la OMS fecha por intervalo («+M6», la segunda del VPH) no se tiran: se cuelgan
  de la dosis anterior como «2nd dose 6 months later».
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DESTINO = ROOT / "config" / "vaccines.yaml"
BASE = "https://xmart-api-public.who.int/WIISE/AD_SCHEDULES"
UA = {"User-Agent": "Mozilla/5.0 (compatible; PediBot-schedules/1.0)"}
PAGINA = "https://immunizationdata.who.int/global/wiise-detail-page/vaccination-schedule-for-"

IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")

#: ISO3 → (ISO2, el nombre del país en las ocho lenguas del sitio)
PAISES: dict[str, tuple[str, dict[str, str]]] = {
    "SAU": ("SA", {"en": "Saudi Arabia", "es": "Arabia Saudí", "fr": "Arabie saoudite",
                   "de": "Saudi-Arabien", "ru": "Саудовская Аравия", "ar": "السعودية",
                   "pt": "Arábia Saudita", "hi": "सऊदी अरब"}),
    "ARE": ("AE", {"en": "United Arab Emirates", "es": "Emiratos Árabes Unidos",
                   "fr": "Émirats arabes unis", "de": "Vereinigte Arabische Emirate",
                   "ru": "ОАЭ", "ar": "الإمارات العربية المتحدة", "pt": "Emirados Árabes Unidos",
                   "hi": "संयुक्त अरब अमीरात"}),
    "EGY": ("EG", {"en": "Egypt", "es": "Egipto", "fr": "Égypte", "de": "Ägypten",
                   "ru": "Египет", "ar": "مصر", "pt": "Egito", "hi": "मिस्र"}),
    "QAT": ("QA", {"en": "Qatar", "es": "Catar", "fr": "Qatar", "de": "Katar",
                   "ru": "Катар", "ar": "قطر", "pt": "Catar", "hi": "क़तर"}),
    "KWT": ("KW", {"en": "Kuwait", "es": "Kuwait", "fr": "Koweït", "de": "Kuwait",
                   "ru": "Кувейт", "ar": "الكويت", "pt": "Kuwait", "hi": "कुवैत"}),
    # ── África, 18-sep-2026 ────────────────────────────────────────────────────────────
    # El operador: «tenemos totalmente olvidado el mercado africano… estamos vendiendo que el
    # proyecto es altruista y para países que no tienen acceso fácil a pediatría, y en cambio
    # hemos dejado de lado a todo un continente». Medido: 4 países de 53, y los cuatro del
    # norte. La OMS publica el calendario de 48 países africanos en el mismo almacén del que
    # salieron los del Golfo, así que el coste de arreglarlo es ejecutar este script.
    #
    # Los nombres salen de `Intl.DisplayNames` (CLDR, vía Node), no escritos a mano: 48 países
    # por ocho lenguas son 384 nombres y a mano se cuela una errata segura.
    "AGO": ("AO", {"en": "Angola", "es": "Angola", "fr": "Angola", "de": "Angola", "ru": "Ангола", "ar": "أنغولا", "pt": "Angola", "hi": "अंगोला"}),
    "BDI": ("BI", {"en": "Burundi", "es": "Burundi", "fr": "Burundi", "de": "Burundi", "ru": "Бурунди", "ar": "بوروندي", "pt": "Burundi", "hi": "बुरुंडी"}),
    "BEN": ("BJ", {"en": "Benin", "es": "Benín", "fr": "Bénin", "de": "Benin", "ru": "Бенин", "ar": "بنين", "pt": "Benin", "hi": "बेनिन"}),
    "BFA": ("BF", {"en": "Burkina Faso", "es": "Burkina Faso", "fr": "Burkina Faso", "de": "Burkina Faso", "ru": "Буркина-Фасо", "ar": "بوركينا فاسو", "pt": "Burquina Faso", "hi": "बुर्किना फ़ासो"}),
    "BWA": ("BW", {"en": "Botswana", "es": "Botsuana", "fr": "Botswana", "de": "Botsuana", "ru": "Ботсвана", "ar": "بوتسوانا", "pt": "Botsuana", "hi": "बोत्स्वाना"}),
    "CAF": ("CF", {"en": "Central African Republic", "es": "República Centroafricana", "fr": "République centrafricaine", "de": "Zentralafrikanische Republik", "ru": "Центрально-Африканская Республика", "ar": "جمهورية أفريقيا الوسطى", "pt": "República Centro-Africana", "hi": "मध्य अफ़्रीकी गणराज्य"}),
    "CIV": ("CI", {"en": "Côte d’Ivoire", "es": "Côte d’Ivoire", "fr": "Côte d’Ivoire", "de": "Côte d’Ivoire", "ru": "Кот-д’Ивуар", "ar": "ساحل العاج", "pt": "Costa do Marfim", "hi": "कोत दिवुआर"}),
    "CMR": ("CM", {"en": "Cameroon", "es": "Camerún", "fr": "Cameroun", "de": "Kamerun", "ru": "Камерун", "ar": "الكاميرون", "pt": "Camarões", "hi": "कैमरून"}),
    "COD": ("CD", {"en": "Congo - Kinshasa", "es": "República Democrática del Congo", "fr": "Congo-Kinshasa", "de": "Kongo-Kinshasa", "ru": "Конго - Киншаса", "ar": "الكونغو - كينشاسا", "pt": "Congo - Kinshasa", "hi": "कांगो - किंशासा"}),
    "COG": ("CG", {"en": "Congo - Brazzaville", "es": "Congo", "fr": "Congo-Brazzaville", "de": "Kongo-Brazzaville", "ru": "Конго - Браззавиль", "ar": "الكونغو - برازافيل", "pt": "República do Congo", "hi": "कांगो – ब्राज़ाविल"}),
    "COM": ("KM", {"en": "Comoros", "es": "Comoras", "fr": "Comores", "de": "Komoren", "ru": "Коморы", "ar": "جزر القمر", "pt": "Comores", "hi": "कोमोरोस"}),
    "CPV": ("CV", {"en": "Cape Verde", "es": "Cabo Verde", "fr": "Cap-Vert", "de": "Cabo Verde", "ru": "Кабо-Верде", "ar": "الرأس الأخضر", "pt": "Cabo Verde", "hi": "केप वर्ड"}),
    "DJI": ("DJ", {"en": "Djibouti", "es": "Yibuti", "fr": "Djibouti", "de": "Dschibuti", "ru": "Джибути", "ar": "جيبوتي", "pt": "Djibuti", "hi": "जिबूती"}),
    "ERI": ("ER", {"en": "Eritrea", "es": "Eritrea", "fr": "Érythrée", "de": "Eritrea", "ru": "Эритрея", "ar": "إريتريا", "pt": "Eritreia", "hi": "इरिट्रिया"}),
    "ETH": ("ET", {"en": "Ethiopia", "es": "Etiopía", "fr": "Éthiopie", "de": "Äthiopien", "ru": "Эфиопия", "ar": "إثيوبيا", "pt": "Etiópia", "hi": "इथियोपिया"}),
    "GAB": ("GA", {"en": "Gabon", "es": "Gabón", "fr": "Gabon", "de": "Gabun", "ru": "Габон", "ar": "الغابون", "pt": "Gabão", "hi": "गैबॉन"}),
    "GHA": ("GH", {"en": "Ghana", "es": "Ghana", "fr": "Ghana", "de": "Ghana", "ru": "Гана", "ar": "غانا", "pt": "Gana", "hi": "घाना"}),
    "GIN": ("GN", {"en": "Guinea", "es": "Guinea", "fr": "Guinée", "de": "Guinea", "ru": "Гвинея", "ar": "غينيا", "pt": "Guiné", "hi": "गिनी"}),
    "GMB": ("GM", {"en": "Gambia", "es": "Gambia", "fr": "Gambie", "de": "Gambia", "ru": "Гамбия", "ar": "غامبيا", "pt": "Gâmbia", "hi": "गाम्बिया"}),
    "GNB": ("GW", {"en": "Guinea-Bissau", "es": "Guinea-Bisáu", "fr": "Guinée-Bissau", "de": "Guinea-Bissau", "ru": "Гвинея-Бисау", "ar": "غينيا بيساو", "pt": "Guiné-Bissau", "hi": "गिनी-बिसाउ"}),
    "GNQ": ("GQ", {"en": "Equatorial Guinea", "es": "Guinea Ecuatorial", "fr": "Guinée équatoriale", "de": "Äquatorialguinea", "ru": "Экваториальная Гвинея", "ar": "غينيا الاستوائية", "pt": "Guiné Equatorial", "hi": "इक्वेटोरियल गिनी"}),
    "KEN": ("KE", {"en": "Kenya", "es": "Kenia", "fr": "Kenya", "de": "Kenia", "ru": "Кения", "ar": "كينيا", "pt": "Quênia", "hi": "केन्या"}),
    "LBR": ("LR", {"en": "Liberia", "es": "Liberia", "fr": "Liberia", "de": "Liberia", "ru": "Либерия", "ar": "ليبيريا", "pt": "Libéria", "hi": "लाइबेरिया"}),
    "LSO": ("LS", {"en": "Lesotho", "es": "Lesoto", "fr": "Lesotho", "de": "Lesotho", "ru": "Лесото", "ar": "ليسوتو", "pt": "Lesoto", "hi": "लेसोथो"}),
    "MDG": ("MG", {"en": "Madagascar", "es": "Madagascar", "fr": "Madagascar", "de": "Madagaskar", "ru": "Мадагаскар", "ar": "مدغشقر", "pt": "Madagascar", "hi": "मेडागास्कर"}),
    "MLI": ("ML", {"en": "Mali", "es": "Mali", "fr": "Mali", "de": "Mali", "ru": "Мали", "ar": "مالي", "pt": "Mali", "hi": "माली"}),
    "MOZ": ("MZ", {"en": "Mozambique", "es": "Mozambique", "fr": "Mozambique", "de": "Mosambik", "ru": "Мозамбик", "ar": "موزمبيق", "pt": "Moçambique", "hi": "मोज़ांबिक"}),
    "MRT": ("MR", {"en": "Mauritania", "es": "Mauritania", "fr": "Mauritanie", "de": "Mauretanien", "ru": "Мавритания", "ar": "موريتانيا", "pt": "Mauritânia", "hi": "मॉरिटानिया"}),
    "MUS": ("MU", {"en": "Mauritius", "es": "Mauricio", "fr": "Maurice", "de": "Mauritius", "ru": "Маврикий", "ar": "موريشيوس", "pt": "Maurício", "hi": "मॉरीशस"}),
    "MWI": ("MW", {"en": "Malawi", "es": "Malaui", "fr": "Malawi", "de": "Malawi", "ru": "Малави", "ar": "ملاوي", "pt": "Malaui", "hi": "मलावी"}),
    "NAM": ("NA", {"en": "Namibia", "es": "Namibia", "fr": "Namibie", "de": "Namibia", "ru": "Намибия", "ar": "ناميبيا", "pt": "Namíbia", "hi": "नामीबिया"}),
    "NER": ("NE", {"en": "Niger", "es": "Níger", "fr": "Niger", "de": "Niger", "ru": "Нигер", "ar": "النيجر", "pt": "Níger", "hi": "नाइजर"}),
    "NGA": ("NG", {"en": "Nigeria", "es": "Nigeria", "fr": "Nigeria", "de": "Nigeria", "ru": "Нигерия", "ar": "نيجيريا", "pt": "Nigéria", "hi": "नाइजीरिया"}),
    "RWA": ("RW", {"en": "Rwanda", "es": "Ruanda", "fr": "Rwanda", "de": "Ruanda", "ru": "Руанда", "ar": "رواندا", "pt": "Ruanda", "hi": "रवांडा"}),
    "SEN": ("SN", {"en": "Senegal", "es": "Senegal", "fr": "Sénégal", "de": "Senegal", "ru": "Сенегал", "ar": "السنغال", "pt": "Senegal", "hi": "सेनेगल"}),
    "SLE": ("SL", {"en": "Sierra Leone", "es": "Sierra Leona", "fr": "Sierra Leone", "de": "Sierra Leone", "ru": "Сьерра-Леоне", "ar": "سيراليون", "pt": "Serra Leoa", "hi": "सिएरा लियोन"}),
    "SOM": ("SO", {"en": "Somalia", "es": "Somalia", "fr": "Somalie", "de": "Somalia", "ru": "Сомали", "ar": "الصومال", "pt": "Somália", "hi": "सोमालिया"}),
    "SSD": ("SS", {"en": "South Sudan", "es": "Sudán del Sur", "fr": "Soudan du Sud", "de": "Südsudan", "ru": "Южный Судан", "ar": "جنوب السودان", "pt": "Sudão do Sul", "hi": "दक्षिण सूडान"}),
    "STP": ("ST", {"en": "São Tomé & Príncipe", "es": "Santo Tomé y Príncipe", "fr": "Sao Tomé-et-Principe", "de": "São Tomé und Príncipe", "ru": "Сан-Томе и Принсипи", "ar": "ساو تومي وبرينسيبي", "pt": "São Tomé e Príncipe", "hi": "साओ टोम और प्रिंसिपे"}),
    "SWZ": ("SZ", {"en": "Eswatini", "es": "Esuatini", "fr": "Eswatini", "de": "Eswatini", "ru": "Эсватини", "ar": "إسواتيني", "pt": "Essuatíni", "hi": "एस्वाटिनी"}),
    "SYC": ("SC", {"en": "Seychelles", "es": "Seychelles", "fr": "Seychelles", "de": "Seychellen", "ru": "Сейшельские о-ва", "ar": "سيشل", "pt": "Seicheles", "hi": "सेशेल्स"}),
    "TCD": ("TD", {"en": "Chad", "es": "Chad", "fr": "Tchad", "de": "Tschad", "ru": "Чад", "ar": "تشاد", "pt": "Chade", "hi": "चाड"}),
    "TGO": ("TG", {"en": "Togo", "es": "Togo", "fr": "Togo", "de": "Togo", "ru": "Того", "ar": "توغو", "pt": "Togo", "hi": "टोगो"}),
    "TZA": ("TZ", {"en": "Tanzania", "es": "Tanzania", "fr": "Tanzanie", "de": "Tansania", "ru": "Танзания", "ar": "تنزانيا", "pt": "Tanzânia", "hi": "तंज़ानिया"}),
    "UGA": ("UG", {"en": "Uganda", "es": "Uganda", "fr": "Ouganda", "de": "Uganda", "ru": "Уганда", "ar": "أوغندا", "pt": "Uganda", "hi": "युगांडा"}),
    "ZAF": ("ZA", {"en": "South Africa", "es": "Sudáfrica", "fr": "Afrique du Sud", "de": "Südafrika", "ru": "Южно-Африканская Республика", "ar": "جنوب أفريقيا", "pt": "África do Sul", "hi": "दक्षिण अफ़्रीका"}),
    "ZMB": ("ZM", {"en": "Zambia", "es": "Zambia", "fr": "Zambie", "de": "Sambia", "ru": "Замбия", "ar": "زامبيا", "pt": "Zâmbia", "hi": "ज़ाम्बिया"}),
    "ZWE": ("ZW", {"en": "Zimbabwe", "es": "Zimbabue", "fr": "Zimbabwe", "de": "Simbabwe", "ru": "Зимбабве", "ar": "زيمبابوي", "pt": "Zimbábue", "hi": "ज़िम्बाब्वे"}),
}

#: El código de la OMS → el nombre con el que la vacuna se conoce, y la familia a la que
#: pertenece. La familia sirve para una sola cosa: darse cuenta de que dos filas en la misma
#: casilla son dos PRODUCTOS y no dos vacunas.
NOMBRES: dict[str, tuple[str, str]] = {
    "BCG": ("BCG (tuberculosis)", "bcg"),
    "HEPB_PEDIATRIC": ("Hepatitis B", "hepb"),
    "HEPA_PEDIATRIC": ("Hepatitis A", "hepa"),
    "DTAPHIBHEPBIPV": ("DTaP-Hib-HepB-IPV (hexavalent)", "dtp"),
    "DTWPHIBHEPB": ("DTwP-Hib-HepB (pentavalent)", "dtp"),
    "DTAPHIBHEPB": ("DTaP-Hib-HepB (pentavalent)", "dtp"),
    "DTAPHIBIPV": ("DTaP-Hib-IPV (pentavalent)", "dtp"),
    "DTAPHIB": ("DTaP-Hib", "dtp"),
    "DTAPIPV": ("DTaP-IPV", "dtp"),
    "DTAP": ("DTaP (diphtheria, tetanus, pertussis)", "dtp"),
    "DTWP": ("DTwP (diphtheria, tetanus, pertussis)", "dtp"),
    "TDAP_S": ("Tdap booster (tetanus, diphtheria, pertussis)", "td"),
    "TD_S": ("Td booster (tetanus, diphtheria)", "td"),
    "IPV": ("Polio, inactivated (IPV)", "ipv"),
    "IPV_FRAC": ("Polio, fractional inactivated (fIPV)", "ipv"),
    "OPV": ("Polio, oral (OPV)", "opv"),
    "MMR": ("MMR (measles, mumps, rubella)", "measles"),
    "MMRV": ("MMRV (measles, mumps, rubella, varicella)", "measles"),
    "MEASLES": ("Measles", "measles"),
    "MR": ("MR (measles, rubella)", "measles"),
    "VARICELLA": ("Varicella (chickenpox)", "varicella"),
    "PCV13": ("Pneumococcal conjugate, 13-valent", "pcv"),
    "PCV15": ("Pneumococcal conjugate, 15-valent", "pcv"),
    "PCV_15_VALENT": ("Pneumococcal conjugate, 15-valent", "pcv"),
    "PCV20": ("Pneumococcal conjugate, 20-valent", "pcv"),
    "PCV10": ("Pneumococcal conjugate, 10-valent", "pcv"),
    "ROTAVIRUS_1": ("Rotavirus, 2-dose course", "rota"),
    "ROTAVIRUS_5": ("Rotavirus, 3-dose course", "rota"),
    "MEN_ACYW_135CONJ": ("Meningococcal ACWY, conjugate", "men"),
    "MEN_AC_PS": ("Meningococcal AC, polysaccharide", "men"),
    "MENA_CONJ": ("Meningococcal A, conjugate", "men"),
    "MEN_B": ("Meningococcal B", "menb"),
    "MEN_C_CONJ": ("Meningococcal C, conjugate", "menc"),
    "HIB": ("Hib (Haemophilus influenzae b)", "hib"),
    "HPV2": ("HPV, 2-valent", "hpv"),
    "HPV4": ("HPV, 4-valent", "hpv"),
    "HPV9": ("HPV, 9-valent", "hpv"),
    "INFLUENZA_PEDIATRIC": ("Seasonal influenza", "flu"),
    "RSV_MONO": ("RSV antibody (nirsevimab)", "rsv"),
    "VITAMINA": ("Vitamin A (a supplement, not a vaccine)", "vita"),
    "TYPHOID_CONJ": ("Typhoid, conjugate", "typhoid"),
    # ── África, 18-sep-2026: lo que aquí no existe y allí es el calendario ───────────────
    # La de la malaria salía 24 veces en 48 países y este script la estaba TIRANDO por no
    # tener nombre. Es la vacuna nueva (RTS,S y R21) que la OMS recomendó para las zonas de
    # transmisión alta, y es justo la que un padre de Ghana o Kenia quiere ver en su tabla.
    # La meningocócica A es la del cinturón de la meningitis, del Sahel a Etiopía.
    "MALARIA": ("Malaria (RTS,S / R21)", "malaria"),
    "MEN_A_CONJ": ("Meningococcal A, conjugate", "men"),
    "MEN_A_PS": ("Meningococcal A, polysaccharide", "men"),
    "DTWPHIBHEPBIPV": ("DTwP-Hib-HepB-IPV (hexavalent)", "dtp"),
    "TDAP_S_IPV": ("Tdap-IPV booster", "td"),
    "DT": ("DT (diphtheria, tetanus, children's dose)", "dtp"),
}

#: Poblaciones que NO son «lo que le toca a un niño sano en el calendario».
#: Las que sí lo son quedan fuera de esta lista: None y GENERAL (el grueso del calendario),
#: B_CHILD_W / B_2YL_W / B_ADO_W y sus variantes (cohortes de edad: los refuerzos del segundo
#: año, de la edad escolar y de la adolescencia) y BOTH / FEMALE (el VPH).
#: Comprobado contra India: el refuerzo de DPT de los 5-6 años viaja como B_CHILD_W, así que
#: descartarlo le quitaría a la tabla india una vacuna que sí se pone.
POBLACION_FUERA = {
    "RISKGROUPS", "ADULTS", "PW", "HW", "TRAVELLERS", "SYRINGE", "PLANNED",
    "CATCHUP_C", "CATCHUP_A", "POSTPARTUM", "CB_AGED_WOMEN",
}
#: Lo que no es una cita sino una campaña que vuelve cada temporada.
CADA_AÑO = {"INFLUENZA_PEDIATRIC"}
#: Vacunas que no son de la infancia por mucho que aparezcan en la tabla del país.
VACUNAS_FUERA = {
    "TT", "TD_A", "INFLUENZA_ADULT", "COVID19", "HEPB_ADULT", "PPV23", "ZOSTER", "RABIES",
    "YF", "CHOLERA", "MPOX", "RSV", "TYPHOID_PS", "JE_INACTD", "HEPA_ADULT",
}

# ── cómo se dice una edad en ocho lenguas ────────────────────────────────────────────────────
#: singular, «pocos» (2-4, que es lo que pide el ruso), plural
_UNIDADES: dict[str, dict[str, tuple[str, str, str]]] = {
    "W": {"en": ("week", "weeks", "weeks"), "es": ("semana", "semanas", "semanas"),
          "fr": ("semaine", "semaines", "semaines"), "de": ("Woche", "Wochen", "Wochen"),
          "ru": ("неделя", "недели", "недель"), "ar": ("أسبوع", "أسابيع", "أسبوعا"),
          "pt": ("semana", "semanas", "semanas"), "hi": ("हफ़्ता", "हफ़्ते", "हफ़्ते")},
    "M": {"en": ("month", "months", "months"), "es": ("mes", "meses", "meses"),
          "fr": ("mois", "mois", "mois"), "de": ("Monat", "Monate", "Monate"),
          "ru": ("месяц", "месяца", "месяцев"), "ar": ("شهر", "أشهر", "شهرا"),
          "pt": ("mês", "meses", "meses"), "hi": ("महीना", "महीने", "महीने")},
    "Y": {"en": ("year", "years", "years"), "es": ("año", "años", "años"),
          "fr": ("an", "ans", "ans"), "de": ("Jahr", "Jahre", "Jahre"),
          "ru": ("год", "года", "лет"), "ar": ("سنة", "سنوات", "سنة"),
          "pt": ("ano", "anos", "anos"), "hi": ("साल", "साल", "साल")},
}
_AL_NACER = {"en": "At birth", "es": "Al nacer", "fr": "À la naissance", "de": "Bei der Geburt",
             "ru": "При рождении", "ar": "عند الولادة", "pt": "Ao nascer", "hi": "जन्म के समय"}
_DESDE = {"en": "From {x}", "es": "Desde los {x}", "fr": "À partir de {x}", "de": "Ab {x}",
          "ru": "С {x}", "ar": "من عمر {x}", "pt": "A partir dos {x}", "hi": "{x} से"}
_DUAL_AR = {"W": "أسبوعان", "M": "شهران", "Y": "سنتان"}


def _palabra(n: float, unidad: str, lang: str) -> str:
    """La unidad en la forma que pide el número. Al ruso y al árabe no les vale con la -s."""
    sing, pocos, muchos = _UNIDADES[unidad][lang]
    if n != int(n):
        # «3,6 года» y no «3,6 лет»: en ruso el decimal rige genitivo SINGULAR, que es la misma
        # forma que la de dos a cuatro. El árabe, en cambio, deja la unidad en singular.
        return muchos if lang == "ar" else pocos
    entero = int(n)
    if lang == "ru":
        # 11-14 van siempre en genitivo plural: «11 месяцев», nunca «11 месяца»
        if entero % 100 in (11, 12, 13, 14):
            return muchos
        if entero % 10 == 1:
            return sing
        if entero % 10 in (2, 3, 4):
            return pocos
        return muchos
    if lang == "ar":
        # el árabe cuenta distinto: uno, dos (dual), de tres a diez (plural), y de once en
        # adelante vuelve al singular
        if entero == 1:
            return sing
        if entero == 2:
            return _DUAL_AR[unidad]
        if 3 <= entero <= 10:
            return pocos
        return muchos
    return sing if entero == 1 else pocos


#: Lenguas que escriben el decimal con coma. Sólo asoma en una casilla —Kuwait reporta el
#: refuerzo preescolar como «Y3.6»— pero «3.6 Jahre» está mal escrito en alemán.
_COMA = {"es", "fr", "de", "pt", "ru"}
#: El alemán pide dativo detrás de «Ab»: «ab 6 Monaten», no «ab 6 Monate».
_DATIVO_DE = {"Wochen": "Wochen", "Monate": "Monaten", "Jahre": "Jahren"}


def _cifra(n: float, lang: str = "en") -> str:
    texto = f"{n:g}"
    return texto.replace(".", ",") if lang in _COMA else texto


def frase_edad(n: float, unidad: str, lang: str, hasta: float | None, desde: bool) -> str:
    if unidad == "B":
        return _AL_NACER[lang]
    if hasta is not None:
        # manda el número de arriba: «4-6 años», «4–6 лет». En árabe, un rango se lee siempre
        # como plural, sea cual sea el número, así que se le pide la forma de 3-10.
        cuenta = 3.0 if lang == "ar" else hasta
        texto = f"{_cifra(n, lang)}–{_cifra(hasta, lang)} {_palabra(cuenta, unidad, lang)}"
    elif lang == "ar" and n in (1.0, 2.0):
        texto = _palabra(n, unidad, lang)  # «شهران» ya dice «dos meses»; la cifra sobraría
    else:
        texto = f"{_cifra(n, lang)} {_palabra(n, unidad, lang)}"
    if not desde:
        return texto
    if lang == "de":
        cola = texto.rsplit(" ", 1)[-1]
        if cola in _DATIVO_DE:
            texto = texto[: -len(cola)] + _DATIVO_DE[cola]
    return _DESDE[lang].format(x=texto)


#: Lo que se le añade a la etiqueta de la gripe. Sin esto, «desde los 6 meses» parece una cita
#: única y es una campaña que se repite cada temporada mientras el niño esté en esa edad.
_CADA_AÑO = {"en": "{x}, every year", "es": "{x}, todos los años", "fr": "{x}, chaque année",
             "de": "{x}, jedes Jahr", "ru": "{x}, каждый год", "ar": "{x}، كل عام",
             "pt": "{x}, todos os anos", "hi": "{x}, हर साल"}


def etiqueta(
    n: float, unidad: str, hasta: float | None, desde: bool, cada_año: bool = False
) -> dict[str, str]:
    out = {lg: frase_edad(n, unidad, lg, hasta, desde) for lg in IDIOMAS}
    return {lg: _CADA_AÑO[lg].format(x=t) for lg, t in out.items()} if cada_año else out


def normaliza(meses: float, unidad: str, n: float, hasta: float | None):
    """La misma edad escrita de una sola manera.

    Kuwait reporta los doce meses como «M12» para la polio y como «Y1» para el sarampión, y los
    veinticuatro como «M24» y «Y2». Son el mismo día en la vida del niño, y si la tabla los
    imprime en dos filas distintas parece que hay dos visitas donde hay una. La regla es la que
    ya seguían los ocho calendarios escritos a mano: en meses hasta los dos años, en años a
    partir de ahí. Las semanas se quedan en semanas —el calendario indio se lee así, «a las seis
    semanas»— porque nadie cita a un lactante «al mes y medio».
    """
    if unidad == "Y" and meses < 24:
        return "M", n * 12, (hasta * 12 if hasta is not None else None)
    if unidad == "M" and meses >= 24 and n % 12 == 0 and (hasta is None or hasta % 12 == 0):
        return "Y", n / 12, (hasta / 12 if hasta is not None else None)
    return unidad, n, hasta


# ── cómo lee la OMS una edad ─────────────────────────────────────────────────────────────────
_EDAD = re.compile(r"^(>=|>|<=|<)?([BWMY])(\d+(?:\.\d+)?)?(?:-([BWMY])(\d+(?:\.\d+)?))?$")
_EN_MESES = {"B": 0.0, "W": 12.0 / 52.0, "M": 1.0, "Y": 12.0}


def lee_edad(bruto: str | None) -> tuple[float, str, float, float | None, bool] | None:
    """(meses, unidad, número, hasta, «a partir de»). None si la fila no dice CUÁNDO.

    Fuera quedan «1st contact», «+M6» y «+Y1»: son intervalos desde la dosis anterior, no
    edades. El «+» se recupera luego, colgándolo de la dosis de la que cuelga.
    """
    if not bruto:
        return None
    m = _EDAD.match(bruto.strip().upper())
    if not m:
        return None
    signo, unidad, valor, u2, v2 = m.groups()
    if signo in ("<", "<="):
        return None  # «antes de los 7 años» es un tope, no una cita
    if unidad == "B":
        return (0.0, "B", 0.0, None, False)
    if valor is None:
        return None
    n = float(valor)
    hasta = float(v2) if v2 is not None and u2 == unidad else None
    return (n * _EN_MESES[unidad], unidad, n, hasta, signo in (">=", ">"))


_INTERVALO = re.compile(r"^\+([DWMY])(\d+)(?:-[DWMY]\d+)?$")
_DESPUES = {"D": "days", "W": "weeks", "M": "months", "Y": "years"}


def lee_intervalo(bruto: str | None) -> str | None:
    """«+M6» → «6 months later»: lo que la OMS cuenta desde la dosis anterior."""
    if not bruto:
        return None
    m = _INTERVALO.match(bruto.strip().upper())
    return f"{m.group(2)} {_DESPUES[m.group(1)]} later" if m else None


# ── la tabla ─────────────────────────────────────────────────────────────────────────────────
def traer(iso3: str) -> list[dict]:
    q = urllib.parse.urlencode(
        {"$filter": f"COUNTRY eq '{iso3}'", "$orderby": "YEAR desc", "$top": "200"}, safe="$ '"
    )
    with urllib.request.urlopen(urllib.request.Request(f"{BASE}?{q}", headers=UA), timeout=90) as r:
        return list(json.load(r)["value"])


def calendario(iso3: str) -> tuple[int, list[dict], list[str]]:
    filas = traer(iso3)
    if not filas:
        raise SystemExit(f"{iso3}: la OMS no publica calendario")
    año = max(f["YEAR"] for f in filas)
    vivas = [
        f
        for f in filas
        if f["YEAR"] == año
        and f.get("GEOAREA") == "NATIONAL"
        and str(f.get("TARGETPOP")) not in POBLACION_FUERA
        and str(f["VACCINECODE"]) not in VACUNAS_FUERA
    ]
    fuera: list[str] = []
    # La casilla es (meses, hasta en meses, ¿es la campaña anual?). La unidad NO entra en la
    # clave: «M12» y «Y1» son la misma casilla aunque se escriban distinto. La gripe sí entra,
    # porque una campaña que se repite no puede fundirse con las vacunas de esa misma edad: el
    # buscador de «qué le toca a mi hijo» arrastra las casillas anuales a todas las edades
    # posteriores, y arrastraría con ellas la hexavalente de los 6 meses.
    casillas: dict[tuple, dict] = {}
    ultima: dict[str, tuple] = {}  # vacuna → la última casilla en la que aparece
    intervalos: list[tuple[str, str]] = []
    solo_niñas = {"FEMALE"}

    orden = sorted(vivas, key=lambda f: (str(f["VACCINECODE"]), int(f.get("SCHEDULEROUNDS") or 0)))
    for f in orden:
        codigo = str(f["VACCINECODE"])
        ficha = NOMBRES.get(codigo)
        if ficha is None:
            fuera.append(f"{codigo}: no está en la tabla de nombres del script")
            continue
        nombre, familia = ficha
        if str(f.get("TARGETPOP")) in solo_niñas:
            # El VPH saudí es sólo para niñas. Una tabla que no lo diga le promete a un padre
            # una vacuna que a su hijo no le van a poner.
            nombre += " (girls)"
        intervalo = lee_intervalo(f.get("AGEADMINISTERED"))
        if intervalo is not None:
            intervalos.append((codigo, intervalo))
            continue
        edad = lee_edad(f.get("AGEADMINISTERED"))
        if edad is None:
            fuera.append(f"{codigo}: edad sin fecha ({f.get('AGEADMINISTERED')})")
            continue
        meses, unidad, n, hasta, desde = edad
        unidad, n, hasta = normaliza(meses, unidad, n, hasta)
        hasta_meses = None if hasta is None else hasta * _EN_MESES[unidad]
        clave = (round(meses, 2), hasta_meses, codigo in CADA_AÑO)
        casilla = casillas.setdefault(
            clave, {"unidad": unidad, "n": n, "hasta": hasta, "desde": desde, "familias": {}}
        )
        # «desde los 2 años» sólo se mantiene si TODAS las filas de la casilla lo dicen: Kuwait
        # reporta la segunda de sarampión como «Y2» (la triple vírica) y como «>=Y2» (la
        # tetravírica), y son la misma cita con dos productos.
        casilla["desde"] = casilla["desde"] and desde
        familias = casilla["familias"]
        if nombre not in familias.setdefault(familia, []):
            familias[familia].append(nombre)
        ultima[codigo] = clave

    for codigo, intervalo in intervalos:
        clave = ultima.get(codigo)
        ficha = NOMBRES.get(codigo)
        if clave is None or ficha is None:
            fuera.append(f"{codigo}: dosis por intervalo sin dosis anterior ({intervalo})")
            continue
        nombre, familia = ficha
        nombres = casillas[clave]["familias"][familia]
        for i, existente in enumerate(nombres):
            if existente.startswith(nombre) and "later" not in existente:
                nombres[i] = f"{existente} — 2nd dose {intervalo}"
                break

    salida = []
    # 18-sep-2026, con los datos africanos: dos casillas pueden compartir edad y diferir en el
    # rango —una «a los 9 meses» y otra «de 9 a 12»— y entonces Python compara None con un
    # número al ordenar. El orden lo da la edad; el rango ausente se trata como el más corto.
    def _orden(par):
        (meses, hasta, gripe), _ = par
        return (meses, -1.0 if hasta is None else hasta, gripe)

    for (meses, _hasta_meses, es_gripe), casilla in sorted(casillas.items(), key=_orden):
        vacunas = [" or ".join(v) for _, v in sorted(casilla["familias"].items())]
        fila: dict = {
            "meses": round(meses, 1),
            "label": etiqueta(
                casilla["n"], casilla["unidad"], casilla["hasta"], casilla["desde"], es_gripe
            ),
            "vacunas": vacunas,
        }
        if es_gripe:
            fila["cada_año"] = True
        salida.append(fila)
    return año, salida, fuera


# ── el YAML ──────────────────────────────────────────────────────────────────────────────────
def nota(iso3: str) -> dict[str, str]:
    """Lo que hay que saber ANTES de leer la tabla: de dónde sale y qué no dice."""
    base = {
        "en": ("This is the schedule {pais} reports to WHO, published as data under WHO's open "
               "licence — not a copy of the ministry's own page. The ministry can change a date "
               "without WHO's file changing the same week, so if your health centre says "
               "something different, your health centre is right. Two products on one line are "
               "alternatives for a single injection, not two."),
        "es": ("Este es el calendario que {pais} le reporta a la OMS, publicado como datos con la "
               "licencia abierta de la OMS; no es una copia de la página del ministerio. El "
               "ministerio puede cambiar una fecha sin que el fichero de la OMS cambie esa misma "
               "semana, así que si tu centro de salud dice otra cosa, manda tu centro de salud. "
               "Dos productos en la misma línea son alternativas para un pinchazo, no dos."),
        "fr": ("Voici le calendrier que {pais} déclare à l'OMS, publié comme données sous la "
               "licence ouverte de l'OMS ; ce n'est pas une copie de la page du ministère. Le "
               "ministère peut changer une date sans que le fichier de l'OMS change la même "
               "semaine : si votre centre de santé dit autre chose, c'est lui qui a raison. Deux "
               "produits sur une ligne sont des alternatives pour une seule injection."),
        "de": ("Das ist der Impfkalender, den {pais} der WHO meldet, veröffentlicht als Daten "
               "unter der offenen Lizenz der WHO — keine Kopie der Ministeriumsseite. Das "
               "Ministerium kann ein Datum ändern, ohne dass sich die WHO-Datei in derselben "
               "Woche ändert; sagt Ihre Gesundheitsstelle etwas anderes, gilt sie. Zwei Produkte "
               "in einer Zeile sind Alternativen für eine Impfung, nicht zwei."),
        "ru": ("Это календарь, который {pais} сообщает ВОЗ, опубликованный как данные под "
               "открытой лицензией ВОЗ, а не копия страницы министерства. Министерство может "
               "изменить дату, а файл ВОЗ обновится не в ту же неделю; если в вашей поликлинике "
               "говорят иначе, правы они. Два препарата в одной строке — это варианты одной "
               "прививки, а не две."),
        "ar": ("هذا هو التقويم الذي تبلغ به {pais} منظمة الصحة العالمية، منشورا بيانات برخصة "
               "المنظمة المفتوحة، لا نسخة من صفحة الوزارة. وقد تغير الوزارة موعدا دون أن يتغير "
               "ملف المنظمة في الأسبوع نفسه، فإن قال المركز الصحي غير هذا فالقول قوله. وإذا ظهر "
               "منتجان في سطر واحد فهما بديلان لحقنة واحدة، لا حقنتان."),
        "pt": ("Este é o calendário que {pais} reporta à OMS, publicado como dados sob a licença "
               "aberta da OMS; não é uma cópia da página do ministério. O ministério pode mudar "
               "uma data sem que o ficheiro da OMS mude na mesma semana; se o seu centro de saúde "
               "disser outra coisa, manda o seu centro de saúde. Dois produtos na mesma linha são "
               "alternativas para uma injeção, não duas."),
        "hi": ("यह वह अनुसूची है जो {pais} विश्व स्वास्थ्य संगठन को बताता है — WHO के खुले लाइसेंस के तहत डेटा "
               "के रूप में प्रकाशित, मंत्रालय के पन्ने की नक़ल नहीं। मंत्रालय कोई तारीख़ बदल सकता है और WHO की "
               "फ़ाइल उसी हफ़्ते न बदले; अगर आपका स्वास्थ्य केंद्र कुछ और कहे, तो वही सही है। एक ही पंक्ति में दो "
               "उत्पाद हों तो वे एक ही टीके के विकल्प हैं, दो टीके नहीं।"),
    }
    extra = {
        "SAU": {
            "en": " Saudi Arabia has reported BCG at 6 months, not at birth, every year since 2019.",
            "es": " Arabia Saudí reporta la BCG a los 6 meses, no al nacer, todos los años desde 2019.",
            "fr": " L'Arabie saoudite déclare le BCG à 6 mois, et non à la naissance, depuis 2019.",
            "de": " Saudi-Arabien meldet BCG seit 2019 mit 6 Monaten, nicht bei der Geburt.",
            "ru": " С 2019 года Саудовская Аравия сообщает БЦЖ в 6 месяцев, а не при рождении.",
            "ar": " وتبلغ السعودية عن لقاح BCG في عمر ستة أشهر، لا عند الولادة، منذ عام 2019.",
            "pt": " A Arábia Saudita reporta a BCG aos 6 meses, não ao nascer, desde 2019.",
            "hi": " सऊदी अरब 2019 से हर साल BCG को जन्म पर नहीं, 6 महीने पर बताता है।",
        },
        "MUS": {
            "en": " Mauritius has reported BCG at 1 month, not at birth, every year since at least 2018.",
            "es": " Mauricio reporta la BCG al mes, no al nacer, todos los años desde 2018 por lo menos.",
            "fr": " Maurice déclare le BCG à 1 mois, et non à la naissance, depuis 2018 au moins.",
            "de": " Mauritius meldet BCG seit mindestens 2018 mit 1 Monat, nicht bei der Geburt.",
            "ru": " Маврикий как минимум с 2018 года сообщает БЦЖ в 1 месяц, а не при рождении.",
            "ar": " تبلغ موريشيوس عن لقاح BCG في عمر شهر، لا عند الولادة، منذ 2018 على الأقل.",
            "pt": " As Maurícias reportam a BCG ao 1.º mês, não ao nascer, desde pelo menos 2018.",
            "hi": " मॉरीशस कम से कम 2018 से BCG को जन्म पर नहीं, 1 महीने पर बताता है।",
        },
        "KWT": {
            "en": " Kuwait has reported BCG at 3 months, not at birth, for more than a decade, and it records the pre-school booster at «3.6 years» — between the third and fourth birthday. Both are copied here as reported.",
            "es": " Kuwait reporta la BCG a los 3 meses, no al nacer, desde hace más de diez años, y anota el refuerzo preescolar en «3,6 años» — entre el tercer y el cuarto cumpleaños. Las dos cosas van aquí tal como las reporta.",
            "fr": " Le Koweït déclare le BCG à 3 mois, et non à la naissance, depuis plus de dix ans, et note le rappel préscolaire à « 3,6 ans » — entre le troisième et le quatrième anniversaire. Les deux sont repris tels quels.",
            "de": " Kuwait meldet BCG seit über zehn Jahren mit 3 Monaten, nicht bei der Geburt, und die Vorschul-Auffrischung mit «3,6 Jahren» — zwischen dem dritten und vierten Geburtstag. Beides steht hier so, wie es gemeldet wurde.",
            "ru": " Кувейт уже более десяти лет сообщает БЦЖ в 3 месяца, а не при рождении, а дошкольную ревакцинацию указывает как «3,6 года» — между третьим и четвёртым днём рождения. И то и другое приведено так, как сообщено.",
            "ar": " وتبلغ الكويت عن لقاح BCG في عمر ثلاثة أشهر، لا عند الولادة، منذ أكثر من عشر سنوات، وتسجل جرعة ما قبل المدرسة عند «3.6 سنة» — أي بين عيد الميلاد الثالث والرابع. وكلاهما منقول كما ورد.",
            "pt": " O Kuwait reporta a BCG aos 3 meses, não ao nascer, há mais de dez anos, e regista o reforço pré-escolar em «3,6 anos» — entre o terceiro e o quarto aniversário. Ambos vão aqui tal como são reportados.",
            "hi": " कुवैत दस साल से ज़्यादा समय से BCG को जन्म पर नहीं, 3 महीने पर बताता है, और स्कूल से पहले वाले बूस्टर को «3.6 साल» पर दर्ज करता है — तीसरे और चौथे जन्मदिन के बीच। दोनों यहाँ वैसे ही हैं जैसे बताए गए।",
        },
    }
    nombres = PAISES[iso3][1]
    return {lg: base[lg].format(pais=nombres[lg]) + extra.get(iso3, {}).get(lg, "") for lg in IDIOMAS}


def _mapa(d: dict[str, str]) -> str:
    # json.dumps y no un f-string con comillas: una comilla dentro de una nota —«3.6 years»
    # escrito a la inglesa— parte el YAML por la mitad, y el fichero no se vuelve a abrir.
    # El escapado de JSON es exactamente el que acepta un escalar YAML entre comillas dobles.
    return "{" + ", ".join(f"{lg}: {json.dumps(d[lg], ensure_ascii=False)}" for lg in IDIOMAS) + "}"


def yaml_de(iso3: str, año: int, tabla: list[dict]) -> str:
    iso2, nombres = PAISES[iso3]
    hoy = dt.date.today().strftime("%d-%m-%Y")
    titulo = {
        lg: nombres[lg]
        + " — "
        + {
            "en": "national schedule", "es": "calendario nacional", "fr": "calendrier national",
            "de": "nationaler Impfkalender", "ru": "национальный календарь",
            "ar": "التقويم الوطني", "pt": "calendário nacional", "hi": "राष्ट्रीय टीकाकरण अनुसूची",
        }[lg]
        + f" ({año})"
        for lg in IDIOMAS
    }
    fuente = (
        f"WHO/UNICEF — national immunization schedule as reported by {nombres['en']} to WHO; "
        f"WIISE public dataset AD_SCHEDULES, {año} reporting year (consultado el {hoy})"
    )
    lineas = [f"  {iso2}:"]
    lineas.append(f"    name: {_mapa(titulo)}")
    lineas.append(f'    source: "{fuente}"')
    lineas.append(f'    source_url: "{PAGINA}{nombres["en"].lower().replace(" ", "-")}"')
    lineas.append(f"    note: {_mapa(nota(iso3))}")
    lineas.append("    schedule:")
    for fila in tabla:
        vs = ", ".join(f'"{v}"' for v in fila["vacunas"])
        cada = "every_year: true, " if fila.get("cada_año") else ""
        lineas.append(
            f"      - {{age: {fila['meses']:g}, label: {_mapa(fila['label'])}, {cada}"
            f"vaccines: [{vs}]}}"
        )
    return "\n".join(lineas)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paises", nargs="+", help="códigos ISO3: SAU ARE EGY QAT KWT")
    ap.add_argument("--write", action="store_true", help="lo añade a config/vaccines.yaml")
    args = ap.parse_args()

    salida = []
    for iso3 in args.paises:
        if iso3 not in PAISES:
            raise SystemExit(f"{iso3}: añádelo a PAISES con su nombre en las ocho lenguas")
        año, tabla, fuera = calendario(iso3)
        print(f"# {iso3}: año {año}, {len(tabla)} casillas", file=sys.stderr)
        for f in fuera:
            print(f"#   fuera: {f}", file=sys.stderr)
        salida.append(yaml_de(iso3, año, tabla))
    texto = "\n".join(salida)
    if not args.write:
        print(texto)
        return 0
    actual = DESTINO.read_text(encoding="utf-8")
    ya = [p for p in args.paises if f"\n  {PAISES[p][0]}:\n" in actual]
    if ya:
        raise SystemExit(f"ya están en el fichero: {ya}. Quítalos a mano antes de reescribirlos.")
    DESTINO.write_text(actual.rstrip("\n") + "\n" + texto + "\n", encoding="utf-8")
    print(f"escritos en {DESTINO.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
