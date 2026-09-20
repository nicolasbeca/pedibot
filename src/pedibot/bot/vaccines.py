"""Tabulated vaccination schedules (config/vaccines.yaml). Deterministic — the LLM never invents dates."""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from pedibot.bot.strings import data_lang, tool_strings
from pedibot.bot.vaccine_names import list_separator, localise

#: "Is this about vaccines?" — the gate to the vaccination tables, which are the most visited
#: pages on the site. It knew Spanish, English and French, so German, Russian, Arabic, Hindi and
#: PORTUGUESE ("vacina", no u) fell through to the corpus and never saw a calendar at all.
#: Devanagari sits outside the `\b(...)\b` group: `\w` excludes its combining vowel signs, so a
#: word boundary after टीके never matches — the same property that broke the triage patterns and
#: the query tokeniser.
_VACC = re.compile(
    r"\b("
    r"vacun\w*|vacin\w*|vaccin\w*|inmuniz\w*|immuniz\w*|imuniz\w*"
    r"|impf\w*|geimpft"
    r"|привив\w*|вакцин\w*"
    r"|teeka|teeke|teekaakaran"
    r"|shots?|jabs?|mmr|dtap|dtpa|menb|hpv|vph|triple v[ií]rica"
    r")\b"
    # Devanagari y árabe van FUERA del grupo con `\b`, y no por descuido: `\b` se define
    # sobre `\w`, y en estas escrituras el artículo y el plural son caracteres de palabra.
    # En «اللقاحات» la raíz لقاح lleva ال delante y ات detrás, así que no hay ninguna frontera
    # y `\bاللقاح\b` no casa nunca. El devanagari ya estaba fuera por esta misma razón; el
    # árabe seguía dentro y no detectaba media pregunta (7-sep-2026).
    r"|टीक|वैक्सीन"
    r"|تطعيم|تلقيح"
    # «حبوب اللقاح» es el POLEN, no una vacuna: una pregunta por la alergia al polen no puede
    # acabar en el calendario de vacunación.
    # Dos lookbehind encadenados y no una alternancia: `re` exige anchura fija en cada uno,
    # y «حبوب » (5) y «حبوب ال» (7) no la comparten. El primero cubre la forma desnuda y el
    # segundo la del artículo, que era la que se colaba.
    r"|(?<!حبوب )(?<!حبوب ال)لقاح",
    re.I,
)
COUNTRY_ALIASES = {"UK": "GB", "EN": "GB", "USA": "US", "SPAIN": "ES", "ESPAÑA": "ES"}

