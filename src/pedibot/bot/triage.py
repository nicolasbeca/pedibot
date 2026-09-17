"""Rule-based severity triage. Runs before any LLM call (CLAUDE.md rule 3 and 5).

Levels: emergency > urgent > mental_health > routine.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

LEVEL_ORDER = {"routine": 0, "mental_health": 1, "urgent": 2, "emergency": 3}

# `\b` is useless after Devanagari: most words end in a combining vowel sign, which Python does
# not count as a word character, so there is no boundary there to match. This pair works for both
# scripts — "not followed by a letter, a digit or any Devanagari sign" — and is what every age
# lookup below uses instead.
DEV = "\u0900-\u097f"
NOT_BEFORE = rf"(?<![\w{DEV}])"
NOT_AFTER = rf"(?![\w{DEV}])"

#: La misma frase escrita deprisa (17-sep-2026).
#:
#: Medido cogiendo las 408 frases de la batería y quitándoles lo que un padre se salta: **23
#: dejaban de saltar, y 17 eran árabes**. Un padre que escribe «حمي» en vez de «حمى», «انفه» en
#: vez de «أنفه» o «بشده» en vez de «بشدة» no recibía ningún aviso — y así es como se teclea en
#: un móvil, sin teclado con hamza y sin ganas a las tres de la mañana.
#:
#: La búsqueda ya normalizaba el árabe desde el 16-sep; el triaje, no. Se arregla en un sitio y
#: no en mil patrones, y se aplica a LAS DOS PARTES: al texto del padre y a los patrones al
#: cargarlos. Si sólo se aplanara el texto, los patrones escritos con hamza dejarían de casar.
#:
#: Qué se aplana y qué no, que es lo delicado:
#:
#: - latinas: las tildes, **y sólo sobre letra latina**. Es la misma regla que el índice (`fold`);
#: - cirílico: sólo la ё, a mano. La й lleva un breve combinante pero es una LETRA, y quitárselo
#:   rompe media lengua («детей» → «детеи»);
#: - árabe: hamza (أ إ آ ٱ ؤ ئ), ة→ه, ى→ي y fuera los harakat. Es lo que hace `_normaliza_ar` en
#:   la búsqueda desde el 16-sep;
#: - devanagari: **sólo el nuqta** (क़→क, ज़→ज, ड़→ड, फ़→फ), que es lo que se pierde al teclear.
#:   Las matras NO se tocan: son la palabra, no un adorno («बुखार» sin matras no es nada).
_LATINA_BASE = re.compile(r"[a-zA-Z]")
_ARABE_ORTO = str.maketrans(
    {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ؤ": "و", "ئ": "ي", "ة": "ه", "ى": "ي"}
)
_HARAKAT = dict.fromkeys(range(0x064B, 0x0653))
_NUQTA = "\u093c"


def aplana(texto: str) -> str:
    """El texto sin lo que se cae al escribir deprisa. Se aplica al padre y a los patrones."""
    fuera: list[str] = []
    for c in unicodedata.normalize("NFD", texto):
        if c == _NUQTA:
            continue
        if unicodedata.combining(c):
            if fuera and _LATINA_BASE.match(fuera[-1]):
                continue  # tilde sobre letra latina
            if 0x064B <= ord(c) <= 0x0652:
                continue  # harakat árabe
            fuera.append(c)  # matra devanagari, breve de la й: son la palabra
        else:
            fuera.append(c)
    unido = unicodedata.normalize("NFC", "".join(fuera))
    return unido.translate(_ARABE_ORTO).translate(_HARAKAT).replace("ё", "е").replace("Ё", "Е")


_AGE_PATTERNS = [
    # (regex, unit multiplier to months)
    (
        re.compile(
            r"(\d{1,2})\s*(?:meses|m[eê]s|months?|mois|monate[n]?|monat|monatig\w*|mo|месяц\w*|мес"
            r"|شهرا?|أشهر|شهور)\b",
            re.I,
        ),
        1.0,
    ),
    (
        re.compile(
            r"(\d{1,2}(?:[.,]\d)?)\s*(?:años|año|anos|years?|yrs?|ans?|jahre[n]?|jahr|j[äa]hrig\w*|год\w*|лет|سنة|سنوات|سنين|y\.?o\.?)\b",
            re.I,
        ),
        12.0,
    ),
    (
        re.compile(
            r"(\d{1,2})\s*(?:semanas|semana|weeks?|semaines?|wochen|woche|w[öo]chig\w*|недел\w*|нед|أسبوع|أسابيع|wks?)\b",
            re.I,
        ),
        1 / 4.345,
    ),
    (
        re.compile(
            r"(\d{1,2})\s*(?:d[ií]as|d[ií]a|days?|jours?)\s*(?:de (?:vida|edad|nacid|vie)|old)",
            re.I,
        ),
        1 / 30.4,
    ),
    (re.compile(r"(?:tiene|has|is|de)\s+(\d{1,2})\s*(?:a|y)\b", re.I), 12.0),
    # Hindi, in both scripts. Separate entries because they end with NOT_AFTER instead of `\b`.
    (
        re.compile(
            rf"(\d{{1,2}})\s*(?:महीने|महीना|महीनों|माह|मास|mahin[ae]|maheene){NOT_AFTER}", re.I
        ),
        1.0,
    ),
    (re.compile(rf"(\d{{1,2}})\s*(?:साल|वर्ष|बरस|s[a]?al|varsh){NOT_AFTER}", re.I), 12.0),
    (
        re.compile(rf"(\d{{1,2}})\s*(?:हफ़्ते|हफ्ते|हफ़्ता|हफ्ता|सप्ताह|haft[ae]|saptah){NOT_AFTER}", re.I),
        1 / 4.345,
    ),
    # «10 दिन का» solo es una edad cuando detrás va el niño: «10 दिन का बच्चा» es un bebé de
    # diez días y «10 दिन का बुखार» son diez días DE fiebre, que es un niño de cualquier edad.
    # Sin el sustantivo, un niño de cinco años con fiebre desde hace diez días recibía el
    # aviso del lactante menor de tres meses, con ese motivo escrito en el banner.
    (
        re.compile(
            rf"(\d{{1,2}})\s*(?:दिन|din)\s*(?:का|के|की|ka|ke)\s*"
            rf"(?:बच्चा|बच्ची|बच्चे|शिशु|नवजात|बेटा|बेटी|bachch[aei]|shishu|navjat|bet[ai]|baby)"
            rf"{NOT_AFTER}",
            re.I,
        ),
        1 / 30.4,
    ),
]
_NEWBORN = re.compile(
    r"reci[eé]n nacid|rec[eé]m[- ]?nascid|newborn|neonat|nouveau[- ]n[eé]|neugeboren|новорожд"
    r"|حديث الولادة|مولود جديد|नवजात|navjat|naujaat",
    re.I,
)
_NEWBORN = re.compile(aplana(_NEWBORN.pattern), _NEWBORN.flags)
_AGE_PATTERNS = [(re.compile(aplana(rx.pattern), rx.flags), m) for rx, m in _AGE_PATTERNS]

_WORD_AGES_CRUDO = {
    # «Año y medio» en las ocho lenguas, y ANTES de «un año»: el diccionario se recorre en orden
    # y «un año» ganaba a «un año y medio». 6 de 39 formas naturales fallaban, y las seis eran
    # un niño de 18 meses, justo donde cambian la dosis y las reglas (12-sep-2026).
    "año y medio": 18,
    "a year and a half": 18,
    "one and a half years": 18,
    "un an et demi": 18,
    "anderthalb jahre": 18,
    "eineinhalb jahre": 18,
    "полтора года": 18,
    "سنة ونصف": 18,
    "डेढ़ साल": 18,
    "ano e meio": 18,
    "un mes": 1,
    # Las semanas en letra: es como se dice la edad de un recién nacido, y en cifra ya se
    # entendían. «mi bebé de tres semanas» no llegaba a la regla del lactante (7-sep-2026).
    # 17-sep-2026: en francés y portugués las semanas en letra no se leían, y es como se dice
    # la edad de un recién nacido en los dos.
    "une semaine": 0.23,
    "deux semaines": 0.46,
    "trois semaines": 0.69,
    "quatre semaines": 0.92,
    "six semaines": 1.38,
    "uma semana": 0.23,
    "duas semanas": 0.46,
    "três semanas": 0.69,
    "quatro semanas": 0.92,
    "una semana": 0.23,
    "dos semanas": 0.46,
    "tres semanas": 0.69,
    "cuatro semanas": 0.92,
    "cinco semanas": 1.15,
    "seis semanas": 1.38,
    "siete semanas": 1.61,
    "ocho semanas": 1.84,
    "one week": 0.23,
    "two weeks": 0.46,
    "three weeks": 0.69,
    "four weeks": 0.92,
    "five weeks": 1.15,
    "six weeks": 1.38,
    "seven weeks": 1.61,
    "eight weeks": 1.84,
    "two week": 0.46,
    "three week": 0.69,
    "six week": 1.38,
    "1 mes": 1,
    "dos meses": 2,
    "tres meses": 3,
    "one month": 1,
    "two months": 2,
    "three months": 3,
    # "my two month old" — English drops the plural when the age is used as an adjective, and
    # that is the phrasing a parent types
    "two month": 2,
    "three month": 3,
    "un año": 12,
    "dos años": 24,
    "one year": 12,
    "two years": 24,
    "un mois": 1,
    "deux mois": 2,
    "trois mois": 3,
    "un an": 12,
    "deux ans": 24,
    "ein monat": 1,
    "einem monat": 1,
    "zwei monate": 2,
    "zwei monaten": 2,
    "drei monate": 3,
    "drei monaten": 3,
    "ein jahr": 12,
    "einem jahr": 12,
    "zwei jahre": 24,
    "zwei jahren": 24,
    "один месяц": 1,
    "месяц": 1,
    "два месяца": 2,
    "три месяца": 3,
    "год": 12,
    "одного года": 12,
    "два года": 24,
    # Arabic has a form of its own for exactly two, and it is the age that matters most here
    "شهر": 1,
    "شهر واحد": 1,
    "شهران": 2,
    "شهرين": 2,
    "ثلاثة أشهر": 3,
    "ثلاثة اشهر": 3,
    "سنة": 12,
    "سنة واحدة": 12,
    "سنتان": 24,
    "سنتين": 24,
    # Portuguese: it had been riding on the Spanish words, which works for "meses" and not for "mês"
    "um mês": 1,
    "um mes": 1,
    "dois meses": 2,
    "três meses": 3,
    "um ano": 12,
    "dois anos": 24,
    # Hindi, both scripts
    "एक महीने": 1,
    "एक महीना": 1,
    "एक माह": 1,
    "दो महीने": 2,
    "दो महीना": 2,
    "तीन महीने": 3,
    "एक साल": 12,
    "दो साल": 24,
    "ek mahina": 1,
    "ek mahine": 1,
    "do mahine": 2,
    "teen mahine": 3,
    "ek saal": 12,
    "do saal": 24,
}

#: Aplanadas al construirse: el texto llega sin tildes ni hamza, y una clave con ellas no
#: casaría nunca («año y medio» contra «ano y medio»).
_WORD_AGES = {aplana(k): v for k, v in _WORD_AGES_CRUDO.items()}


@dataclass
class Rule:
    id: str
    level: str
    source: str
    reason_es: str
    reason_en: str
    #: every other language, keyed by code. It used to be one field per language with the
    #: loader copying each by name, so a new language silently answered in English — which
    #: is what happened to Hindi, on the component where silence is worst.
    reasons_by_lang: dict[str, str] = field(default_factory=dict)
    patterns: list[re.Pattern[str]] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)


@dataclass
class TriageResult:
    level: str
    matched: list[Rule]
    age_months: float | None
    has_fever: bool

    def reasons(self, lang: str = "en") -> list[str]:
        def pick(r: Rule) -> str:
            # a lookup, not a ladder of ifs: a new language used to mean remembering to add
            # a branch here, and forgetting meant silently answering in English
            if lang == "es":
                return r.reason_es
            return r.reasons_by_lang.get(lang) or r.reason_en

        return [pick(r) for r in self.matched]

    @property
    def is_alarm(self) -> bool:
        return self.level != "routine"


#: El alemán pega el número a la unidad y le añade la terminación del adjetivo: «zweimonatiges
#: Baby», «dreijährige Tochter», «achtwöchiges Kind». Era el único de los ocho idiomas que no
#: sabía leer su propia forma natural de decir la edad —«meine 3-jährige Tochter hat Fieber»
#: devolvía None y la respuesta salía preguntando la edad que estaba escrita en la frase— y con
#: ella se caía también «mein 2-monatiges Baby hat Fieber», que es la regla del lactante.
_DE_NUM = {
    "ein": 1,
    "eine": 1,
    "einem": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fünf": 5,
    "funf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
    "elf": 11,
    "zwölf": 12,
    "zwolf": 12,
}
_DE_UNIDAD = {
    "jährig": 12.0,
    "jahrig": 12.0,
    "monatig": 1.0,
    "wöchig": 1 / 4.345,
    "wochig": 1 / 4.345,
}
_DE_COMPUESTO = re.compile(
    r"(?<![\w])(ein|eine|einem|zwei|drei|vier|fünf|funf|sechs|sieben|acht|neun|zehn|elf"
    r"|zwölf|zwolf)(jährig|jahrig|monatig|wöchig|wochig)\w*",
    re.I,
)
_DE_COMPUESTO = re.compile(aplana(_DE_COMPUESTO.pattern), _DE_COMPUESTO.flags)

#: Y lo mismo en ruso, que es donde más falta hacía (17-sep-2026).
#:
#: Medido: de seis formas naturales de decir la edad de un bebé en ruso, **las seis se perdían**.
#: «Двухмесячный ребёнок» es como se dice de verdad —no «ребёнку 2 месяца»—, y el lector exigía
#: una cifra delante de la unidad. Eso dejaba sin alcanzar la regla del lactante con fiebre, que
#: es la más importante que hay, exactamente igual que le pasó al hindi el 5-sep y por lo mismo.
#:
#: «Летн» exige prefijo a propósito: sin él, «летний» es *de verano* y no *de un año*.
_RU_NUM = {
    "": 1.0, "одно": 1.0, "полу": 0.5, "полутора": 1.5, "двух": 2.0, "трёх": 3.0, "трех": 3.0,
    "четырёх": 4.0, "четырех": 4.0, "пяти": 5.0, "шести": 6.0, "семи": 7.0, "восьми": 8.0,
    "девяти": 9.0, "десяти": 10.0, "одиннадцати": 11.0, "двенадцати": 12.0,
}
_RU_UNIDAD = {"месячн": 1.0, "недельн": 1 / 4.345, "летн": 12.0, "годовал": 12.0}
_RU_PREFIJOS = "|".join(sorted((k for k in _RU_NUM if k), key=len, reverse=True))
_RU_COMPUESTO = re.compile(
    rf"(?<![\w])({_RU_PREFIJOS})?(месячн|недельн|годовал)\w*|(?<![\w])({_RU_PREFIJOS})(летн)\w*",
    re.I,
)
_RU_COMPUESTO = re.compile(aplana(_RU_COMPUESTO.pattern), _RU_COMPUESTO.flags)


#: Guiones de todas las formas: el corto, el largo, el de las cifras y los que mete un procesador
#: de texto. Todos separan el número de la unidad exactamente igual que un espacio.
_GUIONES = re.compile(r"[-\u2010\u2011\u2012\u2013\u2014\u2015\u2212]+")


#: «Menos de», delante de una edad, la invierte. En las ocho lenguas.
#:
#: El lector sacaba el número y perdía el cualificador, así que «bebé menor de 3 meses con
#: fiebre» daba exactamente 3,0 meses — y la regla del lactante se dispara con `< 3`. La frase
#: con la que la propia regla está escrita, y con la que la lista de urgencias del SEUP la
#: enuncia, no la disparaba (9-sep-2026).
_MENOS_DE = re.compile(
    r"(menor(es)? de|menos de|de menos de|no llega a"
    r"|under|less than|younger than|below"
    r"|moins de|de moins de"
    r"|unter|weniger als|j[üu]nger als"
    r"|abaixo de|menos de|com menos de"
    r"|меньше"
    r"|до "
    r"|أقل من"
    r"|سن من)"
    r"[\s]{0,3}$",
    re.I,
)
_MENOS_DE = re.compile(aplana(_MENOS_DE.pattern), _MENOS_DE.flags)

#: Cuánto se mira hacia atrás para encontrarlo. Corto: el cualificador va pegado al número.
_VENTANA_MENOS = 14


#: El hindi lo pospone: «3 महीने से कम» es «menos de 3 meses» con el cualificador DETRÁS del
#: número. Mirar solo hacia atrás no podía verlo — lo cazó el candado que exige que todo detector
#: cubra las cuatro escrituras, que es justo para lo que está.
_MENOS_DE_DETRAS = re.compile(
    r"^[\s]{0,3}(से कम|से छोट|"
    r"से नीचे|or less|or younger|o menos)",
    re.I,
)
_MENOS_DE_DETRAS = re.compile(aplana(_MENOS_DE_DETRAS.pattern), _MENOS_DE_DETRAS.flags)


def parse_age_months(text: str) -> float | None:
    """La edad en meses, si la pregunta la dice.

    Los guiones se convierten en espacios antes de mirar nada. Los patrones de abajo separan el
    número de la unidad con `\\s*`, y un guion no es un espacio: hasta el 7-sep-2026
    «My 2-month-old has a fever» devolvía None y se quedaba en «rutina», mientras que
    «My 2 month old has a fever» daba 2 meses y **urgente**. La fiebre en un lactante de menos de
    tres meses es de las reglas más importantes que hay, y un guion la apagaba en silencio.

    Se arregla aquí, en un sitio, y no en cada expresión: así lo heredan los ocho idiomas, las
    edades en cifra y las escritas en letra («six-week-old»).
    """
    # se aplana aquí también: `assess` ya le pasa el texto aplanado, pero esta función se
    # llama sola desde la API, desde Telegram y desde las pruebas (17-sep-2026)
    low = aplana(_GUIONES.sub(" ", text.lower()))
    if _NEWBORN.search(low):
        return 0.5
    for phrase, months in _WORD_AGES.items():
        m = re.search(rf"{NOT_BEFORE}{re.escape(phrase)}{NOT_AFTER}", low)
        if m:
            edad = float(months)
            # el mismo cualificador que abajo: «de menos de un mes» es otra cosa que «un mes»,
            # y la edad en letra se resuelve en este bucle, antes de llegar al otro
            antes = low[max(0, m.start() - _VENTANA_MENOS) : m.start()]
            detras = low[m.end() : m.end() + _VENTANA_MENOS]
            if _MENOS_DE.search(antes) or _MENOS_DE_DETRAS.search(detras):
                edad = max(0.0, edad - 0.5)
            return edad
    compuesto = _DE_COMPUESTO.search(low)
    if compuesto:
        return _DE_NUM[compuesto.group(1)] * _DE_UNIDAD[compuesto.group(2)]
    ruso = _RU_COMPUESTO.search(low)
    if ruso:
        prefijo = ruso.group(1) or ruso.group(3) or ""
        unidad = ruso.group(2) or ruso.group(4)
        return _RU_NUM[prefijo.lower()] * _RU_UNIDAD[unidad.lower()]
    for rx, mult in _AGE_PATTERNS:
        m = rx.search(low)
        if m:
            edad = float(m.group(1).replace(",", ".")) * mult
            antes = low[max(0, m.start() - _VENTANA_MENOS) : m.start()]
            detras = low[m.end() : m.end() + _VENTANA_MENOS]
            if _MENOS_DE.search(antes) or _MENOS_DE_DETRAS.search(detras):
                # medio escalón por debajo: no se busca una edad exacta, se busca que la
                # comparación con los cortes de 1 y 3 meses caiga del lado correcto
                edad = max(0.0, edad - 0.5 * mult)
            return edad
    return None


#: Lo que anula una señal si aparece justo antes de ella. Un padre que escribe «sin dificultad
#: para respirar» está diciendo lo contrario de lo que la regla busca, y hasta el 7-sep-2026
#: recibía una alarma de emergencia por decirlo.
NEGADORES = re.compile(
    r"(?:\bsin\b|\bno\b|\bni\b|\bnada de\b"
    r"|\bwithout\b|\bno\b|\bnot\b|\bdoes ?n[o']?t\b|\bhas ?n[o']?t\b|\bisn[o']?t\b"
    r"|\bsans\b|\bpas de\b|\baucun\w*\b"
    r"|\bohne\b|\bkein\w*\b|\bnicht\b"
    r"|\bsem\b|\bn[ãa]o\b"
    r"|\bбез\b|\bне\b|\bнет\b"
    r"|بدون|بلا|ليس|لا\s"
    r"|बिना|नहीं)"
    r"[\s\wáéíóúüñ,]{0,18}$",
    re.I | re.U,
)

#: Preguntar CÓMO EVITAR algo no es que ese algo esté pasando (17-sep-2026).
#:
#: Salió al escribir el nombre de las cosas —«golpe de calor», «Hitzschlag»— como patrón suelto:
#: «¿cómo prevenir un golpe de calor en verano?» pasó a urgente. Lo cazó una prueba que ya estaba.
#:
#: Va aparte de `NEGADORES` porque es otra cosa: no niega el hecho, lo pone en hipotético. Y se
#: exige el INTERROGATIVO delante («cómo», «how to», «كيف») a propósito: «no pude evitar que se
#: tragara una pila» lleva «evitar» y tiene que seguir saltando, porque ahí la pila ya está dentro.
HIPOTETICA = re.compile(
    r"(?:c[óo]mo|como|how (?:to|do i|can i)|comment|wie (?:kann|man)|как|كيف|कैसे)"
    r"[^.]{0,25}"
    r"(?:preven\w*|evit\w*|prevent\w*|avoid\w*|protect\w*|prot[ée]g\w*|[ée]vit\w*|vorbeug\w*|verhinder\w*|vermeid\w*|sch[üu]tz\w*|предотврат\w*|избеж\w*|уберечь|الوقاية|أتجنب|تجنب|أحمي|رोक\w*|बचा\w*)"
    r"[^.]{0,40}$",
    re.I | re.U,
)
#: Y la palabra sola cuando encabeza: «prevención del golpe de calor», «Vorbeugung», «रोकथाम».
PREVENCION = re.compile(
    r"\b(?:prevenci[óo]n|prevention|pr[ée]vention|vorbeugung|pr[äa]vention|профилактик\w*|"
    r"الوقاية من|रोकथाम)\b[^.]{0,40}$",
    re.I | re.U,
)
#: El interrogativo suelto y el verbo suelto, para las lenguas que los separan (el alemán manda
#: el verbo al final de la frase, y el ruso y el árabe lo ponen antes del complemento).
INTERROGATIVO = re.compile(
    r"(?:\bc[óo]mo\b|\bcomo\b|\bhow\b|\bcomment\b|\bwie\b|\bкак\b|كيف|कैसे"
    r"|\bqu[ée] (?:puedo|debo) hacer\b)",
    re.I | re.U,
)
EVITAR = re.compile(
    r"(?:preven\w*|evit\w*|prevent\w*|avoid\w*|protect\w*|prot[ée]g\w*|[ée]vit\w*|vorbeug\w*|verhinder\w*|vermeid\w*|sch[üu]tz\w*|предотврат\w*|избеж\w*|уберечь|الوقاية|أتجنب|تجنب|أحمي|رोक\w*|बचा\w*)",
    re.I | re.U,
)

#: Cuánto se mira hacia atrás para lo hipotético: más que para la negación, porque la pregunta
#: entera cabe ahí («¿cómo puedo evitar que a mi hijo le dé un …»).
VENTANA_HIPOTETICA = 60


#: Cuánto se mira hacia atrás. Corto a propósito: «no tiene fiebre, pero sí le cuesta respirar»
#: no puede quedar anulado por un «no» que iba con otra cosa.
VENTANA_NEGACION = 26


#: Lo que devuelve a la frase su valor afirmativo: el final de una oración, y las conjunciones
#: adversativas. «sin fiebre pero le cuesta respirar» tiene que seguir saltando.
CORTES = (
    ".",
    ";",
    "!",
    "?",
    "\n",
    " pero ",
    " aunque ",
    " but ",
    " aber ",
    " doch ",
    " jedoch ",
    " mais ",
    " mas ",
    " porém ",
    " но ",
    " однако ",
    " لكن ",
    " लेकिन ",
)


#: Las comas cierran la oración a la que pertenece la negación, igual que un punto. «síntomas que
#: antes no tenía, como problemas para respirar» afirma la segunda mitad (9-sep-2026).
COMAS = (",", "،", "؛", "、")

#: La salvedad que hace segura la regla de arriba: una enumeración negada reparte UNA negación
#: entre varios elementos —«no tiene fiebre, tos ni dificultad para respirar»— y ahí la coma no
#: cierra nada. Se reconoce porque el trozo que sigue a la coma lleva una conjunción.
CONJUNCIONES = re.compile(
    r"\b(?:y|e|o|u|ni|and|or|nor|et|ou|und|oder|noch|nem|"
    r"и|или|ни|أو|و|और|या)\b",
    re.I | re.U,
)


def _hipotetica(texto: str, inicio: int, fin: int = 0) -> bool:
    """¿La frase pregunta cómo EVITAR esto, en vez de contarlo?

    Se mira delante y DETRÁS porque el alemán manda el verbo al final —«wie kann ich einen
    Hitzschlag verhindern?»— y cuando la regla casa «Hitzschlag» el «verhindern» aún no ha
    llegado. Hace falta el interrogativo en los dos casos: sin él, «no pude evitar que se
    tragara una pila» quedaría anulado, y ahí la pila ya está dentro.
    """
    antes = texto[max(0, inicio - VENTANA_HIPOTETICA) : inicio]
    # Una oración nueva cierra la hipótesis, igual que cierra la negación: «cómo evitar que se
    # atragante, SE HA ATRAGANTADO con una uva» son dos frases y la segunda es de verdad.
    for corte in (*CORTES, *COMAS):
        if corte in antes:
            antes = antes.rsplit(corte, 1)[1]
    if PREVENCION.search(antes) or HIPOTETICA.search(antes):
        return True
    if not INTERROGATIVO.search(antes):
        return False
    detras = texto[fin or inicio : (fin or inicio) + VENTANA_HIPOTETICA]
    return bool(EVITAR.search(detras))


def _negada(texto: str, inicio: int, fin: int) -> bool:
    """¿Hay una negación pegada justo antes de esta coincidencia?

    No entiende la frase: solo mira la ventana anterior. Y no cuenta la negación que forma parte
    de la propia coincidencia — «no responde», «no deja de sangrar» y «no puede respirar» son
    patrones que empiezan por una negación y tienen que seguir saltando.
    """
    antes = texto[max(0, inicio - VENTANA_NEGACION) : inicio]
    # Una frase nueva corta el efecto de la negación anterior. Y una conjunción adversativa
    # también: «sin fiebre PERO le cuesta respirar» afirma la segunda mitad, y sin este corte
    # el «sin» de la fiebre anulaba la dificultad respiratoria (probado el 7-sep-2026).
    for corte in CORTES:
        if corte in antes:
            antes = antes.rsplit(corte, 1)[1]
    # La coma cierra la oración salvo que lo que siga sea otro elemento de la misma enumeración
    # negada, y eso lo delata una conjunción: «no tiene fiebre, tos NI dificultad para respirar».
    for coma in COMAS:
        if coma in antes:
            cola = antes.rsplit(coma, 1)[1]
            if not CONJUNCIONES.search(cola):
                antes = cola
    if NEGADORES.search(antes):
        # salvo que la propia coincidencia ya empiece negada
        return not NEGADORES.search(texto[inicio:fin][:14] + " ")
    return False


class Triage:
    def __init__(self, path: Path):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.rules: list[Rule] = []
        for r in raw["rules"]:
            self.rules.append(
                Rule(
                    id=r["id"],
                    level=r["level"],
                    source=r["source"],
                    reason_es=r["reason_es"],
                    reason_en=r["reason_en"],
                    reasons_by_lang={
                        k[7:]: v
                        for k, v in r.items()
                        if k.startswith("reason_") and k not in ("reason_es", "reason_en")
                    },
                    patterns=[re.compile(aplana(p), re.I) for p in r.get("patterns", [])],
                    requires=list(r.get("requires", [])),
                )
            )
        ctx = raw.get("context", {})
        self._fever = [re.compile(aplana(p), re.I) for p in ctx.get("fever", [])]

    def has_fever(self, text: str) -> bool:
        """«Sin fiebre» no es fiebre: la misma regla de negación que para los patrones."""
        return any(self._hits(rx, aplana(text)) for rx in self._fever)

    @staticmethod
    def _hits(rx: re.Pattern[str], text: str) -> bool:
        """Una coincidencia cuenta salvo que venga negada. Se recorren todas: «sin fiebre pero le
        cuesta respirar» tiene que seguir saltando por la segunda mitad."""
        return any(
            not _negada(text, m.start(), m.end()) and not _hipotetica(text, m.start(), m.end())
            for m in rx.finditer(text)
        )

    def _contradicted(self, requires: list[str], age: float | None) -> bool:
        """¿Sabemos ya, con certeza, que esta regla NO es la que toca?

        Solo la edad puede contradecir: si la pregunta dice que el niño tiene ocho meses, la
        regla del lactante no es suya, por muy bien que casen sus palabras. Que no se haya
        detectado fiebre NO contradice nada — un padre escribe «está ardiendo» de mil maneras y
        el detector no las conoce todas; ahí el patrón es precisamente lo que salva la situación.
        """
        return "age_under_3_months" in requires and age is not None and age >= 3

    def assess(self, text: str) -> TriageResult:
        # Los guiones se vuelven espacios ANTES de mirar nada, igual que en `parse_age_months`.
        # Aquello se arregló el 7-sep-2026 «en un sitio, y no en cada expresión, para que lo
        # hereden los ocho idiomas» — y se arregló en la lectura de la edad y no en las reglas,
        # que es la otra mitad de la misma casa. Medido el 8-sep: «my 5 days old refuses to
        # feed» daba urgente y «my 5-day-old refuses to feed» —la forma normal en inglés— daba
        # rutina, con la misma regla y la misma frase. Ningún patrón del fichero necesita un
        # guion literal, así que la conversión no puede quitarle una coincidencia a nadie.
        texto = aplana(_GUIONES.sub(" ", text))
        age = parse_age_months(texto)
        fever = self.has_fever(texto)
        flags = {
            "fever": fever,
            "age_under_3_months": age is not None and age < 3,
        }
        matched: list[Rule] = []
        for r in self.rules:
            # Dos caminos independientes hacia la misma alarma, y hasta el 8-sep-2026 el segundo
            # no existía: en cuanto una regla tenía `requires`, sus patrones no se miraban NUNCA.
            # La regla del lactante con fiebre —la más importante que hay, la 5 de CLAUDE.md—
            # tenía 28 patrones escritos en las ocho lenguas y ninguno podía saltar. El candado
            # estructural que exige patrones en los tres alfabetos los contaba tan contento:
            # comprobaba que estuvieran escritos, no que sirvieran (L47 otra vez).
            #
            # Lo que se perdía era justo lo que el `requires` no sabe leer: «mi lactante tiene
            # fiebre», «Säugling hat Fieber», «у младенца температура», «رضيعي عنده حرارة». Ahí
            # no hay ninguna cifra de edad que interpretar, y la palabra con la que un padre dice
            # «es muy pequeño» sí estaba en los patrones.
            if r.requires and all(flags.get(k, False) for k in r.requires):
                matched.append(r)
                continue
            if not any(self._hits(rx, texto) for rx in r.patterns):
                continue
            if r.requires and self._contradicted(r.requires, age):
                continue
            matched.append(r)
        level = "routine"
        for r in matched:
            if LEVEL_ORDER[r.level] > LEVEL_ORDER[level]:
                level = r.level
        # mental health has its own protocol but never outranks a physical emergency
        matched.sort(key=lambda r: -LEVEL_ORDER[r.level])
        return TriageResult(level=level, matched=matched, age_months=age, has_fever=fever)
