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
    #: Un motivo que no viene de una regla. Lo usa la cinta del brazo (20-sep-2026): el hallazgo
    #: es una MEDIDA, no un síntoma escrito, así que no hay regla que lo haya encontrado y aun
    #: así el aviso tiene que decir por qué. Sin esto, la alternativa era inventar una regla
    #: falsa o un segundo sistema de avisos, y las dos son peores.
    reasons_override: list[str] | None = None

    def reasons(self, lang: str = "en") -> list[str]:
        if self.reasons_override is not None:
            return [r for r in self.reasons_override if r]

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
    "": 1.0,
    "одно": 1.0,
    "полу": 0.5,
    "полутора": 1.5,
    "двух": 2.0,
    "трёх": 3.0,
    "трех": 3.0,
    "четырёх": 4.0,
    "четырех": 4.0,
    "пяти": 5.0,
    "шести": 6.0,
    "семи": 7.0,
    "восьми": 8.0,
    "девяти": 9.0,
    "десяти": 10.0,
    "одиннадцати": 11.0,
    "двенадцати": 12.0,
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
    r"|बिना|नहीं"
    # Suajili (18-sep-2026). La negación no es una palabra: es un prefijo pegado al verbo.
    # «ana homa» es tiene fiebre y «HAna homa» es no tiene fiebre; «HAkuna damu» es no hay
    # sangre; «HAjatapika» es no ha vomitado. Por eso van las formas enteras y no un «no».
    #
    # Y por eso NO se añade el «si» suajili —que es «no es»— a secas: en castellano, francés e
    # italiano «si» es la condición, y meterlo aquí convertiría «si tiene fiebre» en una
    # negación en tres lenguas. Van sólo sus parejas fijas: «si hatari», «si kawaida».
    r"|\bhana\b|\bhakuna\b|\bhaja\w+|\bhawa(?:na|ku)\w*|\bhaina\b|\bhatuna\b"
    r"|\bsi (?:hatari|kawaida|ya kawaida|kitu)\b)"
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
#: Preguntar qué acepta o cómo funciona la herramienta, con las palabras del peligro dentro
#: (23-sep-2026, octava tanda). «¿Puedo mandarte una foto de labios azules?» daba EMERGENCIA;
#: «¿puedes saber si está deshidratado por una foto?», urgente. Ninguna es un niño: son las
#: preguntas que escribe quien está probando el sitio — y quien evalúa una beca.
#:
#: A diferencia de `ASISTENTE`, ésta basta sola: nadie cuenta una urgencia diciendo «¿puedo
#: mandarte una foto de…?». Y si la cuenta en la frase siguiente, esa frase es otra oración y
#: este guardián no la toca.
PREGUNTA_POR_LA_HERRAMIENTA = re.compile(
    r"(?:puedo|podr[íi]a|se puede|es posible)\s+(?:mandar|enviar|subir|adjuntar|pasar)"
    r"|(?:can|could) i (?:send|upload|share|attach)"
    r"|(?:puedes?|podr[íi]as?|sabes)\s+(?:saber|ver|decirme|identificar|valorar|reconocer)"
    r"[^.?!]{0,40}(?:por|con|en|de)\s+(?:una?\s+)?(?:foto|imagen|fotograf[íi]a|v[íi]deo|video)"
    r"|(?:foto|imagen|fotograf[íi]a)[^.?!]{0,25}(?:para que|y me dices|y dime)"
    r"|c[óo]mo distingu\w+|c[óo]mo diferenci\w+"
    r"|si digo[^.?!]{0,70}(?:qu[ée] (?:haces|har[íi]as|pasa)|cu[áa]l)"
    r"|qu[ée] (?:haces|har[íi]as) (?:si|cuando)"
    # las otras tres escrituras, que el candado de `test_regex_scripts` exige y con razón: un
    # padre ruso, árabe o indio también pregunta qué acepta esto antes de contarte nada
    r"|(?:могу|можно) ли[^.?!]{0,30}(?:отправить|прислать|загрузить)"
    r"|(?:можешь|можете)[^.?!]{0,30}(?:по|на) фото"
    r"|чем отличается[^.?!]{0,40}от"
    r"|هل (?:يمكنني|أستطيع)[^.?!]{0,30}(?:إرسال|رفع|تحميل)"
    r"|هل (?:يمكنك|تستطيع)[^.?!]{0,40}(?:من|عبر) (?:صورة|الصورة)"
    r"|ما الفرق بين"
    r"|क्या मैं[^.?!]{0,30}(?:भेज|अपलोड)"
    r"|क्या आप[^.?!]{0,40}(?:तस्वीर|फ़ोटो|फोटो)[^.?!]{0,20}(?:से|देख)"
    r"|में क्या (?:फ़र्क|फर्क|अंतर) है",
    re.I | re.U,
)