#: Country names as a parent writes them, in the eight languages of the site. Used ONLY to read a
#: country the question states out loud — never to infer one from the language. A French speaker
#: may be in Belgium, Canada or Switzerland, and handing a Belgian family the French calendar
#: would be worse than saying nothing, because it would look right.
COUNTRY_IN_TEXT: dict[str, tuple[str, ...]] = {
    "ES": (
        "españa",
        "espana",
        "spain",
        "espagne",
        "spanien",
        "испани",
        "إسبانيا",
        "espanha",
        "स्पेन",
    ),
    # India: «Hindustan» va porque es como mucha gente escribe su país, y «भारत» es el
    # nombre oficial en hindi, que no se parece en nada a «India» y no casaría solo.
    #
    # 18-sep-2026: «inde» y «инди» se han bajado a COUNTRY_SHORT, con frontera de palabra.
    # «inde» vivía dentro de «Windeln» —que es «pañales» en alemán— y el golden tiene una
    # frase de deshidratación que dice «sie macht kaum Windeln nass»: una madre alemana
    # contando que su hija apenas moja pañales estaba siendo leída como si dijera «India».
    # También dentro de «independiente» y de «indexado». «инди» vive dentro de
    # «индивидуальный».
    "IN": ("india", "indien", "الهند", "índia", "भारत", "hindustan"),
    "FR": ("francia", "france", "frankreich", "франци", "فرنسا", "frança", "फ़्रांस", "फ्रांस"),
    "DE": (
        "alemania",
        "germany",
        "allemagne",
        "deutschland",
        "герман",
        "ألمانيا",
        "alemanha",
        "जर्मनी",
    ),
    "GB": (
        "reino unido",
        "united kingdom",
        "royaume-uni",
        "vereinigtes königreich",
        "великобритани",
        "المملكة المتحدة",
        "inglaterra",
        "england",
        "angleterre",
        "यूनाइटेड किंगडम",
    ),
    "US": (
        "estados unidos",
        "united states",
        "états-unis",
        "etats-unis",
        "vereinigte staaten",
        "сша",
        "الولايات المتحدة",
        "eeuu",
        "अमेरिका",
        # 18-sep-2026: «usa» a secas se ha bajado, y no por la frontera de palabra sino porque
        # es una palabra española corriente: «la CAUSA exacta del fallo», «mi hija no USA el
        # orinal», «hay que USAR el termómetro». Treinta y dos veces en el corpus del propio
        # proyecto. Arriba se queda lo que sólo puede ser el país; abajo, en mayúsculas, la
        # sigla — que es como se escribe «USA» cuando se quiere decir Estados Unidos.
    ),
    "PT": ("portugal", "португали", "البرتغال", "पुर्तगाल"),
    # El Golfo y Egipto (17-sep-2026). Van también las CIUDADES que la gente nombra en lugar del
    # país —«en Dubái», «en Doha»—, porque es como se escribe de verdad cuando uno vive allí.
    # «مصر» y «قطر» no están aquí sino abajo, con lupa: escritas así, sin más, se meten dentro de
    # «قطرة» (una gota de jarabe) y de «مصرية», y una pregunta de dosis acabaría en un calendario.
    "SA": (
        "arabia saudí",
        "arabia saudita",
        "saudi arabia",
        "arabie saoudite",
        "saudi-arabien",
        "саудовск",
        "السعودية",
        "السعوديه",
        "arábia saudita",
        "सऊदी अरब",
        # «riad» se lee abajo con frontera: está dentro de «resfriado». 18-sep-2026.
        "riyadh",
        "الرياض",
        "جدة",
        "jeddah",
    ),
    "AE": (
        "emiratos",
        "united arab emirates",
        "émirats",
        "emirats",
        "vereinigte arabische emirate",
        "эмират",
        "оаэ",
        "الإمارات",
        "الامارات",
        "emirados",
        "संयुक्त अरब अमीरात",
        "dubai",
        "dubái",
        "dubaï",
        "دبي",
        "abu dhabi",
        "abu dabi",
        "أبوظبي",
        "أبو ظبي",
        "sharjah",
        "الشارقة",
    ),
    "MA": (
        "marruecos",
        "morocco",
        "maroc",
        "marokko",
        "марокко",
        "المغرب",
        "marrocos",
        "मोरक्को",
        "casablanca",
        "rabat",
        "marrakech",
        "الدار البيضاء",
        "طنجة",
    ),
    "TN": (
        "túnez",
        "tunez",
        "tunisia",
        "tunisie",
        "tunesien",
        "тунис",
        "تونس",
        "tunísia",
        "ट्यूनीशिया",
        "sfax",
    ),
    "DZ": (
        "argelia",
        "algeria",
        "algérie",
        "algerie",
        "algerien",
        "алжир",
        "الجزائر",
        "argélia",
        "अल्जीरिया",
        "argel",
    ),
    "LY": (
        "libia",
        "libya",
        "libye",
        "libyen",
        "ливия",
        "ليبيا",
        "líbia",
        "लीबिया",
        "trípoli",
        "tripoli",
        "bengasi",
        "benghazi",
    ),
    "SD": (
        "sudán",
        "soudan",
        "судан",
        "السودان",
        "sudão",
        "सूडान",
        "jartum",
        "khartoum",
        "الخرطوم",
        "omdurman",
    ),
    "EG": (
        "egipto",
        "egypt",
        "égypte",
        "egypte",
        "ägypten",
        "египет",
        "египт",
        "egito",
        "मिस्र",
        "el cairo",
        "cairo",
        "القاهرة",
        "الإسكندرية",
    ),
    "QA": (
        # «catar» se lee abajo con frontera: vive dentro de «catarro» y de «se acatarra», que
        # son de las palabras más dichas por un padre español. 18-sep-2026.
        "qatar",
        "katar",
        "катар",
        "क़तर",
        "कतर",
        "doha",
        "الدوحة",
    ),
    "KW": (
        "kuwait",
        "koweït",
        "koweit",
        "кувейт",
        "الكويت",
        "कुवैत",
    ),
    "BR": (
        "brasil",
        "brazil",
        "brésil",
        "bresil",
        "brasilien",
        "бразили",
        "البرازيل",
        "ब्राज़ील",
        "ब्राजील",
    ),
    # ── África, 18-sep-2026 ───────────────────────────────────────────────────────────
    # 48 países de golpe. Los nombres salen del CLDR en los ocho idiomas y se les añade lo
    # que un padre escribe de verdad y el CLDR no da: «RD Congo», «RDC», «Kinshasa», «Costa
    # de Marfil», «ЮАР». Al ruso se le quita la vocal final —«Нигерия» → «нигери»— porque
    # declina: un padre escribe «в Нигерии», no «Нигерия».
    #
    # Cuatro países no están aquí y están abajo, en COUNTRY_SHORT, por la misma razón por
    # la que «us» y «uk» estaban ya allí: su nombre vive dentro de otra palabra. «Mali»
    # dentro de «maligno», «niger» dentro de «Nigeria», «чад» dentro de «чадо» —que es
    # «criatura»— y «togo» que en ruso es «того», el genitivo de «тот». Ghana en ruso es
    # «гана», que vive dentro de «органа». Y Ghana en portugués es «Gana», que es el verbo
    # español de «mi bebé no gana peso»: esa forma no se puede usar de ninguna manera.
    "AO": ("angola", "ангол", "أنغولا", "अंगोला"),
    "BF": (
        "burkina",
        "burkina faso",
        "burquina",
        "burquina faso",
        "буркина",
        "буркина-фасо",
        "بوركينا",
        "بوركينا فاسو",
        "बुर्किना फ़ासो",
    ),
    "BI": ("burundi", "бурунди", "بوروندي", "बुरुंडी"),
    "BJ": ("benin", "benín", "bénin", "бенин", "بنين", "बेनिन"),
    "BW": ("botsuana", "botswana", "ботсван", "بوتسوانا", "बोत्स्वाना"),
    "CD": (
        "congo kinshasa",
        "congo-kinshasa",
        "democratic republic of the congo",
        "demokratische republik kongo",
        "dr congo",
        "kinshasa",
        "kongo-kinshasa",
        "rd congo",
        "rd del congo",
        "republica democratica del congo",
        "republique democratique du congo",
        "república democrática del congo",
        "république démocratique du congo",
        "конго-киншаса",
        "الكونغو-كينشاسا",
        "كينشاسا",
        "कांगो-किंशासा",
    ),
    "CF": (
        "central african republic",
        "republica centro-africana",
        "republica centroafricana",
        "republique centrafricaine",
        "república centro-africana",
        "república centroafricana",
        "république centrafricaine",
        "zentralafrikanische republik",
        "центрально-африканская республика",
        "جمهورية أفريقيا الوسطى",
        "मध्य अफ़्रीकी गणराज्य",
    ),
    "CG": (
        "brazzaville",
        "congo",
        "congo brazzaville",
        "congo-brazzaville",
        "kongo-brazzaville",
        "republic of the congo",
        "republica do congo",
        "republique du congo",
        "república do congo",
        "конго",
        "конго-браззавиль",
        "الكونغو",
        "الكونغو-برازافيل",
        "कांगो",
        "कांगो-ब्राज़ाविल",
    ),
    "CI": (
        "costa de marfil",
        "costa do marfim",
        "cote d'ivoire",
        "cote divoire",
        "côte d'ivoire",
        "elfenbeinkueste",
        "elfenbeinküste",
        "ivory coast",
        "кот-д'ивуар",
        "ساحل العاج",
        "कोत दिवुआर",
    ),
    "CM": (
        "camaroes",
        "camarões",
        "cameroon",
        "cameroun",
        "camerun",
        "camerún",
        "kamerun",
        "камерун",
        "الكاميرون",
        "कैमरून",
    ),
    "CV": ("cabo verde", "cap-vert", "cape verde", "кабо-верде", "الرأس الأخضر", "केप वर्ड"),
    "DJ": ("djibouti", "djibuti", "dschibuti", "yibuti", "джибути", "جيبوتي", "जिबूती"),
    "ER": ("eritrea", "eritreia", "erythree", "érythrée", "эритре", "إريتريا", "इरिट्रिया"),
    "ET": (
        "aethiopien",
        "athiopien",
        "ethiopia",
        "ethiopie",
        "etiopia",
        "etiopía",
        "etiópia",
        "äthiopien",
        "éthiopie",
        "эфиопи",
        "إثيوبيا",
        "इथियोपिया",
    ),
    "GA": ("gabao", "gabon", "gabun", "gabão", "gabón", "габон", "الغابون", "गैबॉन"),
    "GH": ("ghana", "غانا", "घाना"),
    "GM": ("gambia", "gambie", "gâmbia", "гамби", "غامبيا", "गाम्बिया"),
    "GN": ("guinee", "guiné", "guinée", "гвине", "غينيا", "गिनी"),
    "GQ": (
        "aquatorialguinea",
        "equatorial guinea",
        "guine equatorial",
        "guinea ecuatorial",
        "guinee equatoriale",
        "guiné equatorial",
        "guinée équatoriale",
        "äquatorialguinea",
        "экваториальная гвинея",
        "غينيا الاستوائية",
        "इक्वेटोरियल गिनी",
    ),
    "GW": (
        "guine-bissau",
        "guinea bisau",
        "guinea bissau",
        "guinea-bisau",
        "guinea-bissau",
        "guinea-bisáu",
        "guinee-bissau",
        "guiné-bissau",
        "guinée-bissau",
        "гвинея-бисау",
        "غينيا بيساو",
        "गिनी-बिसाउ",
    ),
    "KE": ("kenia", "kenya", "quenia", "quênia", "кени", "كينيا", "केन्या"),
    "KM": ("comoras", "comores", "comoros", "komoren", "коморы", "جزر القمر", "कोमोरोस"),
    "LR": ("liberia", "libéria", "либери", "ليبيريا", "लाइबेरिया"),
    "LS": ("lesotho", "lesoto", "лесото", "ليسوتو", "लेसोथो"),
    "MG": ("madagascar", "madagaskar", "мадагаскар", "مدغشقر", "मेडागास्कर"),
    "MR": (
        "mauretanien",
        "mauritania",
        "mauritanie",
        "mauritânia",
        "мавритани",
        "موريتانيا",
        "मॉरिटानिया",
    ),
    "MU": (
        "ile maurice",
        "isla mauricio",
        "mauritius",
        "île maurice",
        "маврики",
        "маврикий",
        "موريشيوس",
        "मॉरीशस",
    ),
    "MW": ("malaui", "malawi", "малави", "ملاوي", "मलावी"),
    "MZ": (
        "mocambique",
        "mosambik",
        "mozambique",
        "moçambique",
        "мозамбик",
        "موزمبيق",
        "मोज़ांबिक",
    ),
    "NA": ("namibia", "namibie", "namíbia", "намиби", "ناميبيا", "नामीबिया"),
    "NG": ("nigeria", "nigéria", "нигери", "نيجيريا", "नाइजीरिया"),
    "RW": ("ruanda", "rwanda", "руанд", "رواندا", "रवांडा"),
    "SC": (
        "seicheles",
        "seychellen",
        "seychelles",
        "сейшел",
        "сейшельские о-ва",
        "سيشل",
        "सेशेल्स",
    ),
    "SL": (
        "serra leoa",
        "sierra leona",
        "sierra leone",
        "сьерра-леоне",
        "سيراليون",
        "सिएरा लियोन",
    ),
    "SN": ("senegal", "sénégal", "сенегал", "السنغال", "सेनेगल"),
    "SO": ("somalia", "somalie", "somália", "сомали", "الصومال", "सोमालिया"),
    "SS": (
        "soudan du sud",
        "south sudan",
        "sudan del sur",
        "sudao do sul",
        "sudsudan",
        "sudán del sur",
        "sudão do sul",
        "südsudan",
        "южный судан",
        "جنوب السودان",
        "दक्षिण सूडान",
    ),
    "ST": (
        "principe",
        "santo tome",
        "santo tome y principe",
        "santo tomé",
        "santo tomé y príncipe",
        "sao tome",
        "sao tome e principe",
        "sao tome und principe",
        "sao tome y principe",
        "sao tome-et-principe",
        "sao tomé-et-principe",
        "são tomé",
        "são tomé e príncipe",
        "são tomé und príncipe",
        "são tomé y príncipe",
        "сан-томе и принсипи",
        "ساو تومي وبرينسيبي",
        "साओ टोम और प्रिंसिपे",
    ),
    "SZ": ("essuatini", "essuatíni", "esuatini", "eswatini", "эсватини", "إسواتيني", "एस्वाटिनी"),
    "TZ": ("tansania", "tanzania", "tanzanie", "tanzânia", "танзани", "تنزانيا", "तंज़ानिया"),
    "UG": ("ouganda", "uganda", "уганд", "أوغندا", "युगांडा"),
    "ZA": (
        "africa do sul",
        "afrique du sud",
        "south africa",
        "sudafrica",
        "sudafrika",
        "sudáfrica",
        "suedafrika",
        "südafrika",
        "áfrica do sul",
        "южно-африканская республика",
        "جنوب أفريقيا",
        "दक्षिण अफ़्रीका",
    ),
    "ZM": ("sambia", "zambia", "zambie", "zâmbia", "замби", "زامبيا", "ज़ाम्बिया"),
    "ZW": ("simbabwe", "zimbabue", "zimbabwe", "zimbábue", "зимбабве", "زيمبابوي", "ज़िम्बाब्वे"),
}


