"""The answer pipeline (PRD §5.1): triage → retrieval → drafting → verification → assembly."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pedibot.bot.dose import DRUGS, calculate, format_result
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.growth import is_growth_question
from pedibot.bot.guides import GuideIndex, GuideLink
from pedibot.bot.llm import LLMProvider, LLMResult
from pedibot.bot.retrieval import Retriever, detect_lang
from pedibot.bot.strings import LANGUAGE_NAME
from pedibot.bot.triage import LEVEL_ORDER, Triage, TriageResult
from pedibot.bot.vaccines import (
    Vaccines,
    country_in_question,
    format_answer,
    is_vaccine_question,
)
from pedibot.index.store import Hit

PROMPTS_DIR = Path(__file__).parent / "prompts"
MAX_TURNS = 6  # PRD §5.4: short window
CHILD_MODE = (
    "MODE: EXPLAIN TO THE CHILD. The parent wants a version to read aloud to a child aged 5-10. "
    "Keep every rule (sources only, citations [n], no doses). Write 3-5 very short, warm sentences "
    "in second person to the child ('your body…'), no scary words, one simple comparison, and end "
    "with one thing the child can do (drink, rest, tell mum or dad if…). Keep the citations.\n"
)
_CIT = re.compile(r"\[(\d{1,2})\]")
#: Los kilos, en las ocho lenguas. Las unidades latinas llevan `\b` detrás; las de las otras
#: escrituras NO, por lo mismo que en el detector de vacunas: `\b` se define sobre `\w` y en
#: árabe y devanagari los sufijos son caracteres de palabra, así que la frontera no existe.
#: Hasta el 7-sep-2026 solo conocía «kg», y con eso el ruso, el árabe y el hindi no llegaban
#: nunca a la calculadora — que es la única herramienta que da un mililitro exacto sin modelo.
_WEIGHT = re.compile(
    r"(\d{1,3}(?:[.,]\d)?)\s*"
    r"(?:(?:kg|kilos?|kilogramos?|kgs|quilos?)\b"
    r"|кг|килограмм\w*|кило\w*"
    r"|كيلوغرام|كيلوجرام|كيلو|كجم|كغ"
    r"|किलोग्राम|किलो|किग्रा)",
    re.I,
)

#: Las cifras arábigo-índicas y devanagari, que es lo que sale de un teclado árabe o hindi.
_DIGITOS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹०१२३४५६७८९", "01234567890123456789" + "0123456789")
_DRUG = re.compile(
    r"\b(paracetamol|acetaminophen|tylenol|apiretal|ibuprofen[oe]?|dalsy|advil|nurofen)\w*", re.I
)
_DRUG_ALIAS = {
    "tylenol": "paracetamol",
    "apiretal": "paracetamol",
    "acetaminophen": "paracetamol",
    "dalsy": "ibuprofen",
    "advil": "ibuprofen",
    "nurofen": "ibuprofen",
    "ibuprofene": "ibuprofen",
    "ibuprofeno": "ibuprofen",
}
#: Las unidades, en las tres escrituras además de la latina. Este patrón es la puerta del único
#: guardia que hay contra una dosis inventada, y estaba escrito solo en latino: «дайте 250 мг» o
#: «250 मिग्रा» no lo cruzaban, así que el guardia ni miraba (7-sep-2026). Las latinas llevan `\b`
#: detrás; las otras no, por lo mismo de siempre — en árabe y devanagari los sufijos son
#: caracteres de palabra y la frontera no existe.
#: Detrás de la unidad NO puede venir una letra. Se escribió sin esa condición porque en
#: árabe y devanagari los sufijos son caracteres de palabra y `\b` no sirve; el efecto fue
#: que la unidad casaba DENTRO de otras palabras y el guardia se disparaba solo. Auditando
#: las 483 guías publicadas (8-sep-2026) salieron las dos que lo demuestran:
#:
#:     «2.6 مليون وفاة»        → «مل» dentro de «مليون» (millones)
#:     «2–3 из 100 младенцев»  → «мл» dentro de «младенцев» (lactantes)
#:
#: Un falso positivo aquí no da una dosis mala: **tira la respuesta**, porque `verify` la
#: manda a regenerar y de ahí al «no tengo información fiable». O sea que el guardia estaba
#: costando respuestas en ruso y en árabe cada vez que un texto citaba una cifra grande.
#:
#: Se escribe como «no seguido de letra» y no como `\b`, que es lo que funciona en las
#: cuatro escrituras a la vez: una dosis de verdad va seguida de espacio, coma o punto.
_NO_LETRA = r"(?![\w\u0600-\u06ff\u0900-\u097f])"
_DOSE_NUM = re.compile(
    r"\b\d+([.,]\d+)?\s*"
    r"(?:(mg|ml)\b"
    rf"|(мг|мл){_NO_LETRA}"
    rf"|(ملغ|مغ|ملغم|مل){_NO_LETRA}"
    rf"|(मिग्रा|मिलीग्राम|मिली|मिलीलीटर){_NO_LETRA})",
    re.I,
)


# A millilitre figure is a medication dose unless the words around it clearly say fluid: the
# rehydration volumes in the SEUP vómitos/gastroenteritis leaflets are not doses. Fails closed —
# an unexplained "5 ml" still counts as a dose. Milligrams are always a dose.
_FLUID_WORDS = re.compile(
    r"(suero|rehidrataci|sales de rehidrat|rehydration|\bors\b|agua\b|water\b|leche|milk|"
    r"pecho|breast|biber[oó]n|bottle|toma[s]?\b|feed|l[ií]quido|fluid|zumo|juice"
    # los líquidos también en las otras tres: sin esto, los volúmenes de suero oral de las hojas
    # del SEUP se tomarían por dosis y la respuesta se rechazaría sin motivo
    r"|вод|молок|регидрат|жидкост|груд|бутылочк"
    r"|ماء|حليب|محلول معالجة الجفاف|سوائل|رضاعة"
    r"|पानी|दूध|ओआरएस|तरल|स्तनपान)",
    re.I,
)
_MEDICINE_WORDS = re.compile(
    r"(paracetamol|acetaminophen|ibuprofeno|ibuprofen|antibi[oó]tic|antibiotic|amoxicilin|"
    r"amoxicillin|jarabe|syrup|antihistam[ií]nic|antihistamine|medicamento|medicine|dosis|dose|"
    r"calpol|dalsy|apiretal|junifen|tylenol|nurofen"
    # y en las otras tres escrituras: el genérico, «dosis», «jarabe» y «medicamento»
    r"|парацетамол|ибупрофен|доз|сироп|лекарств|антибиотик"
    r"|باراسيتامول|إيبوبروفين|جرعة|شراب|دواء|مضاد حيوي"
    r"|पैरासिटामोल|आइबुप्रोफेन|खुराक|सिरप|दवा|एंटीबायोटिक)",
    re.I,
)
_DOSE_WINDOW = 90


def looks_like_medication_dose(text: str) -> bool:
    """True if the text states a medication dose (mg always; ml unless clearly a fluid)."""
    for m in _DOSE_NUM.finditer(text):
        unidad = (m.group(2) or m.group(3) or m.group(4) or m.group(5) or "").lower()
        # Los miligramos son SIEMPRE una dosis, se escriban en el alfabeto que se escriban.
        if unidad in {"mg", "мг", "ملغ", "مغ", "ملغم", "मिग्रा", "मिलीग्राम"}:
            return True
        around = text[max(0, m.start() - _DOSE_WINDOW) : m.end() + _DOSE_WINDOW]
        if _MEDICINE_WORDS.search(around):
            return True
        if not _FLUID_WORDS.search(around):
            return True
    return False


# Every language the engine will answer in. Adding one here is not enough on its own: it needs
# its triage patterns in red_flags.yaml and its texts below, or the safety layer goes silent.
SUPPORTED_LANGS = ("es", "en", "fr", "de", "ru", "ar", "pt", "hi")

DISCLAIMER = {
    "en": "PediBot gives information from official paediatric guidelines. It is not medical advice and does not replace your paediatrician.",
    "es": "PediBot informa a partir de guías pediátricas oficiales. No es consejo médico y no sustituye a tu pediatra.",
    "fr": "PediBot informe à partir de recommandations pédiatriques officielles. Ce n'est pas un avis médical et cela ne remplace pas votre pédiatre.",
    "de": "PediBot gibt Informationen aus offiziellen kinderärztlichen Leitlinien wieder. Das ist keine medizinische Beratung und ersetzt nicht Ihre Kinderärztin oder Ihren Kinderarzt.",
    "ru": "PediBot даёт информацию из опубликованных педиатрических рекомендаций. Это не медицинская консультация и не заменяет вашего педиатра.",
    "ar": "يقدم PediBot معلومات مأخوذة من إرشادات طب الأطفال المنشورة. هذه ليست استشارة طبية ولا تغني عن طبيب طفلك.",
    "hi": "PediBot प्रकाशित बाल रोग दिशानिर्देशों से जानकारी देता है। यह चिकित्सकीय सलाह नहीं है और आपके डॉक्टर की जगह नहीं लेता।",
    "pt": "O PediBot informa a partir de diretrizes pediátricas oficiais. Não é aconselhamento médico e não substitui o seu pediatra.",
}
NO_SOURCE = {
    "en": "I don't have reliable information on this in my sources, so I'd rather not guess. Please contact your paediatrician or a nurse line. If your child seems seriously unwell, go to the emergency department.",
    "es": "No tengo información fiable sobre esto en mis fuentes y prefiero no adivinar. Consulta con tu pediatra. Si tu hijo o hija parece estar grave, acude a urgencias.",
    "fr": "Je n'ai pas d'information fiable à ce sujet dans mes sources et je préfère ne pas deviner. Parlez-en à votre pédiatre. Si votre enfant semble aller très mal, allez aux urgences.",
    "de": "Dazu habe ich in meinen Quellen keine verlässliche Information, und raten möchte ich nicht. Sprechen Sie bitte mit Ihrer Kinderärztin oder Ihrem Kinderarzt. Wenn Ihr Kind schwer krank wirkt, fahren Sie in die Notaufnahme.",
    "ru": "В моих источниках нет надёжной информации об этом, а гадать я не хочу. Обратитесь, пожалуйста, к своему педиатру. Если ребёнку явно плохо, поезжайте в приёмное отделение.",
    "ar": "لا توجد في مصادري معلومات موثوقة عن هذا، ولا أريد التخمين. من فضلك تحدث إلى طبيب طفلك. وإذا بدا على طفلك تعب شديد، فتوجّه إلى قسم الطوارئ.",
    "hi": "मेरे स्रोतों में इसके बारे में भरोसेमंद जानकारी नहीं है, और मैं अंदाज़ा नहीं लगाना चाहता। कृपया अपने डॉक्टर से बात करें। अगर बच्चा बहुत बीमार लग रहा है, तो इमरजेंसी में जाएँ।",
    "pt": "Não tenho informação confiável sobre isso nas minhas fontes e prefiro não adivinhar. Procure o seu pediatra. Se a criança parecer estar mal, vá ao pronto-socorro.",
}
#: Lo que se dice cuando se ha agotado el tope de gasto del día y la respuesta sale sin modelo.
#: Estaba en dos idiomas —inglés, y español para los otros seis—, así que un padre alemán recibía
#: una frase en español (7-sep-2026).
BUDGET_SPENT = {
    "en": "Today's answer budget is used up, so here are the relevant guideline passages instead:",
    "es": "El presupuesto de respuestas de hoy se ha agotado; aquí tienes los pasajes relevantes de las guías:",
    "fr": "Le budget de réponses du jour est épuisé ; voici les passages pertinents des recommandations :",
    "de": "Das Antwortbudget für heute ist aufgebraucht; hier sind stattdessen die passenden Stellen aus den Leitlinien:",
    "ru": "Дневной лимит ответов исчерпан; вот подходящие фрагменты из рекомендаций:",
    "ar": "انتهت حصة الإجابات لهذا اليوم؛ إليك المقاطع المتعلقة من الإرشادات:",
    "pt": "O orçamento de respostas de hoje acabou; aqui estão os trechos relevantes das diretrizes:",
    "hi": "आज का उत्तर बजट समाप्त हो गया है; यहाँ दिशानिर्देशों के प्रासंगिक अंश हैं:",
}


#: Lo que se dice cuando el modelo no contesta (caído, lento o sin saldo). Distinto del aviso de
#: presupuesto: aquello es una decisión nuestra y esto una avería, y el lector merece saber cuál.
NO_MODEL = {
    "en": "I cannot write an answer right now, so here are the relevant guideline passages instead:",
    "es": "Ahora mismo no puedo redactar una respuesta; aquí tienes los pasajes relevantes de las guías:",
    "fr": "Je ne peux pas rédiger de réponse pour le moment ; voici les passages pertinents des recommandations :",
    "de": "Ich kann gerade keine Antwort formulieren; hier sind stattdessen die passenden Stellen aus den Leitlinien:",
    "ru": "Сейчас я не могу составить ответ; вот подходящие фрагменты из рекомендаций:",
    "ar": "لا أستطيع صياغة إجابة الآن؛ إليك المقاطع المتعلقة من الإرشادات:",
    "pt": "Não consigo redigir uma resposta agora; aqui estão os trechos relevantes das diretrizes:",
    "hi": "मैं अभी उत्तर नहीं लिख सकता; यहाँ दिशानिर्देशों के प्रासंगिक अंश हैं:",
}


CLARIFY = {
    "en": "I want to get this right. What's the main thing going on?",
    "es": "Quiero acertar. ¿Qué es lo principal que le pasa?",
    "fr": "Je veux bien comprendre. Quel est le principal problème ?",
    "de": "Ich möchte es richtig verstehen. Was ist das Hauptproblem?",
    "ru": "Хочу понять правильно. Что беспокоит больше всего?",
    "ar": "أريد أن أفهم الأمر بدقة. ما الذي يقلقك أكثر؟",
    "hi": "मैं ठीक से समझना चाहता हूँ। सबसे बड़ी दिक्कत क्या है?",
    "pt": "Quero acertar. O que está acontecendo, principalmente?",
}
CLARIFY_OPTIONS = {
    "en": [
        "Fever",
        "Cough or breathing",
        "Vomiting or diarrhoea",
        "Rash or skin",
        "A fall or injury",
        "Feeding or sleep",
        "Something else",
    ],
    "es": [
        "Fiebre",
        "Tos o respiración",
        "Vómitos o diarrea",
        "Manchas o piel",
        "Golpe o caída",
        "Comida o sueño",
        "Otra cosa",
    ],
    "fr": [
        "Fièvre",
        "Toux ou respiration",
        "Vomissements ou diarrhée",
        "Boutons ou peau",
        "Chute ou coup",
        "Alimentation ou sommeil",
        "Autre chose",
    ],
    "de": [
        "Fieber",
        "Husten oder Atmung",
        "Erbrechen oder Durchfall",
        "Ausschlag oder Haut",
        "Sturz oder Verletzung",
        "Essen oder Schlaf",
        "Etwas anderes",
    ],
    "ru": [
        "Температура",
        "Кашель или дыхание",
        "Рвота или понос",
        "Сыпь или кожа",
        "Падение или травма",
        "Еда или сон",
        "Другое",
    ],
    "ar": [
        "حرارة",
        "سعال أو تنفس",
        "قيء أو إسهال",
        "طفح جلدي",
        "سقوط أو إصابة",
        "طعام أو نوم",
        "شيء آخر",
    ],
    "pt": [
        "Febre",
        "Tosse ou respiração",
        "Vômitos ou diarreia",
        "Manchas ou pele",
        "Batida ou queda",
        "Comida ou sono",
        "Outra coisa",
    ],
    "hi": [
        "बुखार",
        "खाँसी या साँस",
        "उल्टी या दस्त",
        "दाने या त्वचा",
        "चोट या गिरना",
        "खाना या नींद",
        "कुछ और",
    ],
}
#: Lo que se responde a la última opción de CLARIFY_OPTIONS, la de «otra cosa». No es un
#: síntoma: es el botón que dice «nada de lo de arriba», y buscarlo en el corpus devuelve cero
#: fragmentos y por tanto «no tengo información fiable sobre esto». Medido el 9-sep-2026 sobre
#: las 56 combinaciones de opción × idioma: las ocho de esa columna acababan igual.
#:
#: Ofrecer un botón y contestar «no sé» a quien lo pulsa es peor que no ofrecerlo.
DESCRIBE_IT = {
    "en": "Of course. Tell me in your own words what is happening, and how old your child is.",
    "es": "Claro. Cuéntame con tus palabras qué le pasa y qué edad tiene.",
    "fr": "Bien sûr. Dites-moi avec vos mots ce qui se passe et l'âge de votre enfant.",
    "de": "Natürlich. Erzählen Sie mir mit Ihren Worten, was los ist, und wie alt Ihr Kind ist.",
    "ru": "Конечно. Расскажите своими словами, что происходит и сколько лет ребёнку.",
    "ar": "بالطبع. احكِ لي بكلماتك ما الذي يحدث وكم عمر طفلك.",
    "pt": "Claro. Conte com as suas palavras o que está acontecendo e a idade da criança.",
    "hi": "ज़रूर। अपने शब्दों में बताइए क्या हो रहा है और बच्चे की उम्र क्या है।",
}


#: Cierra la respuesta dada sin edad: se ha contestado, y con la edad se afina. Medido en
#: producción: pedirla ANTES de responder perdía a 10 de cada 11 padres (12-sep-2026).
AGE_REFINES = {
    "en": "How old is your child? With the age I can make this more precise.",
    "es": "¿Qué edad tiene? Con la edad afino la respuesta.",
    "fr": "Quel âge a votre enfant ? Avec l'âge, je peux préciser la réponse.",
    "de": "Wie alt ist Ihr Kind? Mit dem Alter kann ich die Antwort genauer machen.",
    "ru": "Сколько лет ребёнку? Зная возраст, я отвечу точнее.",
    "ar": "كم عمر طفلك؟ بمعرفة العمر أستطيع أن أجيب بدقة أكبر.",
    "pt": "Que idade tem? Com a idade afino a resposta.",
    "hi": "बच्चे की उम्र कितनी है? उम्र जानकर मैं जवाब और सटीक कर सकता हूँ।",
}

ASK_AGE = {
    "en": "To answer safely I need to know how old your child is (months or years). Could you tell me?",
    "es": "Para responder con seguridad necesito saber la edad (meses o años). ¿Me la dices?",
    "fr": "Pour répondre en toute sécurité, j'ai besoin de l'âge de votre enfant (en mois ou en années). Pouvez-vous me le dire ?",
    "de": "Um sicher antworten zu können, muss ich wissen, wie alt Ihr Kind ist (in Monaten oder Jahren). Können Sie mir das sagen?",
    "ru": "Чтобы ответить безопасно, мне нужно знать возраст ребёнка (в месяцах или годах). Подскажете?",
    "ar": "لكي أجيب بأمان أحتاج أن أعرف عمر طفلك (بالأشهر أو بالسنوات). هل يمكنك إخباري؟",
    "hi": "सुरक्षित जवाब देने के लिए मुझे बच्चे की उम्र जाननी होगी (महीनों या सालों में)। बता सकते हैं?",
    "pt": "Para responder com segurança preciso saber a idade (meses ou anos). Pode me dizer?",
}


@dataclass
class Answer:
    text: str
    level: str
    banner: str | None
    sources: list[str]
    lang: str
    prompt_version: str | None
    llm: LLMResult | None
    chunk_ids: list[str]
    verification: str  # ok | no_source | asked_age | dose_calculator | vaccine_schedule | clarify | regenerated | fallback
    expansion: list[str] = field(default_factory=list)
    options: list[str] = field(default_factory=list)  # quick replies when verification == 'clarify'
    # The guide written from the sources this answer used. None when nothing overlaps: a guide
    # that is merely on a related subject is not worth putting under a health answer.
    guide: GuideLink | None = None
    # Why the first draft was thrown away, when it was. Empty otherwise. Kept because "22% of
    # answers are regenerated" is a number you cannot act on without knowing which check fired.
    problems: list[str] = field(default_factory=list)
    # The page of this site that answers the same question better than prose: the vaccination
    # table, the dose calculator. None when there is not one.
    tool: ToolLink | None = None
    # Fiebre sin edad: se ha respondido con la regla del lactante por delante, y se pide la
    # edad para afinar. El chat pinta los botones de edad DEBAJO de la respuesta.
    ask_age: bool = False

    @property
    def clean_text(self) -> str:
        """Answer text for humans: citation markers removed (they stay in `text` for verification)."""
        t = _CIT.sub("", self.text)
        t = re.sub(r"[ \t]+([.,;:!?])", r"\1", t)  # "word [1]." → "word."
        t = re.sub(r"[ \t]{2,}", " ", t)
        return t.strip()

    def render(self) -> str:
        """What the parent sees (operator decision 25-ago): banner + short answer. No source list,
        no document titles, no links — the organisation is already named inside the text. The legal
        line lives in the UI, not in every message."""
        parts = []
        if self.banner:
            parts.append(self.banner)
        parts.append(self.clean_text)
        return "\n\n".join(parts)

    def render_debug(self) -> str:
        """Full rendering with numbered sources, for logs, eval and the operator."""
        parts = [self.render()]
        if self.sources:
            parts.append(
                ("Fuentes:" if self.lang == "es" else "Sources:") + "\n" + "\n".join(self.sources)
            )
        parts.append("ℹ️ " + DISCLAIMER[self.lang])
        return "\n\n".join(parts)


class EmergencyNumbers:
    def __init__(self, path: Path):
        self.raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    def get(self, country: str | None, lang: str = "en") -> dict[str, str | None]:
        """The country's own numbers, or a fallback phrase IN THE READER'S LANGUAGE.

        The fallback is not a number — no country has been chosen — so it is a sentence, and a
        sentence has a language. It used to be one English string dropped into all eight banners:
        "Rufen Sie jetzt your local emergency number an".
        """
        c = (country or "").upper()
        found = self.raw.get(c)
        if found:
            return dict(found)
        default = dict(self.raw["default"])
        phrases = default.get("emergency")
        if isinstance(phrases, dict):
            default["emergency"] = phrases.get(lang) or phrases["en"]
        return default


def load_prompt(version: str = "answer_v6") -> tuple[str, str]:
    text = (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")
    return version, text


@dataclass(frozen=True)
class ToolLink:
    """A page of this site that answers the same question better than prose can.

    `kind` and not a label: the words live in i18n.ts in eight languages, and a Spanish string
    coming out of the engine would be a ninth copy waiting to drift.
    """

    kind: str  # "vaccines" | "dose"
    url: str


def _growth_pages() -> set[str]:
    from pedibot.bot.growth import load_countries

    global _GROWTH_PAGES
    if _GROWTH_PAGES is None:
        _GROWTH_PAGES = set(
            load_countries(Path(__file__).resolve().parents[3] / "config" / "growth_charts.yaml")
        )
    return _GROWTH_PAGES


_GROWTH_PAGES: set[str] | None = None


def tool_link(kind: str, lang: str, country: str | None = None) -> ToolLink:
    prefix = "" if lang == "en" else f"/{lang}"
    if kind == "vaccines":
        tail = f"/vaccines/{country.lower()}" if country else "/vaccines"
    elif kind == "growth":
        # la página del país sólo si el país tiene página: un 404 bajo una respuesta de salud no
        tail = (
            f"/growth/{country.lower()}"
            if country and country.upper() in _growth_pages()
            else "/growth"
        )
    else:
        tail = "/dose"
    return ToolLink(kind, f"{prefix}{tail}")


def build_banner(tr: TriageResult, lang: str, numbers: dict[str, str | None]) -> str | None:
    if tr.level == "routine":
        return None
    reasons = "; ".join(tr.reasons(lang))
    if tr.level == "emergency":
        heads = {
            "es": f"🚨 Llama ahora al {numbers['emergency']} o acude a urgencias.",
            "en": f"🚨 Call {numbers['emergency']} now or go to the emergency department.",
            "fr": f"🚨 Appelez tout de suite le {numbers['emergency']} ou allez aux urgences.",
            "de": f"🚨 Rufen Sie jetzt {numbers['emergency']} an oder fahren Sie in die Notaufnahme.",
            "ru": f"🚨 Немедленно звоните {numbers['emergency']} или везите ребёнка в приёмное отделение.",
            "ar": f"🚨 اتصل الآن بـ {numbers['emergency']} أو توجّه فورا إلى قسم الطوارئ.",
            "pt": f"🚨 Ligue agora para {numbers['emergency']} ou vá ao pronto-socorro.",
            "hi": f"🚨 अभी {numbers['emergency']} पर कॉल करें या तुरंत इमरजेंसी ले जाएँ।",
        }
    elif tr.level == "urgent":
        heads = {
            "es": "🚨 Con estos síntomas hay que acudir a urgencias hoy, sin esperar.",
            "en": "🚨 With these symptoms your child should be seen in the emergency department today, without waiting.",
            "fr": "🚨 Avec ces signes, votre enfant doit être vu aux urgences aujourd'hui, sans attendre.",
            "de": "🚨 Mit diesen Anzeichen sollte Ihr Kind heute in der Notaufnahme gesehen werden, ohne zu warten.",
            "ru": "🚨 С такими признаками ребёнка нужно показать врачу в приёмном отделении сегодня, не откладывая.",
            "ar": "🚨 مع هذه العلامات يجب أن يراه طبيب في قسم الطوارئ اليوم، دون تأخير.",
            "pt": "🚨 Com esses sintomas é preciso ir ao pronto-socorro hoje, sem esperar.",
            "hi": "🚨 इन लक्षणों के साथ बच्चे को आज ही इमरजेंसी में दिखाना चाहिए, देर न करें।",
        }
    else:  # mental_health
        # The bracket exists to tell two different numbers apart. Where the country has no
        # separate line for suicide — or no country was chosen — `mental` IS `emergency`, and the
        # sentence used to name the same long phrase twice, in nested brackets, on the banner that
        # sits above a parent who has just typed that their child wants to die.
        mental = numbers.get("mental")
        also = numbers["emergency"] if mental and mental != numbers["emergency"] else None
        mental = mental or numbers["emergency"]
        heads = {
            "es": f"💛 Esto es importante y no estás solo/a. Llama al {mental}"
            + (f" (o al {also} si hay peligro inmediato)" if also else "")
            + ". Si el menor ha hecho algo para hacerse daño, acude a urgencias ahora.",
            "en": f"💛 This matters and you are not alone. Call {mental}"
            + (f" (or {also} if there is immediate danger)" if also else "")
            + ". If your child has already done something to harm themselves, go to the emergency"
            " department now.",
            "fr": f"💛 C'est important et vous n'êtes pas seul·e. Appelez le {mental}"
            + (f" (ou le {also} en cas de danger immédiat)" if also else "")
            + ". Si votre enfant s'est déjà fait du mal, allez aux urgences maintenant.",
            "de": f"💛 Das ist wichtig, und Sie sind damit nicht allein. Rufen Sie {mental} an"
            + (f" (oder {also} bei unmittelbarer Gefahr)" if also else "")
            + ". Wenn Ihr Kind sich bereits etwas angetan hat, fahren Sie jetzt in die"
            " Notaufnahme.",
            "ru": f"💛 Это важно, и вы не одни. Позвоните {mental}"
            + (f" (или {also}, если опасность прямо сейчас)" if also else "")
            + ". Если ребёнок уже причинил себе вред, везите его в приёмное отделение немедленно.",
            "ar": f"💛 هذا أمر مهم ولست وحدك. اتصل بـ {mental}"
            + (f" (أو بـ {also} إذا كان الخطر الآن)" if also else "")
            + ". وإذا كان طفلك قد آذى نفسه بالفعل، فتوجّه إلى قسم الطوارئ حالا.",
            "pt": f"💛 Isso é importante e você não está sozinho(a). Ligue para {mental}"
            + (f" (ou para {also} se houver perigo imediato)" if also else "")
            + ". Se a criança já fez algo para se machucar, vá ao pronto-socorro agora.",
            "hi": f"💛 यह ज़रूरी है और आप अकेले नहीं हैं। {mental} पर कॉल करें"
            + (f" (या {also} पर अगर खतरा अभी है)" if also else "")
            + "। अगर बच्चे ने खुद को नुकसान पहुँचाया है, तो अभी इमरजेंसी ले जाएँ।",
        }
    head = heads.get(lang, heads["en"])
    why = {
        "es": "Motivo",
        "fr": "Raison",
        "de": "Grund",
        "ru": "Причина",
        "ar": "السبب",
        "pt": "Motivo",
        "hi": "कारण",
    }.get(lang, "Reason") + f": {reasons}"
    return head + "\n" + why


#: Los signos que separan palabras, en las escrituras que el producto habla. El árabe tiene
#: su propia coma (،), su punto y coma (؛) y su interrogación (؟); el urdu su punto (۔); y el
#: hindi termina las frases con danda (। ॥). Son caracteres distintos de los latinos y no
#: estaban en la lista, así que «بنادول؟» no era «بنادول» y la pregunta árabe más natural
#: —«mi hijo pesa 14 kilos, ¿cuánto Panadol le doy?»— se quedaba sin dosis (11-sep-2026).
#: Misma familia que el borde de palabra que no funciona en devanagari y que el artículo
#: pegado en árabe: el código da por hecha la forma de una lengua que no es la suya, no
#: falla, y sólo deja de encontrar.
#:
#: Se traducen a espacio y se parte con `split()`, que ya sabe de todos los blancos: así la
#: lista es literalmente la lista de signos, sin una sola barra invertida que escapar.
_SIGNOS = ",.;:!?¿¡()[]«»\"'/\\-" + "،؛؟۔।॥" + "\u2013\u2014"
_A_ESPACIO = str.maketrans({c: " " for c in _SIGNOS})


def dose_intent(query: str, drugs: DrugCatalog | None = None) -> tuple[str, float] | None:
    """(drug_key, weight_kg) when the message is a dose question with an explicit weight.

    Brand names (Calpol, Tylenol, Dalsy, Nurofen…) resolve through the catalogue when given."""
    query = query.translate(_DIGITOS)
    w = _WEIGHT.search(query)
    if not w:
        return None
    kg = float(w.group(1).replace(",", "."))
    key: str | None = None
    d = _DRUG.search(query)
    if d:
        key = _DRUG_ALIAS.get(d.group(1).lower(), d.group(1).lower())
    elif drugs is not None:
        # Las palabras, en cualquier escritura. Se parte por espacios y puntuación en vez de
        # preguntar «¿esto es una letra?»: `\w` son los caracteres alfanuméricos, y las vocales
        # del devanagari (las matras: ा ि ो ै) son marcas combinantes, así que una versión basada
        # en `\w` rompe «पैरासिटामोल» en trozos de una letra y no encuentra nada. Es el primo
        # hermano del `\b` que tampoco funciona en esa escritura (ver triage.py).
        for tok in query.lower().translate(_A_ESPACIO).split():
            if len(tok) < 4:
                continue
            r = drugs.resolve(tok)
            if r:
                key = r[0]
                break
    if key is None or key not in DRUGS:
        return None
    return key, kg


_CHILD = re.compile(
    r"\b(hij[oa]|beb[eé]|ni[ñn][oa]|peque|my (son|daughter|baby|child|toddler|kid|little one)|"
    r"mon (fils|b[eé]b[eé]|enfant)|ma (fille|petite)|mein[e]? (sohn|tochter|kind|baby)|"
    r"(мой|моя|моего|моей|у) (сын|доч|ребён|ребен|малыш|младен)|ребён[коа]|ребен[коа]|"
    r"طفل|ابني|ابنتي|رضيع|مولود|"
    r"\d+\s*(años|año|meses|mes|year|years|month|months|weeks?|semanas?|ans|mois|"
    r"jahre[n]?|monate[n]?|wochen|лет|год\w*|месяц\w*|недел\w*|سنة|سنوات|شهر|أشهر|أسبوع)\b)",
    re.I,
)


def _mentions_child(text: str) -> bool:
    return bool(_CHILD.search(text))


def _age_context(tr: TriageResult) -> str:
    """Age line for the prompt. Under 3 months: home medication advice is never appropriate."""
    if tr.age_months is None and not tr.has_fever:
        return "CHILD AGE: unknown\n"
    if tr.age_months is None:
        # Sólo con fiebre. Del 12 al 13-sep-2026 esta orden iba en toda respuesta sin edad y el
        # modelo la obedecía: el queroseno o el escozor al orinar abrían hablando de fiebre.
        return (
            "CHILD AGE: unknown. Open with ONE sentence: if the child is under 3 months old, a "
            "fever needs a doctor the same day. Then answer for an older child. Give NO specific "
            "medication dose (no mg, no ml): the dose depends on the age and weight you do not "
            "have.\n"
        )
    if tr.age_months < 3:
        return (
            f"CHILD AGE: {tr.age_months:g} months — UNDER 3 MONTHS. Do NOT suggest giving any "
            "medication at home (no paracetamol, no ibuprofen); do not describe home management "
            "of fever. Say that babies this young must be assessed by a doctor the same day and "
            "keep the answer short.\n"
        )
    if tr.age_months < 6:
        return (
            f"CHILD AGE: {tr.age_months:g} months — under 6 months. Do not suggest ibuprofen; "
            "any medication only if a doctor advised it.\n"
        )
    return f"CHILD AGE: {tr.age_months:g} months\n"


def _history_block(history: list[dict[str, str]]) -> str:
    if not history:
        return ""
    lines = []
    for t in history:
        who = "Parent" if t.get("role") == "user" else "PediBot"
        lines.append(f"{who}: {t['text'][:600]}")
    return (
        "CONVERSATION SO FAR (answer the LAST parent message; earlier turns give context such as age or symptoms already mentioned):\n"
        + "\n".join(lines)
        + "\n\n"
    )


def _needs_age(query: str, tr: TriageResult) -> bool:
    """Fever without age: answer with the under-3-months rule first, then ask the age to refine."""
    return tr.has_fever and tr.age_months is None


def _format_sources(hits: list[Hit]) -> str:
    lines = []
    for i, h in enumerate(hits, start=1):
        c = h.chunk
        tag = " [DOSE TABLE]" if c.is_dose_table else ""
        tag += " [WARNING SIGNS]" if c.is_red_flag else ""
        lines.append(
            f"[{i}] {c.org} — {c.doc_title} — section: {c.section} (p. {', '.join(map(str, c.pages))}){tag}\n{c.text}"
        )
    return "\n\n".join(lines)


#: Numbers and services that only work in the country the source was written in. A parent reading
#: an English answer may be anywhere, and "call NHS 111" is worse than no number at all: it costs
#: them the seconds they spend finding out it does not ring. The prompt forbids these in capital
#: letters and the model prints them anyway, so the draft is refused and rewritten instead of
#: asked nicely. Shared with the guide generator so the two lists cannot drift.
FOREIGN_SERVICE = re.compile(
    r"\b999\b|\b911\b|NHS\s*111|(?<![\d.,])111(?![\d.,])|\bA&E\b|GP surgery|GP appointment|"
    r"1-800-222-1222|91\s?562\s?04\s?20"
)


def foreign_service_problem(text: str) -> str | None:
    """The verification message for a text that sends the reader somewhere they cannot go."""
    m = FOREIGN_SERVICE.search(text)
    if not m:
        return None
    return (
        f"foreign_service ({m.group(0)!r}): never send the reader to a number or service that"
        " only exists where the source was written. Write 'your doctor', 'your local emergency"
        " number' or 'the emergency department'."
    )


#: The few organisations whose name is not the same word in every language. The rest are acronyms
#: (SEUP, NHS, CDC, RKI, AEP, AEMPS) or a product name (MedlinePlus) and travel unchanged.
ORG_ALIASES: dict[str, tuple[str, ...]] = {
    "WHO": (
        "OMS",
        "ВОЗ",
        "منظمة الصحة العالمية",
        "Weltgesundheitsorganisation",
        "विश्व स्वास्थ्य संगठन",
    ),
    "Gouvernement du Canada": ("Canada", "Canadá", "Kanada", "Канада", "كندا", "कनाडा"),
    "Junta de Andalucía": ("Andalucía", "Andalusia", "Andalusien", "Andaluzia"),
    "Ministerio de Sanidad": (
        "Ministerio de Sanidad",
        "Ministry of Health",
        "ministère",
        "Gesundheitsministerium",
        "Минздрав",
        "وزارة الصحة",
        "स्वास्थ्य मंत्रालय",
    ),
}


def _org_mentions(text: str, hits: list[Hit]) -> dict[str, int]:
    """How many times the answer names each body it cited, counting its aliases as the same one."""
    cited = {int(n) for n in _CIT.findall(text)}
    low = text.lower()
    out: dict[str, int] = {}
    for n in sorted(cited):
        if not 1 <= n <= len(hits):
            continue
        org = hits[n - 1].chunk.org
        if org in out:
            continue
        out[org] = sum(low.count(name.lower()) for name in (org, *ORG_ALIASES.get(org, ())))
    return out


def names_a_source(text: str, hits: list[Hit]) -> bool:
    """Does the answer say, in words, where any of what it cited came from?"""
    counts = _org_mentions(text, hits)
    return any(counts.values()) if counts else True


#: Naming the SAME body this many times is where an answer stops reading like prose and starts
#: reading like a deposition. Two different bodies twice each is fine and often right.
MAX_SAME_ORG = 2


def verify(text: str, hits: list[Hit]) -> list[str]:
    """Return a list of problems (empty = ok)."""
    problems: list[str] = []
    nums = [int(n) for n in _CIT.findall(text)]
    if not nums:
        problems.append("no_citations")
    for n in nums:
        if n < 1 or n > len(hits):
            problems.append(f"bad_citation_{n}")
    sanctioned = any(h.chunk.is_dose_table and h.chunk.is_dose_source for h in hits)
    if looks_like_medication_dose(text) and not sanctioned:
        problems.append("dose_without_table")
    return problems


def verify_answer(text: str, hits: list[Hit]) -> list[str]:
    """`verify` plus the guard on services that only exist in one country.

    Kept separate because an article is verified on a filtered copy of its body — its sources are
    quoted verbatim in a block that legitimately contains "NHS 111" — while an answer is checked
    on exactly what the model wrote. The banner above the answer is ours, carries the reader's own
    emergency number, and is never part of this.
    """
    problems = verify(text, hits)
    found = foreign_service_problem(text)
    if found:
        problems.append(found)
    counts = _org_mentions(text, hits)
    if not names_a_source(text, hits):
        problems.append(
            "no_organisation_named: name the organisation in words the first time you use a"
            " source (SEUP, NHS, WHO, CDC, MedlinePlus…), with the fact first"
        )
    worst = max(counts.items(), key=lambda kv: kv[1], default=("", 0))
    if worst[1] > MAX_SAME_ORG:
        problems.append(
            f"repeated_attribution ({worst[0]} named {worst[1]} times): name each source once,"
            " when you first use it. Repeating it in sentence after sentence reads like a"
            " deposition, not like someone helping a worried parent."
        )
    return problems


class Engine:
    def __init__(
        self,
        retriever: Retriever,
        triage: Triage,
        llm: LLMProvider,
        numbers: EmergencyNumbers,
        prompt_version: str = "answer_v6",
        drugs: DrugCatalog | None = None,
        vaccines: Vaccines | None = None,
        guides: GuideIndex | None = None,
    ):
        self.retriever = retriever
        self.triage = triage
        self.llm = llm
        self.numbers = numbers
        self.prompt_version, self.prompt = load_prompt(prompt_version)
        self.drugs = drugs
        self.vaccines = vaccines
        self.guides = guides

    def _inject_rule_sources(self, tr: TriageResult, hits: list[Hit]) -> list[Hit]:
        """When a triage rule fired, put the warning-signs chunk of the rule's own source first,
        so the drafted sentence "must be seen today" can cite it instead of echoing the prompt
        (faithfulness judge, 25-ago: 6 of 8 'unfaithful' were exactly this)."""
        if not tr.matched:
            return hits
        present = {h.chunk.doc_id for h in hits if h.chunk.is_red_flag}
        injected: list[Hit] = []
        for rule in tr.matched:
            if rule.source in present:
                continue
            c = self.retriever.index.red_flag_chunk(rule.source)
            if c is not None:
                injected.append(Hit(c, 99.0, 1))
                present.add(rule.source)
        return (injected + hits)[: max(len(hits), 6) + len(injected)]

    def answer_without_model(
        self, query: str, country: str | None = None, lang: str | None = None, why: str = "no_model"
    ) -> Answer:
        """La respuesta cuando no hay modelo: los pasajes recuperados, y el triaje entero.

        Vive aquí y no en el API porque los dos frentes la necesitan — la web y Telegram— y hasta
        el 7-sep-2026 solo el API tenía algo parecido. `why` viaja hasta la base y distingue las
        dos causas: `degraded` es el tope de gasto del día, que decidimos nosotros, y `no_model`
        una avería del proveedor. Mezclarlas escondería la avería dentro de algo que parece normal.

        Lo que NO se pierde por no haber modelo: el nivel de triaje y el banner de urgencia. Son
        deterministas y gratis —no llaman al modelo, no cuestan un céntimo— y son lo único de la
        respuesta que no se puede permitir desaparecer justo el día que el sistema va mal.
        """
        lang = lang or "en"
        hits, _ = self.retriever.search(query, lang)
        tr = self.triage.assess(query)
        banner = build_banner(tr, lang, self.numbers.get(country, lang))
        aviso = BUDGET_SPENT if why == "degraded" else NO_MODEL
        text = NO_SOURCE[lang] if not hits else aviso.get(lang, aviso["en"])
        return Answer(
            text,
            tr.level,
            banner,
            [f"[{i}] {h.chunk.citation()}" for i, h in enumerate(hits, 1)],
            lang,
            None,
            None,
            [h.chunk.chunk_id for h in hits],
            why,
        )

    def ask(
        self,
        query: str,
        country: str | None = None,
        lang: str | None = None,
        history: list[dict[str, str]] | None = None,
        mode: str = "parent",
    ) -> Answer:
        """`history`: previous turns, oldest first, [{"role": "user"|"assistant", "text": ...}].
        Only the last MAX_TURNS are used (PRD §5.4)."""
        history = (history or [])[-MAX_TURNS:]
        prior_user = " ".join(t["text"] for t in history if t.get("role") == "user")
        context_text = f"{prior_user} {query}".strip() if prior_user else query
        lang = lang or detect_lang(query)
        if lang not in SUPPORTED_LANGS:
            lang = "en"
        tr = self.triage.assess(context_text)
        tr_now = self.triage.assess(query)
        # Una regla que ya saltaba con lo de ANTES no vuelve a dar el aviso cada turno: al padre
        # ya se lo dijimos y repetirlo enseña a ignorarlo. Pero una regla que salta al juntar lo
        # de antes con lo de ahora **es información nueva**, y esa es la que hay que avisar.
        #
        # El filtro miraba solo el mensaje actual, y con eso se perdían justo las reglas que
        # existen para una combinación —que son las que un padre cuenta en dos frases. Medido el
        # 8-sep-2026 sobre conversaciones de dos turnos:
        #
        #     «se ha dado un golpe en la cabeza» → «ahora ha vomitado dos veces»   se perdía
        #     «le duele la barriga»              → «ahora más en el lado derecho»  se perdía
        #     «le han salido unas manchas»       → «no desaparecen al apretar»     se perdía
        #
        # La tercera es el signo del meningococo, contado exactamente como lo cuenta alguien que
        # acaba de hacer la prueba del vaso: describe la mancha, y en el mensaje siguiente el
        # resultado. La regla estaba, saltaba con las dos frases juntas, y el filtro la tiraba.
        if history:
            # lo que ya saltaba SIN el mensaje de ahora
            antes = {r.id for r in self.triage.assess(prior_user).matched} if prior_user else set()
            # lo que salta al juntarlo todo y no saltaba antes: lo ha traído este mensaje
            completadas = {r.id for r in tr.matched} - antes
            keep = (
                {r.id for r in tr_now.matched}
                | completadas
                | {
                    # la edad es contexto, no un síntoma: sigue valiendo turno tras turno
                    "infant_fever_under_3_months",
                    "newborn_refusing_feeds",
                }
            )
            tr.matched = [r for r in tr.matched if r.id in keep]
            tr.level = max(
                (r.level for r in tr.matched), key=lambda lv: LEVEL_ORDER[lv], default="routine"
            )
        nums = self.numbers.get(country, lang)
        banner = build_banner(tr, lang, nums)

        intent = dose_intent(query, self.drugs) or (
            dose_intent(context_text, self.drugs)
            if _DRUG.search(query)
            or (
                self.drugs
                and any(
                    # mismo barrido por espacios que en `dose_intent`: la versión latina no
                    # encontraba una sola palabra en cirílico, árabe ni devanagari, así que
                    # el enlace a la calculadora no se ofrecía en tres de los ocho idiomas
                    self.drugs.resolve(t)
                    for t in query.lower().translate(_A_ESPACIO).split()
                    if len(t) >= 4
                )
            )
            else None
        )
        if intent and tr.level == "routine":
            drug, kg = intent
            text = format_result(calculate(drug, kg, tr.age_months), lang)
            return Answer(
                text,
                tr.level,
                None,
                [],
                lang,
                None,
                None,
                [],
                "dose_calculator",
                tool=tool_link("dose", lang),
            )

        if self.vaccines is not None and tr.level == "routine" and is_vaccine_question(query):
            # "Quels vaccins pour un bébé de 3 mois EN FRANCE ?" used to fall through to the
            # corpus and come back as "I have no reliable information", with the country sitting
            # in the sentence the whole time. Read only when the reader picked none, and only a
            # name they wrote themselves — never inferred from the language.
            c = self.vaccines.resolve_country(country) or self.vaccines.resolve_country(
                country_in_question(context_text)
            )
            if c is not None:
                text = format_answer(self.vaccines, c, tr.age_months, lang)
                return Answer(
                    text,
                    tr.level,
                    None,
                    [],
                    lang,
                    None,
                    None,
                    [],
                    "vaccine_schedule",
                    tool=tool_link("vaccines", lang, c),
                )
            # no tabulated schedule for this country → fall through to the sources

        # el botón «otra cosa», que ofrecemos nosotros y no es un síntoma. Se compara con la
        # lista que le acabamos de enseñar, en su idioma, para no confundirlo con una pregunta
        # de verdad que empiece igual.
        if query.strip().lower() == CLARIFY_OPTIONS[lang][-1].strip().lower():
            return Answer(DESCRIBE_IT[lang], tr.level, banner, [], lang, None, None, [], "clarify")

        # vague first message -> offer options. The topic is read from the query PLUS its synonym
        # expansion, the same as retrieval does: "se ha desmayado" or "llora sin parar" are clear
        # questions that the taxonomy does not name literally, and clarifying them is a bad answer.
        if (
            tr.level == "routine"
            and not history
            and self.retriever.taxonomy is not None
            and self.retriever.taxonomy.topic_for(
                query + " " + " ".join(self.retriever.expand(query, lang))
            )
            is None
            and (len(query.split()) <= 3 or _mentions_child(query))
        ):
            return Answer(
                CLARIFY[lang],
                tr.level,
                None,
                [],
                lang,
                None,
                None,
                [],
                "clarify",
                options=CLARIFY_OPTIONS[lang],
            )

        # Fiebre sin edad: hasta el 12-sep-2026 aquí se devolvía ASK_AGE sin responder, y el
        # registro dice que 10 de 11 padres no volvieron. Ahora se responde con la regla del
        # lactante por delante (ver _age_context) y se pide la edad al final, para afinar.
        ask_age = tr.level == "routine" and _needs_age(context_text, tr)

        prev_user = next((t["text"] for t in reversed(history) if t.get("role") == "user"), "")
        search_q = f"{prev_user} {query}" if prev_user and len(query.split()) <= 8 else query
        hits, extra = self.retriever.search(search_q, lang, red_flag_boost=tr.is_alarm)
        hits = self._inject_rule_sources(tr, hits)
        if not hits:
            return Answer(
                NO_SOURCE[lang], tr.level, banner, [], lang, None, None, [], "no_source", extra
            )

        answer_lang = LANGUAGE_NAME.get(lang, "English")
        user = (
            f"ANSWER LANGUAGE: {answer_lang} — the parent wrote in {answer_lang}; "
            "the sources may be in another language, translate faithfully.\n"
            f"{_age_context(tr)}"
            f"{_history_block(history)}"
            f"{CHILD_MODE if mode == 'child' else ''}"
            f"PARENT MESSAGE:\n{query}\n\nSOURCES:\n{_format_sources(hits)}"
        )
        result = self.llm.complete(self.prompt, user, temperature=0.2)
        problems = verify_answer(result.text, hits)
        verification = "ok"
        if problems:
            verification = "regenerated"
            retry = self.llm.complete(
                self.prompt
                + "\n\nYour previous draft failed verification: "
                + ", ".join(problems)
                + ". Fix it.",
                user,
                temperature=0.0,
            )
            # `verify`, not `verify_answer`: only the SAFETY checks can send an answer to the
            # fallback. A style problem — the same body named three times, nobody named at all —
            # gets its one retry and then ships as written. Turning a medically sound answer into
            # "I have no reliable information on this" because it reads stiffly would be a far
            # worse failure than the stiffness.
            if verify(retry.text, hits):
                return Answer(
                    NO_SOURCE[lang],
                    tr.level,
                    banner,
                    [],
                    lang,
                    self.prompt_version,
                    retry,
                    [h.chunk.chunk_id for h in hits],
                    "fallback",
                    extra,
                    problems=problems,
                )
            result = retry

        cited = sorted({int(n) for n in _CIT.findall(result.text)})
        sources = [
            f"[{n}] {hits[n - 1].chunk.citation()}"
            + (f" — {hits[n - 1].chunk.source_url}" if hits[n - 1].chunk.source_url else "")
            for n in cited
        ]
        # the CITED chunks, not every hit: the guide to offer is the one built from the material
        # this answer actually used, and half the retrieved chunks never make it into the text
        guide = (
            self.guides.best_for([hits[n - 1].chunk.chunk_id for n in cited], lang, query)
            if self.guides is not None
            else None
        )
        # A drafted answer can still be about vaccines or about a medicine — the tool did not
        # answer it because no country was known, or because no weight was given. The page is
        # still the better place for what they asked.
        tool = None
        if self.vaccines is not None and is_vaccine_question(context_text):
            tool = tool_link(
                "vaccines",
                lang,
                self.vaccines.resolve_country(country)
                or self.vaccines.resolve_country(country_in_question(context_text)),
            )
        elif intent or _DRUG.search(context_text):
            tool = tool_link("dose", lang)
        # «está muy delgado y no gana peso», «¿qué percentil tiene?»: la curva de la OMS,
        # calculada, contesta mejor que la prosa (13-sep-2026)
        elif is_growth_question(context_text):
            tool = tool_link("growth", lang, country or country_in_question(context_text))
        text = result.text.strip()
        if ask_age:
            text += "\n\n" + AGE_REFINES[lang]
        return Answer(
            text,
            tr.level,
            banner,
            sources,
            lang,
            self.prompt_version,
            result,
            [h.chunk.chunk_id for h in hits],
            verification,
            extra,
            guide=guide,
            problems=problems,
            tool=tool,
            ask_age=ask_age,
        )
