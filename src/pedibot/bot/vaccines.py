"""Tabulated vaccination schedules (config/vaccines.yaml). Deterministic — the LLM never invents dates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from pedibot.bot.strings import data_lang, tool_strings

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
    # nombre oficial en hindi, que no se parece en nada a «India» y no casaría solo
    "IN": ("india", "inde", "indien", "индия", "инди", "الهند", "índia", "भारत", "hindustan"),
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
        "usa",
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
        "riad",
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
        "catar",
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
        "burkina", "burkina faso", "burquina", "burquina faso", "буркина", "буркина-фасо",
        "بوركينا", "بوركينا فاسو", "बुर्किना फ़ासो",
    ),
    "BI": ("burundi", "бурунди", "بوروندي", "बुरुंडी"),
    "BJ": ("benin", "benín", "bénin", "бенин", "بنين", "बेनिन"),
    "BW": ("botsuana", "botswana", "ботсван", "بوتسوانا", "बोत्स्वाना"),
    "CD": (
        "congo kinshasa", "congo-kinshasa", "democratic republic of the congo",
        "demokratische republik kongo", "dr congo", "kinshasa", "kongo-kinshasa", "rd congo",
        "rd del congo", "republica democratica del congo", "republique democratique du congo",
        "república democrática del congo", "république démocratique du congo", "конго-киншаса",
        "الكونغو-كينشاسا", "كينشاسا", "कांगो-किंशासा",
    ),
    "CF": (
        "central african republic", "republica centro-africana", "republica centroafricana",
        "republique centrafricaine", "república centro-africana", "república centroafricana",
        "république centrafricaine", "zentralafrikanische republik",
        "центрально-африканская республика", "جمهورية أفريقيا الوسطى", "मध्य अफ़्रीकी गणराज्य",
    ),
    "CG": (
        "brazzaville", "congo", "congo brazzaville", "congo-brazzaville", "kongo-brazzaville",
        "republic of the congo", "republica do congo", "republique du congo", "república do congo",
        "конго", "конго-браззавиль", "الكونغو", "الكونغو-برازافيل", "कांगो", "कांगो-ब्राज़ाविल",
    ),
    "CI": (
        "costa de marfil", "costa do marfim", "cote d'ivoire", "cote divoire", "côte d'ivoire",
        "elfenbeinkueste", "elfenbeinküste", "ivory coast", "кот-д'ивуар", "ساحل العاج",
        "कोत दिवुआर",
    ),
    "CM": (
        "camaroes", "camarões", "cameroon", "cameroun", "camerun", "camerún", "kamerun", "камерун",
        "الكاميرون", "कैमरून",
    ),
    "CV": ("cabo verde", "cap-vert", "cape verde", "кабо-верде", "الرأس الأخضر", "केप वर्ड"),
    "DJ": ("djibouti", "djibuti", "dschibuti", "yibuti", "джибути", "جيبوتي", "जिबूती"),
    "ER": ("eritrea", "eritreia", "erythree", "érythrée", "эритре", "إريتريا", "इरिट्रिया"),
    "ET": (
        "aethiopien", "athiopien", "ethiopia", "ethiopie", "etiopia", "etiopía", "etiópia",
        "äthiopien", "éthiopie", "эфиопи", "إثيوبيا", "इथियोपिया",
    ),
    "GA": ("gabao", "gabon", "gabun", "gabão", "gabón", "габон", "الغابون", "गैबॉन"),
    "GH": ("ghana", "غانا", "घाना"),
    "GM": ("gambia", "gambie", "gâmbia", "гамби", "غامبيا", "गाम्बिया"),
    "GN": ("guinee", "guiné", "guinée", "гвине", "غينيا", "गिनी"),
    "GQ": (
        "aquatorialguinea", "equatorial guinea", "guine equatorial", "guinea ecuatorial",
        "guinee equatoriale", "guiné equatorial", "guinée équatoriale", "äquatorialguinea",
        "экваториальная гвинея", "غينيا الاستوائية", "इक्वेटोरियल गिनी",
    ),
    "GW": (
        "guine-bissau", "guinea bisau", "guinea bissau", "guinea-bisau", "guinea-bissau",
        "guinea-bisáu", "guinee-bissau", "guiné-bissau", "guinée-bissau", "гвинея-бисау",
        "غينيا بيساو", "गिनी-बिसाउ",
    ),
    "KE": ("kenia", "kenya", "quenia", "quênia", "кени", "كينيا", "केन्या"),
    "KM": ("comoras", "comores", "comoros", "komoren", "коморы", "جزر القمر", "कोमोरोस"),
    "LR": ("liberia", "libéria", "либери", "ليبيريا", "लाइबेरिया"),
    "LS": ("lesotho", "lesoto", "лесото", "ليسوتو", "लेसोथो"),
    "MG": ("madagascar", "madagaskar", "мадагаскар", "مدغشقر", "मेडागास्कर"),
    "MR": (
        "mauretanien", "mauritania", "mauritanie", "mauritânia", "мавритани", "موريتانيا",
        "मॉरिटानिया",
    ),
    "MU": (
        "ile maurice", "isla mauricio", "mauritius", "île maurice", "маврики", "маврикий",
        "موريشيوس", "मॉरीशस",
    ),
    "MW": ("malaui", "malawi", "малави", "ملاوي", "मलावी"),
    "MZ": (
        "mocambique", "mosambik", "mozambique", "moçambique", "мозамбик", "موزمبيق", "मोज़ांबिक",
    ),
    "NA": ("namibia", "namibie", "namíbia", "намиби", "ناميبيا", "नामीबिया"),
    "NG": ("nigeria", "nigéria", "нигери", "نيجيريا", "नाइजीरिया"),
    "RW": ("ruanda", "rwanda", "руанд", "رواندا", "रवांडा"),
    "SC": (
        "seicheles", "seychellen", "seychelles", "сейшел", "сейшельские о-ва", "سيشل", "सेशेल्स",
    ),
    "SL": (
        "serra leoa", "sierra leona", "sierra leone", "сьерра-леоне", "سيراليون", "सिएरा लियोन",
    ),
    "SN": ("senegal", "sénégal", "сенегал", "السنغال", "सेनेगल"),
    "SO": ("somalia", "somalie", "somália", "сомали", "الصومال", "सोमालिया"),
    "SS": (
        "soudan du sud", "south sudan", "sudan del sur", "sudao do sul", "sudsudan",
        "sudán del sur", "sudão do sul", "südsudan", "южный судан", "جنوب السودان", "दक्षिण सूडान",
    ),
    "ST": (
        "principe", "santo tome", "santo tome y principe", "santo tomé", "santo tomé y príncipe",
        "sao tome", "sao tome e principe", "sao tome und principe", "sao tome y principe",
        "sao tome-et-principe", "sao tomé-et-principe", "são tomé", "são tomé e príncipe",
        "são tomé und príncipe", "são tomé y príncipe", "сан-томе и принсипи",
        "ساو تومي وبرينسيبي", "साओ टोम और प्रिंसिपे",
    ),
    "SZ": ("essuatini", "essuatíni", "esuatini", "eswatini", "эсватини", "إسواتيني", "एस्वाटिनी"),
    "TZ": ("tansania", "tanzania", "tanzanie", "tanzânia", "танзани", "تنزانيا", "तंज़ानिया"),
    "UG": ("ouganda", "uganda", "уганд", "أوغندا", "युगांडा"),
    "ZA": (
        "africa do sul", "afrique du sud", "south africa", "sudafrica", "sudafrika", "sudáfrica",
        "suedafrika", "südafrika", "áfrica do sul", "южно-африканская республика", "جنوب أفريقيا",
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
    "US": re.compile(r"\b(?:the u\.?s\.?|u\.?s\.?a\.?)\b", re.I),
    # «قطر» es Catar y también el principio de «قطرة», que es una GOTA: la palabra con la que un
    # padre árabe cuenta el jarabe que le ha dado a su hijo. Sin el paréntesis de abajo, «كم قطرة
    # أعطيه» —«¿cuántas gotas le doy?»— se leería como una pregunta sobre Catar. Igual «مصر»
    # dentro de «مصري», «مصرية» y «مصرف».
    "QA": re.compile(r"قطر(?![ةه])"),
    "EG": re.compile(r"مصر(?![يةه])"),
    # ── África, 18-sep-2026: los nombres que viven dentro de otra palabra ─────────
    # «Mali» está dentro de «maligno», «maligne» y «malignant». «Niger» está dentro de
    # «Nigeria», y la frontera sí los distingue: después de «niger» viene una «i», que
    # es letra. «Чад» está dentro de «чадо», que es «criatura». Y «guinea pig» es el
    # conejillo de Indias, así que Guinea se lee sólo si detrás no viene «pig».
    "CD": re.compile("\\b(?:rdc|drc)\\b", re.I),
    "GH": re.compile("\\bгана\\b", re.I),
    "GN": re.compile("\\bguinea\\b(?!\\s*(?:pig|fowl))", re.I),
    "ML": re.compile("\\b(?:mal[ií]|мали|مالي|माली)\\b", re.I),
    "NE": re.compile("\\b(?:n[ií]ger|нигер|النيجر|नाइजर)\\b", re.I),
    "TD": re.compile("\\b(?:t?chad|tschad|chade|تشاد|चाड)\\b", re.I),
    "TG": re.compile("\\b(?:togo|توغو|टोगो)\\b", re.I),
}


def country_in_question(text: str) -> str | None:
    """The country the question names out loud, or None.

    Longest name wins, so "reino unido" is not read as a shorter name that happens to sit inside
    it. Only consulted when the reader picked no country: a country they wrote themselves beats a
    guess, and there is no guess to fall back on.
    """
    low = text.lower()
    best: tuple[int, str] | None = None
    for code, names in COUNTRY_IN_TEXT.items():
        for name in names:
            if name in low and (best is None or len(name) > best[0]):
                best = (len(name), code)
    if best is not None:
        return best[1]
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
        out = []
        for s in self.raw[country]["schedule"]:
            lg = data_lang(s["label"], lang)
            out.append(
                Slot(
                    float(s["age"]), s["label"][lg], list(s["vaccines"]), bool(s.get("every_year"))
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


def format_answer(v: Vaccines, country: str, age_months: float | None, lang: str = "en") -> str:
    T = tool_strings(lang)
    m = v.meta(country, lang)
    if age_months is None:
        sched = v.schedule(country, lang)
        lines = [f"{m['name']}:"]
        for s in sched:
            lines.append(f"• {s.label}: " + ", ".join(s.vaccines))
        lines.append(T["vax_source"] + m["source"] + ". " + m["note"])
        return "\n".join(lines)
    due, nxt = v.at_age(country, age_months, lang)
    lines = []
    if due:
        lines.append(T["vax_due"])
        for s in due:
            lines.append(f"• {s.label}: " + ", ".join(s.vaccines))
    else:
        lines.append(T["vax_none"])
    if nxt:
        lines.append(T["vax_next"].format(label=nxt.label) + ", ".join(nxt.vaccines))
    lines.append(T["vax_source"] + m["source"] + ". " + m["note"])
    return "\n".join(lines)