#: Las formas cortas, que son como un padre nombra de verdad su país en inglés: «in the UK»,
#: «in the US». Faltaban las dos —y el mercado primero del producto es el inglés—, así que
#: «What vaccines are due at 12 months in the UK?» no llegaba a la tabla y se iba al corpus.
#:
#: Van aparte y con frontera de palabra porque la búsqueda de arriba es por subcadena, y con dos
#: letras eso es una trampa: «us» vive dentro de *because*, *must* y hasta de *bukhar*, y «uk»
#: dentro de *Ukraine*. Con «us» no basta la frontera —es un pronombre inglés corriente: «tell us
#: what vaccines»— así que se exige el artículo delante, que es como se escribe el país.
#:
#: «America» se queda fuera a propósito: en castellano y en portugués nombra el continente, y
#: leerlo como Estados Unidos le enseñaría a un padre colombiano el calendario que no es.
COUNTRY_SHORT: dict[str, re.Pattern[str]] = {
    "GB": re.compile(r"\b(?:uk|u\.k\.|great britain|britain|gro(?:ß|ss)britannien)\b", re.I),
    # «the US» y «U.S.A.» con puntos sólo pueden ser el país. La sigla sin puntos y sin
    # artículo se lee más abajo, en COUNTRY_UPPER, y en mayúsculas.
    "US": re.compile(r"\bthe u\.?s\.?a?\.?\b|\bu\.s\.a?\.?\b", re.I),
    # 18-sep-2026, medido sobre el corpus del propio proyecto: estos tres vivían arriba, como
    # subcadena, y casaban dentro de palabras que un padre dice todos los días.
    #   «catar»  dentro de «catarro» y de «se acatarra»          (8 veces en el corpus)
    #   «riad»   dentro de «resfriado»
    #   «inde»   dentro de «Windeln» —pañales, en alemán—, «independiente» e «indexado» (46)
    # El golden tiene una frase de deshidratación que dice «sie macht kaum Windeln nass»: una
    # madre alemana contando que su hija apenas moja pañales se leía como si dijera India.
    "SA": re.compile(r"\briad\b", re.I),
    # 20-sep-2026, con el norte de África: «sudan» vive dentro de «sudando», y esa palabra
    # está en una alarma de diabetes («sudoroso, sudando, con sed»). Un padre contando que
    # su hijo suda se leía como si dijera Sudán. Es el mismo fallo que el «ni» suajili, y lo
    # cazó el mismo candado antes de salir. «oran», por Orán, vivía dentro de «llorando»,
    # «piorando» y «malodorant».
    "SD": re.compile(r"\b(?:sudan|sud[áa]n)\b", re.I),
    "DZ": re.compile(r"\bor[áa]n\b", re.I),
    # «инди» está dentro de «индивидуальный»; con la frontera y como mucho cinco letras más
    # entran «Индия», «Индии» e «индийский», y se queda fuera la palabra larga.
    "IN": re.compile(r"\binde\b|\bинди\w{0,5}\b", re.I),
    # «قطر» es Catar y también el principio de «قطرة», que es una GOTA: la palabra con la que un
    # padre árabe cuenta el jarabe que le ha dado a su hijo. Sin el paréntesis de abajo, «كم قطرة
    # أعطيه» —«¿cuántas gotas le doy?»— se leería como una pregunta sobre Catar. Igual «مصر»
    # dentro de «مصري», «مصرية» y «مصرف».
    "QA": re.compile(r"\bcatar\b|قطر(?![ةه])", re.I),
    "EG": re.compile(r"مصر(?![يةه])"),
    # ── África, 18-sep-2026: los nombres que viven dentro de otra palabra ─────────
    # «Mali» está dentro de «maligno», «maligne» y «malignant». «Niger» está dentro de
    # «Nigeria», y la frontera sí los distingue: después de «niger» viene una «i», que
    # es letra. «Чад» está dentro de «чадо», que es «criatura». Y «guinea pig» es el
    # conejillo de Indias, así que Guinea se lee sólo si detrás no viene «pig».
    #
    # Pero la frontera de palabra sólo vale para el alfabeto latino y el cirílico, y esto se
    # escribió primero con `\b` alrededor de TODOS los nombres. Eso repitió dos fallos que ya
    # estaban en LESSONS: en árabe el artículo y las preposiciones se pegan a la palabra
    # —«بمالي» es «en Malí» y no tiene ninguna frontera delante (L138)— y en devanagari `\b`
    # se define sobre `\w`, que no incluye las vocales que cuelgan de la consonante: «माली»
    # acaba en «ी», que para `re` no es letra, así que `माली\b` no casa nunca (L164). Siete de
    # trece frases de prueba salían vacías.
    #
    # Cada escritura lleva lo suyo: frontera donde la frontera existe, y el nombre desnudo en
    # árabe y en devanagari, donde lo que hay que acotar se acota mirando alrededor.
    "CD": re.compile(r"\b(?:rdc|drc)\b", re.I),
    # el ruso declina y el padre escribe «в Гане», no «Гана»: la terminación entra en el
    # patrón, y la frontera sigue dejando fuera «органа» y «органе», que es lo que se buscaba.
    "GH": re.compile(r"\bган[аеуы]\b", re.I),
    "GN": re.compile(r"\bguinea\b(?!\s*(?:pig|fowl))", re.I),
    # «مالي» es Malí y también «financiero»: se pide que no lleve el artículo pegado delante
    # —«المالي» es «el financiero»— y que no sea el principio de «ماليزيا», que es Malasia.
    "ML": re.compile(r"\b(?:mal[ií]|мали)\b|(?<!ال)مالي(?!زيا)|माली", re.I),
    # «в Нигере» es Níger; «Нигерия» se lee arriba, en la tabla larga, y gana por más larga
    "NE": re.compile(r"\bn[ií]ger\b|\bнигер[аеоу]?\b|نيجر|नाइजर", re.I),
    "TD": re.compile(r"\b(?:t?chad|tschad|chade)\b|تشاد|चाड", re.I),
    "TG": re.compile(r"\btogo\b|توغو|टोगो", re.I),
}