#: Preguntarle AL CHAT qué sabe hacer (22-sep-2026). «¿Puede decirme qué hacer ante una
#: convulsión?» es un padre conociendo la herramienta un martes por la tarde, no una convulsión.
#: Nunca basta por sí sola: hace falta además que la frase hable en general (`EN_GENERAL`), para
#: que «¿me ayudas? mi hijo se ha atragantado» siga siendo lo que es.
ASISTENTE = re.compile(
    # 23-sep-2026, octava tanda: «¿puedo mandarte una foto de labios azules?» daba
    # EMERGENCIA. No es un niño morado: es un padre preguntando qué acepta la cámara.
    r"(?:puedo|podr[íi]a|se puede)\s+(?:mandar|enviar|subir|adjuntar|pasar)\w*"
    r"|(?:can|could) i (?:send|upload|share|attach)"
    r"|(?:me )?(?:puedes?|pod[ée]is|podr[íi]as?|podr[íi]a|sabes|sabr[íi]as)\s+"
    r"(?:decirme|explicarme|contarme|indicarme|orientarme|ayudarme|ense[ñn]arme|darme)"
    r"|(?:can|could) you (?:tell|explain|help|show|say|give)"
    r"|(?:peux|pouvez)[- ](?:tu|vous)\s+(?:me )?(?:dire|expliquer|aider|montrer)"
    r"|(?:kannst du|k[öo]nnen sie|kannst)\s+(?:mir )?(?:sagen|erkl[äa]ren|helfen|zeigen)"
    r"|(?:можешь|можете)\s+(?:ли\s+)?(?:мне\s+)?(?:сказать|объяснить|помочь|подсказать)"
    r"|(?:pode|podes|poderia|podia)\s+(?:me\s+)?(?:dizer|explicar|ajudar|mostrar)"
    r"|هل يمكنك|هل تستطيع|ممكن تخبرني"
    r"|क्या आप\s+\S*\s*(?:बता|समझा|मदद|दिखा)",
    re.I | re.U,
)
#: Y la mitad que lo hace seguro: la frase habla de un caso cualquiera, no del que está pasando.
EN_GENERAL = re.compile(
    r"\bqu[ée] hacer\b|\bqu[ée] hago\b|\bante\b|\ben caso de\b|\bdiferencia entre\b|\bsi\b"
    r"|\bwhat to do\b|\bin case of\b|\bdifference between\b|\bif\b"
    r"|\bque faire\b|\ben cas de\b|\bdiff[ée]rence entre\b|\bs['i]\b"
    r"|\bwas man\b|\bwas tun\b|\bbei einem?\b|\bunterschied zwischen\b|\bwenn\b"
    r"|что делать|в случае|разниц\w* между|если"
    r"|ماذا أفعل|في حال|الفرق بين|إذا"
    r"|क्या करें|के मामले में|अंतर|अगर",
    re.I | re.U,
)
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
#: «¿cómo sé si…?», «how do I check…?». Preguntar cómo se RECONOCE un signo es una
#: pregunta de información, y va con el interrogativo igual que `EVITAR`. Se deja
#: fuera a propósito el verbo de actuar —«cómo PARO la hemorragia»— que es una
#: pregunta de instrucciones y a la vez una urgencia de verdad: ese tiene que saltar.
RECONOCER = re.compile(
    r"(?:s[ée] si|saber si|comprobar|reconocer|distinguir"
    r"|check if|check whether|know if|know whether|tell if|recognise|recognize"
    r"|savoir si|v[ée]rifier|reconna[îi]tre"
    r"|erkenn\w*|feststell\w*|merke ich"
    r"|определить|узнать|поня(?:ть|л)"
    r"|أعرف|أتأكد|كيف أعرف"
    r"|कैसे पता|पता करूं|पहचान)",
    re.I | re.U,
)
EVITAR = re.compile(
    r"(?:preven\w*|evit\w*|prevent\w*|avoid\w*|protect\w*|prot[ée]g\w*|[ée]vit\w*|vorbeug\w*|verhinder\w*|vermeid\w*|sch[üu]tz\w*|предотврат\w*|избеж\w*|уберечь|الوقاية|أتجنب|تجنب|أحمي|رोक\w*|बचा\w*)",
    re.I | re.U,
)