#: Las siglas, y estas SÍ miran las mayúsculas (18-sep-2026).
#:
#: «USA» en mayúsculas sólo puede ser el país. En minúsculas es el verbo español más corriente
#: que existe en este producto: «mi hija no usa el orinal», «hay que usar el termómetro», «la
#: causa exacta» —«causa» lleva «usa» dentro—. Estaba en la tabla de subcadenas y casaba treinta
#: y dos veces en el corpus del propio proyecto.
#:
#: Por eso se busca sobre el texto tal como lo escribió el padre, sin bajarlo a minúsculas: es
#: el único dato que separa las dos cosas, y tirarlo era lo que hacía imposible distinguirlas.
COUNTRY_UPPER: dict[str, re.Pattern[str]] = {
    "US": re.compile(r"\bUSA\b|\bEE\.? ?UU\.?\b"),
}


def country_in_question(text: str) -> str | None:
    """The country the question names out loud, or None.

    Longest name wins, so "reino unido" is not read as a shorter name that happens to sit inside
    it. Only consulted when the reader picked no country: a country they wrote themselves beats a
    guess, and there is no guess to fall back on.

    Three tables and the order matters. First the full names, by substring, longest first —
    "Equatorial Guinea" beats "Guinea". Then the acronyms, ON THE ORIGINAL TEXT, because "USA"
    is a country and "usa" is a Spanish verb. Last the short forms with a word boundary, which
    are the ones that live inside other words.
    """
    low = text.lower()
    best: tuple[int, str] | None = None
    for code, names in COUNTRY_IN_TEXT.items():
        for name in names:
            if name in low and (best is None or len(name) > best[0]):
                best = (len(name), code)
    if best is not None:
        return best[1]
    for code, rx in COUNTRY_UPPER.items():
        if rx.search(text):
            return code
    for code, rx in COUNTRY_SHORT.items():
        if rx.search(low):
            return code
    return None