#: La pregunta de biblioteca: qué ES, cuáles SON, cómo se sabe si. No es un niño enfermo, es
#: alguien informándose — y desde el 17-sep-2026, con las etiquetas dentro de las reglas, una
#: pregunta así casaba el nombre de la señal y saltaba la alarma.
INFORMATIVA = re.compile(
    r"(?:qu[ée] (?:es|son|significa)|cu[áa]les son|c[óo]mo se (?:sabe|reconoce|detecta)"
    r"|en qu[ée] consiste"
    # 23-sep-2026: «¿cómo distingues "hace ruido" de "le cuesta respirar"?» y «si digo "se
    # ahoga" pero en realidad solo tose, ¿qué haces?». Las dos preguntan por el sistema.
    r"|c[óo]mo distingu\w+|c[óo]mo diferenci\w+|qu[ée] diferencia hay"
    r"|si digo[^.?!]{0,60}(qu[ée] (haces|har[íi]as|pasa)|cu[áa]l)"
    r"|qu[ée] (haces|har[íi]as) si"
    r"|what (?:is|are|does)|which are|how (?:do (?:i|you) (?:know|tell)|can i tell)|signs? of what"
    r"|qu'est.ce que|quels sont|quelles sont|comment (?:savoir|reconna[îi]tre)"
    r"|was (?:ist|sind|bedeutet)|welche (?:sind|zeichen)|woran (?:erkenne|merke)"
    r"|что такое|каковы|какие (?:признаки|симптомы)|как (?:понять|распознать)"
    r"|ما (?:هي|هو|معنى)|كيف (?:أعرف|نعرف)"
    r"|क्या (?:है|हैं|होता)|कौन.?से|कैसे (?:पता|जानें)"
    # 18-sep-2026: lo que a uno LE HAN DICHO no es lo que le está pasando a su hijo. «Me han
    # dicho que si pellizco la piel y tarda en volver es deshidratación» es una explicación que
    # alguien le dio, y recibía una emergencia. Va aquí y no en el condicional porque lo que lo
    # delata es quién habla, no el tiempo del verbo.
    r"|me han dicho|me dijeron|me dijo|dicen que|he le[íi]do|leí que"
    r"|(?:have been|was|were) told|they told me|i read that|i've read"
    r"|on m'a dit|il para[îi]t que|j'ai lu que"
    r"|man hat mir gesagt|ich habe gelesen"
    r"|мне сказали|я (?:читал|читала)"
    r"|قالوا لي|قال لي|قرأت أن"
    r"|मुझे बताया|मैंने पढ़ा)"
    r"[^.?!]{0,60}$",
    re.I | re.U,
)

#: «¿El sarampión puede dar úlceras en la boca?» (18-sep-2026).
#:
#: Preguntar si una enfermedad PUEDE CAUSAR algo es preguntar por la enfermedad, no contar lo que
#: le pasa a un hijo. No lo cubría ninguno de los guardianes: el informativo mira sólo delante de
#: la señal y aquí el «puede dar» va detrás, y el interrogativo pide un «cómo» que en esta frase
#: no hay — sólo el signo de apertura.
#:
#: Se piden las dos cosas a la vez, el verbo de causa y la pregunta, y se mira la oración entera.
#: Con una sola de las dos sería demasiado ancho: «le puede dar una convulsión» sin interrogación
#: es un padre asustado contando lo que teme, y ese no se toca.
CAUSAL = re.compile(
    r"(?:puede[n]? (?:dar|causar|provocar|producir)"
    r"|can (?:it |this |measles |malaria )?(?:cause|give|lead to)|could .{0,12}cause"
    r"|peut.{0,12}(?:donner|provoquer|entra[îi]ner)"
    r"|kann .{0,40}(?:verursachen|ausl[öo]sen)"
    r"|может ли .{0,14}(?:вызвать|дать)|вызывает ли"
    r"|هل (?:يسبب|تسبب|يؤدي)"
    r"|क्या .{0,40}(?:हो सकता|कर सकता|करता है)"
    r"|inaweza ku(?:sababisha|leta))",
    re.I | re.U,
)