@dataclass(frozen=True)
class Slot:
    age_months: float
    label: str
    vaccines: list[str]
    every_year: bool = False


class Vaccines:
    def __init__(self, path: Path):
        self.raw = yaml.safe_load(path.read_text(encoding="utf-8"))["countries"]

    @property
    def countries(self) -> list[str]:
        return list(self.raw)

    def resolve_country(self, country: str | None) -> str | None:
        if not country:
            return None
        c = COUNTRY_ALIASES.get(country.upper(), country.upper())
        return c if c in self.raw else None

    def schedule(self, country: str, lang: str = "en") -> list[Slot]:
        """El calendario de ese país, con los nombres en el idioma del que pregunta.

        La traducción se hace AQUÍ y no en cada pantalla a propósito: por debajo de esta función
        pasan el chat, la cartilla del hijo, el `.ics` del calendario del teléfono y el JSON que
        alimenta la web. Traducir en cuatro sitios es tener cuatro sitios donde se olvida
        (20-sep-2026: 58 de los 66 calendarios vienen en inglés del almacén de la OMS, y un padre
        marroquí leía «Vitamin A (a supplement, not a vaccine)» dentro de su respuesta en árabe).
        """
        out = []
        for s in self.raw[country]["schedule"]:
            lg = data_lang(s["label"], lang)
            out.append(
                Slot(
                    float(s["age"]),
                    s["label"][lg],
                    [localise(str(n), lang) for n in s["vaccines"]],
                    bool(s.get("every_year")),
                )
            )
        return sorted(out, key=lambda x: x.age_months)

    def meta(self, country: str, lang: str = "en") -> dict[str, str]:
        c = self.raw[country]
        return {
            "name": c["name"][data_lang(c["name"], lang)],
            "source": c["source"],
            "source_url": c.get("source_url", ""),
            "note": c["note"][data_lang(c["note"], lang)],
            # En ISO, siempre. La cita no lo lleva dentro a propósito: «consultado el» es
            # nuestro, no del documento, y cada pantalla lo escribe en su idioma.
            "checked": str(c.get("checked") or ""),
        }

    def at_age(
        self, country: str, age_months: float, lang: str = "en"
    ) -> tuple[list[Slot], Slot | None]:
        """Slots due around this age (±1.5 months for infants, ±6 months after 2 years) and the next one."""
        sched = self.schedule(country, lang)
        tol = 1.5 if age_months < 24 else 6.0
        due = [s for s in sched if not s.every_year and abs(s.age_months - age_months) <= tol]
        due += [s for s in sched if s.every_year and s.age_months <= age_months]
        nxt = next((s for s in sched if not s.every_year and s.age_months > age_months + tol), None)
        return due, nxt


def is_vaccine_question(text: str) -> bool:
    return bool(_VACC.search(text))


def fecha_comprobada(meta: dict[str, str], lang: str) -> str:
    """« (comprobado el 18 de septiembre de 2026)», o nada si no consta.

    El día y el mes en cifras se leen al revés en medio mundo: «09-18» es septiembre para un
    lector y el 9 de un mes dieciocho que no existe para el otro. Con el mes escrito no hay
    forma de equivocarse, y es una línea de pie que se lee una vez.
    """
    iso = meta.get("checked")
    if not iso:
        return ""
    T = tool_strings(lang)
    plantilla = T.get("vax_checked")
    if not plantilla:
        return ""
    try:
        dia = _dt.date.fromisoformat(iso)
    except ValueError:
        return ""
    return plantilla.format(date=_fecha_larga(dia, lang))


#: Los meses, escritos, en las ocho lenguas. `Intl` hace esto en el navegador; aquí no hay
#: navegador, y `locale` depende de lo que tenga instalado el servidor, que no es de fiar.
_MESES: dict[str, tuple[str, ...]] = {
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "es": (
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ),
    "fr": (
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ),
    "de": (
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ),
    "ru": (
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ),
    "ar": (
        "يناير",
        "فبراير",
        "مارس",
        "أبريل",
        "مايو",
        "يونيو",
        "يوليو",
        "أغسطس",
        "سبتمبر",
        "أكتوبر",
        "نوفمبر",
        "ديسمبر",
    ),
    "pt": (
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    ),
    "hi": (
        "जनवरी",
        "फ़रवरी",
        "मार्च",
        "अप्रैल",
        "मई",
        "जून",
        "जुलाई",
        "अगस्त",
        "सितंबर",
        "अक्तूबर",
        "नवंबर",
        "दिसंबर",
    ),  # El suajili entra por la capa de seguridad y todavía no tiene web; la fecha sí la
    # escribe, porque el triaje le contesta y una fecha en inglés ahí canta igual.
    "sw": (
        "Januari",
        "Februari",
        "Machi",
        "Aprili",
        "Mei",
        "Juni",
        "Julai",
        "Agosti",
        "Septemba",
        "Oktoba",
        "Novemba",
        "Desemba",
    ),
}