#: El marco que va al FINAL de la frase: suajili e hindi (18-sep-2026).
#:
#: Todos los guardianes de arriba miran lo que va DELANTE de la señal, porque en las ocho lenguas
#: que había el «cómo evitar», el «cuáles son» y el «qué hago si» van delante. El suajili los pone
#: detrás: «degedege la homa NI NINI» es «¿qué es una convulsión febril?» y «dalili za homa ya uti
#: wa mgongo NI ZIPI» es «¿cuáles son los signos de la meningitis?». Las dos daban emergencia.
#:
#: Y va lo de prevenir —«kuzuia»— con una excepción escrita: «kuzuia damu» es «parar la
#: hemorragia», que es una pregunta de instrucciones y a la vez una urgencia de verdad. Es la
#: misma línea que se trazó con «cómo paro la hemorragia» cuando se escribió RECONOCER.
MARCO_AL_FINAL = re.compile(
    r"(?:\bni nini\b|\bni zipi\b|\bni ipi\b|\bni gani\b"
    r"|nitajua\w*|nawezaje|ninawezaje|jinsi ya"
    r"|nimeambiwa|nimesoma|nimeambiwa kwamba"
    r"|kuzuia(?! damu| kutokwa)"
    # Hindi: «गंभीर निर्जलीकरण के लक्षण क्या हैं» es «¿cuáles son los signos de la
    # deshidratación grave?», y el «क्या हैं» va detrás, igual que en suajili.
    r"|(?:लक्षण|संकेत|निशानी)[^।?]{0,16}क्या (?:ह|होत)"
    r"|कैसे (?:रोक|बचा|पहचान)"
    r"|मुझे बताया गया|मैंने पढ़ा)",
    re.I | re.U,
)

#: Lo que pasó hace AÑOS no es lo que está pasando (17-sep-2026).
#:
#: «Tuvo una convulsión hace dos años y nunca se repitió» abría el aviso rojo de llamar al 112.
#: Es un antecedente, y contarlo es de las cosas más normales que hace un padre cuando pregunta
#: otra cosa.
#:
#: El corte está en semanas: lo de hace horas o días SIGUE saltando, porque «tuvo una convulsión
#: esta mañana» es de hoy y hay que verlo. Meses y años, no.
PASADO_REMOTO = re.compile(
    r"(?:hace|desde hace)[^.]{0,12}(?:\d+|un|una|dos|tres|cuatro|cinco|seis|varios|varias|muchos)"
    # 22-sep-2026: «tuvo fiebre hace UNA SEMANA y ahora tiene granitos» —el exantema súbito,
    # de libro— daba aviso de lactante con fiebre: el plural estaba escrito y el singular no.
    r"[^.]{0,6}(?:a[ñn]os?|mes(?:es)?|semanas?)"
    r"|(?:el|los) a[ñn]os? pasad|la semana pasada|el mes pasado"
    r"|\bde beb[ée]\b|cuando era (?:beb[ée]|peque|m[áa]s peque)"
    r"|(?:\d+|a|one|two|three|four|five|six|several|many)[^.]{0,6}"
    r"(?:years?|months?|weeks?) ago|last (?:year|month|week)"
    r"|as a baby|when he was (?:a baby|little)|when she was (?:a baby|little)"
    r"|il y a[^.]{0,12}\b(?:ans?|mois|semaines)\b|l'an dernier|le mois dernier"
    r"|\bvor\b[^.]{0,12}\b(?:jahren?|monaten|wochen)\b|letztes jahr|letzten monat"
    r"|(?:\d+|дв[ае]|три|несколько)[^.]{0,8}(?:лет|года|месяц\w*|недел\w*) назад"
    r"|в прошлом году|на прошлой неделе"
    r"|(?:قبل|منذ)[^.]{0,12}(?:سنة|سنوات|سنتين|شهر|أشهر|شهور)"
    r"|\bh[áa]\b[^.]{0,12}\b(?:anos?|meses|semanas)\b|no ano passado"
    r"|(?:साल|महीने|हफ़्ते|बरस)[^.]{0,8}पहले|पिछले साल"
    # Suajili, con una corrección que costó dos emergencias silenciadas. La primera versión metió
    # aquí el prefijo del pasado —«ALIkuwa», «ALIpata», «ALIanguka»— por analogía con el
    # castellano, y está mal: **«ali-» no marca distancia**. Es el pasado de cualquier cosa que ya
    # ocurrió, incluido lo de hace cinco minutos. Con él dentro, «ALIanguka akagonga kichwa na
    # akapoteza fahamu» —se cayó, se golpeó la cabeza y perdió el conocimiento— dejó de dar
    # alarma, y «ALIkuwa kwenye moto na anakohoa sana» también. Cuando falla un guardián, el
    # fallo es un silencio (L176).
    #
    # Lo que sí marca distancia en suajili es la expresión de tiempo, y va detrás del verbo:
    # «mwaka jana» (el año pasado), «miaka miwili ILIYOPITA» (hace dos años). Eso es lo que queda.
    r"|mwaka jana|mwezi uliopita|wiki iliyopita"
    r"|(?:miaka|miezi|wiki)[^.]{0,14}(?:iliyopita|ilivyopita)",
    re.I | re.U,
)

#: «¿Qué hago SI le da una convulsión?» es la pregunta que se hace cuando NO está pasando.
#:
#: Va aparte de `HIPOTETICA` —que es la de prevenir— porque ésta no habla de evitar nada: habla
#: de estar preparado. Y es tan común que no filtrarla convierte el aviso rojo en ruido: de las
#: nueve lenguas probadas, las nueve daban emergencia.
CONDICIONAL = re.compile(
    # 22-sep-2026: «¿qué pasa si…?» pregunta por un supuesto, en las ocho lenguas
    r"(?:qu[ée] pasa|qu[ée] ocurre|what happens|que se passe|was passiert|что будет|что происходит"
    r"|ماذا يحدث|क्या होता है)[^.?!]{0,40}\b(?:si|if|s['i]|wenn|если|إذا|अगर)\b"
    r"|(?:q(?:u[ée])? (?:hago|hacer|debo hacer|tengo que hacer)|c[óo]mo act[úu]o)[^.?!]{0,40}"
    r"\b(?:si|cuando)\b"
    r"|\bsi\b[^.?!]{0,60}(?:qu[ée] (?:hago|hacer|debo))"
    r"|what (?:should|do|would) i do[^.?!]{0,40}\bif\b"
    r"|\bif\b[^.?!]{0,60}what (?:should|do) i do"
    r"|que faire[^.?!]{0,40}\bs[i']|\bsi\b[^.?!]{0,60}que faire"
    r"|was (?:mache|tue|soll) ich[^.?!]{0,40}\bwenn\b"
    r"|\bwenn\b[^.?!]{0,60}was (?:mache|soll) ich"
    r"|что делать[^.?!]{0,40}если|если[^.?!]{0,60}что делать"
    r"|ماذا أفعل[^.?!]{0,40}(?:إذا|لو)|(?:إذا|لو)[^.?!]{0,60}ماذا أفعل"
    r"|(?:अगर|यदि)[^.?!]{0,60}(?:क्या करूँ|क्या करूं|क्या करना)"
    r"|क्या (?:करूँ|करूं)[^.?!]{0,40}(?:अगर|यदि)"
    # Suajili: el «si» también es un prefijo. «AKIpata degedege» es «si le dan convulsiones» y
    # «NIKImwona amepauka» es «si lo veo pálido». No hay ninguna palabra suelta que buscar, así
    # que se busca el prefijo con su verbo, en los dos órdenes que usa la pregunta.
    r"|nifanye nini[^.?!]{0,45}\b(?:aki|akia|niki|kama)\w*"
    r"|\b(?:aki|niki)\w+[^.?!]{0,45}nifanye nini"
    r"|\bkama\b[^.?!]{0,45}\bata\w+[^.?!]{0,45}(?:nifanye|nimpeleke|wapi)"
    r"|(?:nifanye|nimpeleke)[^.?!]{0,45}\bkama\b",
    re.I | re.U,
)

#: Cuánto se mira hacia atrás para lo hipotético: más que para la negación, porque la pregunta
#: entera cabe ahí («¿cómo puedo evitar que a mi hijo le dé un …»).
VENTANA_HIPOTETICA = 60


#: Los guardianes miran el MISMO texto aplanado que las reglas, así que se aplanan también.
#: Sin esto, el condicional árabe —escrito con hamza, «إذا»— no encontraba nunca el «اذا» que
#: le llegaba, y «ماذا أفعل إذا أصيب بتشنج؟» seguía dando emergencia (17-sep-2026).
for _nombre in (
    "HIPOTETICA",
    "PREVENCION",
    "INFORMATIVA",
    "CONDICIONAL",
    "PASADO_REMOTO",
    "EVITAR",
    "INTERROGATIVO",
    # 18-sep-2026: los tres de hoy. Se me olvidó aplanarlos y el árabe de «في الدقيقة» no
    # casaba, porque el texto del padre llega ya con ة→ه y el patrón seguía con la forma culta.
    "RECONOCER",
    "CAUSAL",
    "MARCO_AL_FINAL",
):
    _rx = globals()[_nombre]
    globals()[_nombre] = re.compile(aplana(_rx.pattern), _rx.flags)