def _fecha_larga(dia: _dt.date, lang: str) -> str:
    meses = _MESES.get(lang) or _MESES["en"]
    mes = meses[dia.month - 1]
    if lang == "en":
        return f"{mes} {dia.day}, {dia.year}"
    if lang == "de":
        return f"{dia.day}. {mes} {dia.year}"
    if lang in ("ru", "ar", "hi", "sw"):
        return f"{dia.day} {mes} {dia.year}"
    if lang == "fr":
        return f"{dia.day} {mes} {dia.year}"
    return f"{dia.day} de {mes} de {dia.year}"


def format_answer(v: Vaccines, country: str, age_months: float | None, lang: str = "en") -> str:
    T = tool_strings(lang)
    sep = list_separator(lang)
    m = v.meta(country, lang)
    if age_months is None:
        sched = v.schedule(country, lang)
        lines = [f"{m['name']}:"]
        for s in sched:
            lines.append(f"• {s.label}: " + sep.join(s.vaccines))
        lines.append(T["vax_source"] + m["source"] + fecha_comprobada(m, lang) + ". " + m["note"])
        return "\n".join(lines)
    due, nxt = v.at_age(country, age_months, lang)
    lines = []
    if due:
        lines.append(T["vax_due"])
        for s in due:
            lines.append(f"• {s.label}: " + sep.join(s.vaccines))
    else:
        lines.append(T["vax_none"])
    if nxt:
        lines.append(T["vax_next"].format(label=nxt.label) + sep.join(nxt.vaccines))
    lines.append(T["vax_source"] + m["source"] + fecha_comprobada(m, lang) + ". " + m["note"])
    return "\n".join(lines)