del _nombre, _rx


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


def _frase_de(texto: str, inicio: int) -> str:
    """La oración donde vive la coincidencia, cortada en el punto y en la coma."""
    ini = 0
    for corte in (".", "!", "?", "\n", ";"):
        pos = texto.rfind(corte, 0, inicio)
        ini = max(ini, pos + 1)
    fin = len(texto)
    for corte in (".", "!", "?", "\n", ";"):
        pos = texto.find(corte, inicio)
        if pos != -1:
            fin = min(fin, pos)
    return texto[ini:fin]


def _hipotetica(texto: str, inicio: int, fin: int = 0) -> bool:
    """¿La frase habla de algo que NO está pasando?

    Cuatro maneras de no estar pasando, y las cuatro son preguntas que un padre hace de verdad:

        prevención   «¿cómo prevenir un golpe de calor?»
        información  «¿cuáles son los signos de deshidratación?»
        condicional  «¿qué hago si le da una convulsión?»
        pasado       «tuvo una convulsión hace dos años»

    Las dos primeras se miran sólo DELANTE de la señal y con ventana corta, para que «no pude
    evitar que se tragara una pila» —donde la pila ya está dentro— siga saltando. Las dos últimas
    se miran en la oración entera, porque el condicional puede ir detrás («si le da una
    convulsión, ¿qué hago?») y el tiempo también («tuvo una convulsión hace dos años»).

    Y el alemán necesita mirar hacia delante aunque no haya nada delante: manda el verbo al final
    —«wie kann ich einen Hitzschlag verhindern?»— y cuando la regla casa «Hitzschlag», el
    «verhindern» aún no ha llegado.
    """
    antes = texto[max(0, inicio - VENTANA_HIPOTETICA) : inicio]
    # Una oración nueva cierra la hipótesis, igual que cierra la negación: «cómo evitar que se
    # atragante, SE HA ATRAGANTADO con una uva» son dos frases y la segunda es de verdad.
    for corte in (*CORTES, *COMAS):
        if corte in antes:
            antes = antes.rsplit(corte, 1)[1]
    if PREVENCION.search(antes) or HIPOTETICA.search(antes) or INFORMATIVA.search(antes):
        return True
    if INTERROGATIVO.search(antes):
        detras = texto[fin or inicio : (fin or inicio) + VENTANA_HIPOTETICA]
        if EVITAR.search(detras) or RECONOCER.search(antes) or RECONOCER.search(detras):
            return True
    frase = _frase_de(texto, inicio)
    if CONDICIONAL.search(frase) or PASADO_REMOTO.search(frase):
        return True
    # preguntarle al chat qué sabe hacer, hablando de un caso cualquiera: las dos cosas
    if ASISTENTE.search(frase) and EN_GENERAL.search(frase):
        return True
    # y preguntar qué acepta la herramienta, que basta sola (23-sep-2026)
    if PREGUNTA_POR_LA_HERRAMIENTA.search(frase):
        return True
    # «¿El sarampión puede dar úlceras en la boca?»: el verbo de causa Y la pregunta, las dos
    # cosas, y en la oración entera porque el «puede dar» puede ir delante o detrás de la señal.
    # el suajili no escribe el signo: marca la pregunta con «je» delante, igual que el
    # castellano la marca con «¿». Sin esto, «je surua inaweza kusababisha vidonda?» daba alarma.
    # 18-sep-2026, midiendo las reglas africanas en las cuatro lenguas que faltaban: un padre
    # que escribe una pregunta **no siempre pone el signo**, y en cuatro de las nueve lenguas la
    # pregunta no se marca con un signo sino con una pieza de la propia frase:
    #
    #     هل تسبب الحصبة تقرحات       la partícula «هل» delante
    #     क्या खसरा छाले कर सकता है     la partícula «क्या» delante
    #     может ли корь вызвать...    la partícula «ли»
    #     kann Masern Geschwüre...    el verbo en primer lugar, que en alemán ES la pregunta
    #
    # Las cuatro daban alarma de sarampión complicado por no llevar «?». Se añaden las piezas,
    # que es más seguro que quitar el requisito entero: sin él, «el golpe le puede dar una
    # hemorragia y está sangrando mucho» se callaría por el «puede dar» de la primera mitad.
    es_pregunta = (
        "?" in frase
        or "؟" in frase
        or "¿" in texto[max(0, inicio - 60) : inicio]
        or re.match(r"\s*je\b", frase, re.I) is not None
        or re.search(r"هل|क्या|\bли\b", frase) is not None
        or re.match(r"\s*(?:kann|ist|hat|kommt|muss|darf|soll|wird)\b", frase, re.I) is not None
    )
    if es_pregunta and CAUSAL.search(frase):
        return True
    # El suajili y el hindi ponen el interrogativo AL FINAL: «degedege la homa NI NINI» es
    # «¿qué es una
    # convulsión febril?» y «dalili za homa ya uti wa mgongo NI ZIPI» es «¿cuáles son los
    # signos?». Ninguna de las otras ocho lenguas lo hace, y todos los guardianes de arriba
    # miran lo que va DELANTE de la señal, así que aquí no ven nada: las dos frases daban
    # emergencia. Por eso esta mira la oración entera.
    return bool(MARCO_AL_FINAL.search(frase))


#: ¿La negación que se encontró es un «ni» suelto? (19-sep-2026, ver `_negada`)
_NI_SUELTO = re.compile(r"ni\b", re.I)
#: Las negaciones que un «ni» castellano continúa. No entra el propio «ni»: dos «ni» seguidos
#: —«ni come ni bebe»— son la misma construcción y no confirman nada que el primero no dijera.
_NEGACION_PREVIA = re.compile(
    r"(?:\bno\b|\bsin\b|\bnada de\b|\btampoco\b|\bnunca\b|\bjam[aá]s\b)", re.I | re.U
)


def _otra_negacion(texto: str, inicio: int) -> bool:
    """¿Hay una negación de verdad antes del «ni», dentro de la misma frase?"""
    frase = _frase_de(texto, inicio)
    corte = texto.rfind(frase, 0, inicio + 1)
    delante = texto[corte:inicio] if corte >= 0 else frase
    return bool(_NEGACION_PREVIA.search(delante))


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
    encontrado = NEGADORES.search(antes)
    if encontrado and _NI_SUELTO.match(encontrado.group(0)) and not _otra_negacion(texto, inicio):
        # 19-sep-2026: «ni» es una negación en castellano y es el verbo SER en suajili.
        # «midomo yake NI ya bluu na hajibu» —sus labios SON azules y no responde— perdía el
        # «no responde», y «hali yake NI mbaya na ana degedege» perdía la convulsión. Del lado
        # peor: no produce una alarma de más, produce un silencio.
        #
        # No se quita el «ni» castellano, que hace falta. Se le pide lo que el castellano
        # cumple siempre y el suajili no: el «ni» CONTINÚA una negación, así que tiene que
        # haber otra negación antes en la misma frase.
        encontrado = None
    if encontrado:
        # salvo que la propia coincidencia ya empiece negada
        return not NEGADORES.search(texto[inicio:fin][:14] + " ")
    return False


#: Las palabras con las que un padre dice «respira», en las ocho lenguas del producto.
_RESPIRA = re.compile(
    r"(respira|respirac|respirando|respire|respirat|breath|breathing|atem|atmet|atmung"
    r"|дыш|дыхан|вдох|تنفس|نفس|يتنفس|साँस|सांस"
    r"|pumzi|kupumua|anapumua|pumua)",
    re.I,
)
#: «por minuto», que es lo que convierte un número suelto en una frecuencia. Con el conector,
#: porque un padre no siempre dice «por»: cuenta «55 EN UN minuto», «58 IN A minute», «60 EM UM
#: minuto». Sin esa forma, la manera más natural de contarlo se quedaba fuera.
_POR_MINUTO = re.compile(
    r"(por|per|par|pro|in a|in einer|en un[ae]?|em um|num|kwa|a|в|في|प्रति|एक)\s*"
    r"(minuto|minute|min\.?|minuten|минуту|мин|دقيقة|الدقيقة|मिनट|dakika)",
    re.I,
)
_CIFRA_RESPIRA = re.compile(r"(?<![\d,.])(\d{2,3})(?![\d,.])")
# Mismo aplanado que los guardianes, y por lo mismo: «في الدقيقة» le llega al patrón como
# «في الدقيقه», con la ta marbuta convertida, y la forma culta no casaba.
_RESPIRA = re.compile(aplana(_RESPIRA.pattern), _RESPIRA.flags)
_POR_MINUTO = re.compile(aplana(_POR_MINUTO.pattern), _POR_MINUTO.flags)

#: Los umbrales del IMCI, de menor a mayor edad: (hasta cuántos meses, respiraciones por minuto).
#: Se leen en orden y se coge el primero que cubre la edad.
_UMBRALES_IMCI = ((2.0, 60), (12.0, 50), (60.0, 40))
#: Sin edad no se puede clasificar, así que se pide el umbral más alto de la tabla.
_UMBRAL_SIN_EDAD = 60


#: «normal», en las ocho lenguas. Un padre que cuenta una urgencia no escribe esta palabra;
#: quien pregunta cuánto es normal, sí.
_NORMALIDAD = re.compile(
    r"(normal\w*|normaux|üblich\w*|нормальн\w*|норм[ае]|طبيعي|طبيعية|सामान्य|habitual|usual)",
    re.I,
)


def _pregunta_por_lo_normal(texto: str, fin: int) -> bool:
    """¿Es «¿son normales 40 por minuto?» en vez de «respira 40 por minuto»?

    Los guardianes de arriba no cubren esta forma: no hay negación, no hay prevención y el
    «how» del interrogativo tampoco aparece. Pero es una pregunta de información corriente y
    dispararía una alarma en un niño que está perfectamente.

    Tres condiciones, y las tres hacen falta:

    · la palabra «normal» cerca del número, ANTES o DESPUÉS. En inglés va detrás —«is 40 breaths
      per minute normal?»— y en castellano delante —«¿son normales 40 respiraciones?»—, que es
      otra vez la lección de que la misma idea tiene varios órdenes (L101);
    · un signo de interrogación cerca. El de apertura va delante y el de cierre detrás, así que
      se miran los dos lados. No vale `_frase_de`, que corta la oración justo en el «?»;
    · que ese «normal» no venga negado: «60 por minuto, eso no es normal, ¿verdad?» es un padre
      asustado contando lo que ve, y ese tiene que saltar.
    """
    ini = max(0, fin - 40)
    cerca = texto[ini : fin + 40]
    m = _NORMALIDAD.search(cerca)
    if not m:
        return False
    if "?" not in texto[fin : fin + 60] and "¿" not in texto[max(0, fin - 60) : fin]:
        return False
    antes = cerca[max(0, m.start() - 14) : m.start()]
    return not NEGADORES.search(antes)


def respiracion_rapida(texto: str, edad_meses: float | None) -> bool:
    """¿El padre ha contado una frecuencia respiratoria alta para la edad del niño?

    `texto` ya viene aplanado por `aplana`, igual que para los patrones.
    """
    for m in _RESPIRA.finditer(texto):
        ventana_ini = max(0, m.start() - 40)
        ventana = texto[ventana_ini : m.end() + 60]
        if not _POR_MINUTO.search(ventana):
            continue
        for c in _CIFRA_RESPIRA.finditer(ventana):
            valor = int(c.group(1))
            if not (20 <= valor <= 120):
                continue  # ni un pulso ni un peso ni unos mililitros
            inicio = ventana_ini + c.start()
            fin = ventana_ini + c.end()
            # los mismos guardianes que protegen a los patrones: una pregunta por lo que es
            # normal, o una frecuencia de ayer, no son un niño respirando deprisa ahora
            if _negada(texto, inicio, fin) or _hipotetica(texto, inicio, fin):
                continue
            if _pregunta_por_lo_normal(texto, fin):
                continue
            umbral = _UMBRAL_SIN_EDAD
            if edad_meses is not None:
                for hasta, corte in _UMBRALES_IMCI:
                    if edad_meses < hasta:
                        umbral = corte
                        break
                else:
                    umbral = _UMBRALES_IMCI[-1][1]
            if valor >= umbral:
                return True
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
            # 18-sep-2026, fase 2 de África: contar las respiraciones durante un minuto es LA
            # herramienta del IMCI para reconocer una neumonía donde no hay radiografía. No es
            # un patrón porque lo que decide no es el número sino el número contra la edad.
            "breathing_too_fast": respiracion_rapida(texto, age),
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
