"""The answer pipeline (PRD §5.1): triage → retrieval → drafting → verification → assembly."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pedibot.bot.about import ficha_de, responde_sobre
from pedibot.bot.dose import DRUGS, bottles_in_country, calculate, format_result
from pedibot.bot.drugs import DrugCatalog
from pedibot.bot.emergency_question import (
    country_name,
    format_numbers,
    is_emergency_number_question,
)
from pedibot.bot.growth import (
    Growth,
    asks_if_a_measure_is_normal,
    explain,
    gives_both_measurements,
    is_growth_question,
    measurements,
)
from pedibot.bot.guides import GuideIndex, GuideLink
from pedibot.bot.interpret import interpret
from pedibot.bot.llm import LLMProvider, LLMResult
from pedibot.bot.muac import assess as muac_assess
from pedibot.bot.muac import explain as muac_explain
from pedibot.bot.muac import is_muac_question, read_mm
from pedibot.bot.muac import reason as muac_reason
from pedibot.bot.retrieval import Retriever, detect_lang
from pedibot.bot.strings import LANGUAGE_NAME, STRINGS, tool_strings
from pedibot.bot.triage import ASISTENTE, LEVEL_ORDER, Triage, TriageResult
from pedibot.bot.vaccines import (
    Vaccines,
    country_in_question,
    format_answer,
    is_vaccine_question,
    pide_calendario,
)
from pedibot.bot.who_first import extra_terms as who_first_terms
from pedibot.bot.who_first import prompt_note as who_first_note
from pedibot.bot.who_first import tropical_note
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
#: Los idiomas en los que este producto contesta ENTEROS: web, guías, fuentes y respuesta.
#: Las respuestas que son una frase FIJA nuestra, sin cifras ni contenido médico nuevo, y que por
#: eso se pueden traducir con el modelo a una lengua que el sitio no tiene (21-sep-2026). Las de
#: las herramientas —dosis, calendarios, curvas, teléfonos— no están aquí a propósito: ésas no
#: las toca el modelo nunca.
def _dice_sin_fuente(texto: str) -> bool:
    """¿El redactor ha contestado la señal de «ningún pasaje responde a esto»?

    El prompt pide la palabra sola, y el modelo a veces la adorna: «No encuentro en las fuentes
    información sobre un dedo roto. NO_SOURCE» (21-sep-2026). Así no se reconocía, la respuesta
    caía en la verificación por no citar y la segunda búsqueda no llegaba a lanzarse. Cuenta
    como señal si aparece y el texto no cita nada: con citas, es una respuesta de verdad.

    Y lo mismo una frase corta sin ninguna cita: «No puedo responder a esa pregunta con la
    información de la que dispongo» es la misma señal dicha con palabras (batería del
    21-sep-2026, veintiséis respuestas acabaron así en «fallback» sin segunda búsqueda).
    """
    if _CIT.search(texto):
        return False
    return "NO_SOURCE" in texto.upper() or len(texto.split()) < 40


_FRASES_FIJAS = frozenset({"no_source", "fallback", "clarify", "asked_age", "about", "off_topic"})

TRADUCE = (
    "Translate the text into the language named on the first line. Output only the "
    "translation, nothing else. Keep emojis, numbers and phone numbers exactly as they are."
)

SUPPORTED_LANGS = ("es", "en", "fr", "de", "ru", "ar", "pt", "hi")

#: Y los que la capa de seguridad sabe leer y escribir, aunque la respuesta larga todavía no
#: venga en ellos (18-sep-2026).
#:
#: El suajili está aquí y no arriba, y la diferencia es deliberada. El triaje entiende suajili en
#: las 83 reglas, el detector lo reconoce y los tres avisos están escritos en suajili: un padre de
#: Kisumu que escribe «mtoto wangu ana degedege» recibe el aviso rojo en su lengua, que es la
#: parte que dice qué hacer y la que no se puede permitir llegar tarde.
#:
#: Lo que NO tiene todavía es corpus: no hay ni un documento en suajili con licencia abierta en el
#: índice, así que la explicación larga y sus fuentes salen en inglés —lengua oficial en Kenia,
#: Tanzania y Uganda— en vez de en un suajili sin nada detrás que citar. Prometer la respuesta
#: entera en suajili hoy sería prometer fuentes que no existen, que es justo lo que este proyecto
#: no hace (L147, L167). Sube a la lista de arriba el día que haya material que citar.
TRIAGE_LANGS = (*SUPPORTED_LANGS, "sw")

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
#: Lo que va debajo de un aviso urgente o de emergencia cuando no hay fuente que añadir.
SIGUE_EL_AVISO = {
    "en": "Do what the warning above says, now. I have no further detail on this exact situation in my guidelines, so I won't add anything that could hold you up.",
    "es": "Haz ahora lo que dice el aviso de arriba. No tengo en mis guías más detalle sobre esta situación concreta, así que no voy a añadir nada que pueda retrasarte.",
    "fr": "Faites maintenant ce que dit l'avertissement ci-dessus. Je n'ai pas plus de détails sur cette situation précise dans mes recommandations, donc je n'ajoute rien qui pourrait vous retarder.",
    "de": "Tun Sie jetzt, was im Hinweis oben steht. Zu genau dieser Situation habe ich in meinen Leitlinien keine weiteren Details, deshalb füge ich nichts hinzu, was Sie aufhalten könnte.",
    "ru": "Сделайте сейчас то, что сказано в предупреждении выше. Подробностей именно об этой ситуации в моих рекомендациях нет, поэтому я не буду добавлять ничего, что может вас задержать.",
    "ar": "افعل الآن ما يقوله التنبيه في الأعلى. لا توجد في إرشاداتي تفاصيل أخرى عن هذه الحالة بالتحديد، لذلك لن أضيف شيئًا قد يؤخرك.",
    "hi": "ऊपर की चेतावनी में जो लिखा है, वह अभी कीजिए। इस ख़ास स्थिति पर मेरे दिशानिर्देशों में और जानकारी नहीं है, इसलिए मैं ऐसा कुछ नहीं जोड़ूँगा जिससे आपको देर हो।",
    "pt": "Faça agora o que diz o aviso acima. Não tenho nas minhas orientações mais detalhes sobre esta situação concreta, por isso não vou acrescentar nada que o possa atrasar.",
}
#: «¿Qué es PediBot?» (21-sep-2026). Un texto FIJO y revisado, no una respuesta redactada por el
#: modelo: lo que el sitio dice de sí mismo no puede depender de cómo le salga ese día. Sin
#: cifras a propósito —cuántos países, cuántos documentos—, porque ésas cambian y un texto fijo
#: con una cifra es una cifra que envejece sin que nadie se entere (ver `DATOS.md`).
ABOUT_PEDIBOT = {
    "en": "PediBot is a free service that answers questions about children's health using only guidelines published by health ministries, the WHO and paediatric societies, and it shows which document each sentence comes from. It does not diagnose and does not replace your paediatrician: it explains what the guidelines say, when a child needs to be seen and which emergency number to call in your country. It works without an account and without asking for personal data. Tell me what is worrying you about your child.\n\nWho makes it and how it is funded: pedibot.xyz/about",
    "es": "PediBot es un servicio gratuito que contesta dudas sobre la salud de los niños usando sólo guías publicadas por ministerios de sanidad, la OMS y sociedades de pediatría, y enseña de qué documento sale cada frase. No diagnostica ni sustituye a tu pediatra: explica qué dicen las guías, cuándo hay que llevar al niño al médico y a qué número de emergencias llamar en tu país. Funciona sin cuenta y sin pedir datos personales. Cuéntame qué te preocupa de tu hijo.\n\nQuién lo hace y cómo se financia: pedibot.xyz/es/about",
    "fr": "PediBot est un service gratuit qui répond aux questions sur la santé des enfants en s'appuyant uniquement sur les recommandations publiées par les ministères de la santé, l'OMS et les sociétés de pédiatrie, et il indique de quel document vient chaque phrase. Il ne pose pas de diagnostic et ne remplace pas votre pédiatre : il explique ce que disent les recommandations, quand un enfant doit être vu par un médecin et quel numéro d'urgence appeler dans votre pays. Il fonctionne sans compte et sans demander de données personnelles. Dites-moi ce qui vous inquiète chez votre enfant.\n\nQui le fait et comment il est financé : pedibot.xyz/fr/about",
    "de": "PediBot ist ein kostenloser Dienst, der Fragen zur Gesundheit von Kindern ausschließlich anhand von Leitlinien beantwortet, die Gesundheitsministerien, die WHO und kinderärztliche Fachgesellschaften veröffentlicht haben, und er zeigt, aus welchem Dokument jeder Satz stammt. Er stellt keine Diagnosen und ersetzt nicht Ihre Kinderärztin oder Ihren Kinderarzt: Er erklärt, was die Leitlinien sagen, wann ein Kind ärztlich gesehen werden muss und welche Notrufnummer in Ihrem Land gilt. Er funktioniert ohne Konto und ohne persönliche Daten. Erzählen Sie mir, was Sie bei Ihrem Kind beunruhigt.\n\nWer es macht und wie es finanziert wird: pedibot.xyz/de/about",
    "ru": "PediBot — бесплатный сервис, который отвечает на вопросы о здоровье детей, опираясь только на рекомендации, опубликованные министерствами здравоохранения, ВОЗ и педиатрическими обществами, и показывает, из какого документа взята каждая фраза. Он не ставит диагнозов и не заменяет вашего педиатра: он объясняет, что говорят рекомендации, когда ребёнка нужно показать врачу и по какому номеру звонить в экстренных случаях в вашей стране. Он работает без регистрации и не просит личных данных. Расскажите, что вас беспокоит в состоянии ребёнка.\n\nКто это делает и на что: pedibot.xyz/ru/about",
    "ar": "PediBot خدمة مجانية تجيب عن أسئلة صحة الأطفال بالاعتماد فقط على الإرشادات التي تنشرها وزارات الصحة ومنظمة الصحة العالمية وجمعيات طب الأطفال، وتبيّن من أي وثيقة أُخذت كل جملة. لا تشخّص ولا تغني عن طبيب طفلك: تشرح ما تقوله الإرشادات، ومتى يجب أن يراه الطبيب، وبأي رقم طوارئ تتصل في بلدك. تعمل من دون حساب ومن دون طلب بيانات شخصية. أخبرني بما يقلقك بشأن طفلك.\n\nمن يصنعه وكيف يُموَّل: pedibot.xyz/ar/about",
    "pt": "O PediBot é um serviço gratuito que responde a dúvidas sobre a saúde das crianças usando apenas diretrizes publicadas por ministérios da saúde, pela OMS e por sociedades de pediatria, e mostra de que documento vem cada frase. Não faz diagnósticos nem substitui o seu pediatra: explica o que dizem as diretrizes, quando a criança precisa ser vista por um médico e para que número de emergência ligar no seu país. Funciona sem conta e sem pedir dados pessoais. Conte-me o que o preocupa no seu filho.\n\nQuem o faz e como é financiado: pedibot.xyz/pt/about",
    "hi": "PediBot एक मुफ़्त सेवा है जो बच्चों के स्वास्थ्य से जुड़े सवालों के जवाब सिर्फ़ स्वास्थ्य मंत्रालयों, विश्व स्वास्थ्य संगठन और बाल रोग संस्थाओं के प्रकाशित दिशानिर्देशों से देती है, और बताती है कि हर वाक्य किस दस्तावेज़ से लिया गया है। यह न तो निदान करती है और न ही आपके डॉक्टर की जगह लेती है: यह बताती है कि दिशानिर्देश क्या कहते हैं, बच्चे को कब डॉक्टर को दिखाना चाहिए और आपके देश में आपातकालीन नंबर क्या है। इसके लिए न खाता चाहिए, न कोई निजी जानकारी। बताइए, आपको अपने बच्चे के बारे में क्या चिंता है।\n\nइसे कौन बनाता है और पैसा कहाँ से आता है: pedibot.xyz/hi/about",
}
#: Cuando la pregunta es de dosis, trae el peso y NO dice qué medicamento (22-sep-2026).
#: «Mi hijo pesa 16 kg y el bote dice 100mg/5ml, ¿cuánto le toca?» se contestaba con «no tengo
#: información fiable sobre esto en mis fuentes», que es la peor respuesta posible: el padre
#: tiene el bote en la mano y sólo falta una palabra. Y adivinarla es lo único que aquí no se
#: puede hacer —100 mg/5 ml es la concentración del ibuprofeno infantil y también existe en
#: paracetamol—, así que se pregunta.
WHICH_DRUG = {
    "en": "Tell me which medicine it is — paracetamol (Calpol, Tylenol) or ibuprofen (Nurofen, "
    "Advil) — and I will work out the dose for that weight, in ml for your bottle.",
    "es": "Dime cuál de los dos es —paracetamol (Apiretal, Termalgin) o ibuprofeno (Dalsy, "
    "Junifen)— y te calculo la dosis para ese peso, en ml para tu bote.",
    "fr": "Dites-moi lequel c'est — paracétamol (Doliprane, Efferalgan) ou ibuprofène (Advil, "
    "Nurofen) — et je calcule la dose pour ce poids, en ml pour votre flacon.",
    "de": "Sagen Sie mir, welches es ist — Paracetamol (ben-u-ron) oder Ibuprofen (Nurofen) — "
    "und ich rechne die Dosis für dieses Gewicht aus, in ml für Ihre Flasche.",
    "ru": "Скажите, какое это лекарство — парацетамол или ибупрофен, — и я рассчитаю дозу для "
    "этого веса, в мл для вашего флакона.",
    "ar": "أخبرني أي دواء هو — الباراسيتامول أو الإيبوبروفين — وسأحسب الجرعة لهذا الوزن، "
    "بالمليلتر حسب زجاجتك.",
    "pt": "Diga-me qual dos dois é — paracetamol (Ben-u-ron) ou ibuprofeno (Brufen) — e calculo "
    "a dose para esse peso, em ml para o seu frasco.",
    "hi": "बताइए कौन-सी दवा है — पैरासिटामोल या आइबुप्रोफेन — और मैं उस वज़न के लिए खुराक "
    "निकाल दूँगा, आपकी बोतल के हिसाब से मिली में।",
}
#: Y cómo se reconoce esa pregunta: pide una dosis, sin nombrar ningún medicamento.
_ASKS_DOSE = re.compile(
    r"cu[áa]nt[oa]\s+(le\s+)?(doy|toca|tengo que dar|debo dar|pongo|jarabe|ml|mililitros)"
    r"|qu[ée]\s+dosis|dosis\s+(le\s+)?(doy|toca|corresponde|para)"
    r"|how (much|many ml)[^.?!]{0,30}(give|dose|syrup)|what dose"
    r"|quelle dose|combien (de )?ml|welche dosis|wie viel ml"
    r"|как[ауой]* доз|сколько (мл|давать)|كم (الجرعة|جرعة)|ما الجرعة"
    r"|कितनी (खुराक|दवा|मिली)|खुराक कितनी",
    re.I | re.U,
)


#: Cuando el padre pide el calendario de un país que no está transcrito (23-sep-2026). Antes
#: caía en el «no tengo información fiable» genérico, que no dice si falla su pregunta, su país
#: o el sitio entero — y países sin calendario hay muchos: toda América Latina menos Brasil.
NO_SCHEDULE = {
    "en": "I don't have {country}'s vaccination schedule transcribed, so I'd rather not guess: "
    "the ages and the vaccines change from one country to the next. The ones I do have are "
    "listed on the vaccines page, linked below. Your health centre or ministry has yours.",
    "es": "No tengo transcrito el calendario de vacunación de {country}, y prefiero no adivinar: "
    "las edades y las vacunas cambian de un país a otro. Los que sí tengo están en la página de "
    "vacunas, enlazada debajo. El tuyo lo tiene tu centro de salud o tu ministerio.",
    "fr": "Je n'ai pas le calendrier vaccinal de {country}, et je préfère ne pas deviner : les "
    "âges et les vaccins changent d'un pays à l'autre. Ceux que j'ai sont sur la page des "
    "vaccins, en lien ci-dessous. Le vôtre est chez votre centre de santé ou votre ministère.",
    "de": "Den Impfkalender von {country} habe ich nicht, und raten möchte ich nicht: Alter und "
    "Impfstoffe unterscheiden sich von Land zu Land. Die vorhandenen stehen auf der "
    "Impfseite, unten verlinkt. Ihren bekommen Sie bei Ihrer Praxis oder Ihrem Ministerium.",
    "ru": "У меня нет календаря прививок страны {country}, и угадывать я не буду: возраст и "
    "вакцины различаются от страны к стране. Те, что есть, собраны на странице вакцин по ссылке "
    "ниже. Ваш календарь есть в вашей поликлинике или министерстве.",
    "ar": "ليس لدي جدول التطعيمات الخاص بـ{country}، ولا أريد التخمين: الأعمار واللقاحات تختلف من "
    "بلد إلى آخر. الجداول المتوفرة في صفحة اللقاحات أسفل هذه الإجابة، وجدول بلدك لدى مركزك "
    "الصحي أو وزارتك.",
    "pt": "Não tenho o calendário de vacinação de {country} transcrito e prefiro não adivinhar: "
    "as idades e as vacinas mudam de país para país. Os que tenho estão na página de vacinas, "
    "ligada abaixo. O seu está no seu centro de saúde ou no seu ministério.",
    "hi": "मेरे पास {country} का टीकाकरण कैलेंडर नहीं है, और मैं अंदाज़ा नहीं लगाना चाहता: "
    "उम्र और टीके हर देश में अलग होते हैं। जो मेरे पास हैं वे नीचे दिए टीकों वाले पेज पर हैं। "
    "आपके देश का कैलेंडर आपके स्वास्थ्य केंद्र या मंत्रालय के पास है।",
}


#: Cuando preguntan el número de emergencias y no hay país (23-sep-2026, séptima tanda). Se
#: arregló el 20-sep para quien había elegido país; quien no lo había elegido seguía recibiendo
#: «no tengo información fiable sobre esto en mis fuentes» a la pregunta más básica que existe.
#: Sin país no hay un número, y eso no es no saber nada: están los generales, y falta un dato
#: que el padre tiene en la punta de la lengua.
NUMBER_NO_COUNTRY = {
    "en": "Tell me which country you are in and I'll give you its number. In the meantime: 112 "
    "works across the European Union, 911 in the United States and Canada, 999 in the United "
    "Kingdom and in much of Africa and Asia. All of them are on the emergency page below.",
    "es": "Dime en qué país estás y te doy el suyo. Mientras tanto: el 112 funciona en toda la "
    "Unión Europea, el 911 en Estados Unidos y Canadá, y el 999 en el Reino Unido y en buena "
    "parte de África y Asia. Están todos en la página de urgencias de aquí abajo.",
    "fr": "Dites-moi dans quel pays vous êtes et je vous donne le sien. En attendant : le 112 "
    "fonctionne dans toute l'Union européenne, le 911 aux États-Unis et au Canada, le 999 au "
    "Royaume-Uni et dans une grande partie de l'Afrique et de l'Asie. Ils sont tous sur la page "
    "des urgences ci-dessous.",
    "de": "Sagen Sie mir, in welchem Land Sie sind, dann nenne ich Ihnen die Nummer. Bis dahin: "
    "112 gilt in der ganzen EU, 911 in den USA und Kanada, 999 im Vereinigten Königreich und in "
    "weiten Teilen Afrikas und Asiens. Alle stehen auf der Notfallseite unten.",
    "ru": "Скажите, в какой вы стране, и я назову её номер. А пока: 112 действует во всём "
    "Евросоюзе, 911 — в США и Канаде, 999 — в Великобритании и во многих странах Африки и Азии. "
    "Все они есть на странице экстренной помощи ниже.",
    "ar": "أخبرني في أي بلد أنت وسأعطيك رقمه. في هذه الأثناء: 112 يعمل في كل الاتحاد الأوروبي، "
    "و911 في الولايات المتحدة وكندا، و999 في المملكة المتحدة وفي كثير من أفريقيا وآسيا. كلها في "
    "صفحة الطوارئ بالأسفل.",
    "pt": "Diga-me em que país está e dou-lhe o número. Entretanto: o 112 funciona em toda a "
    "União Europeia, o 911 nos Estados Unidos e no Canadá, e o 999 no Reino Unido e em boa parte "
    "de África e da Ásia. Estão todos na página de urgências abaixo.",
    "hi": "बताइए आप किस देश में हैं और मैं वहाँ का नंबर दे दूँगा। तब तक: 112 पूरे यूरोपीय संघ "
    "में चलता है, 911 अमेरिका और कनाडा में, और 999 ब्रिटेन तथा अफ़्रीका और एशिया के बड़े हिस्से "
    "में। सभी नीचे दिए आपातकालीन पेज पर हैं।",
}


#: Lo que no tiene nada que ver con la salud de un niño (21-sep-2026): se dice con amabilidad y
#: se invita a preguntar lo que sí. Antes caía en «no tengo información, consulta a tu pediatra»,
#: que para «¿mi perro puede comer chocolate?» es una respuesta absurda.
OFF_TOPIC = {
    "en": "That's outside what PediBot does: I only answer questions about the health of babies and children, from published paediatric guidelines. If you have one about your child, ask me.",
    "es": "Eso se sale de lo que hace PediBot: sólo contesto dudas sobre la salud de bebés y niños, con guías pediátricas publicadas. Si tienes alguna sobre tu hijo, pregúntame.",
    "fr": "Cela sort de ce que fait PediBot : je ne réponds qu'aux questions sur la santé des bébés et des enfants, à partir de recommandations pédiatriques publiées. Si vous en avez une sur votre enfant, posez-la-moi.",
    "de": "Das gehört nicht zu dem, was PediBot macht: Ich beantworte nur Fragen zur Gesundheit von Babys und Kindern, anhand veröffentlichter kinderärztlicher Leitlinien. Wenn Sie eine zu Ihrem Kind haben, fragen Sie mich.",
    "ru": "Это не входит в то, чем занимается PediBot: я отвечаю только на вопросы о здоровье малышей и детей, опираясь на опубликованные педиатрические рекомендации. Если у вас есть вопрос о ребёнке, задайте его.",
    "ar": "هذا خارج ما يقدمه PediBot: أجيب فقط عن أسئلة صحة الرضّع والأطفال، اعتمادًا على إرشادات طب الأطفال المنشورة. إن كان لديك سؤال عن طفلك، فاسألني.",
    "pt": "Isso não é o que o PediBot faz: só respondo a dúvidas sobre a saúde de bebês e crianças, com diretrizes pediátricas publicadas. Se tiver alguma sobre o seu filho, pergunte-me.",
    "hi": "यह PediBot के दायरे से बाहर है: मैं सिर्फ़ शिशुओं और बच्चों के स्वास्थ्य से जुड़े सवालों के जवाब देता हूँ, प्रकाशित बाल रोग दिशानिर्देशों के आधार पर। अगर आपके बच्चे के बारे में कोई सवाल है, तो पूछिए।",
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


#: Las lenguas que el sitio NO habla pero en las que sí contesta, con su código ISO 639-1.
#: No es una lista de idiomas soportados: es para que el registro anónimo diga la verdad sobre en
#: qué lengua escribió el padre, que es el dato que dice en cuál merece la pena crecer.
OTRAS_LENGUAS = {
    "swahili": "sw",
    "urdu": "ur",
    "bengali": "bn",
    "italian": "it",
    "polish": "pl",
    "turkish": "tr",
    "romanian": "ro",
    "ukrainian": "uk",
    "chinese": "zh",
    "mandarin": "zh",
    "japanese": "ja",
    "korean": "ko",
    "dutch": "nl",
    "greek": "el",
    "hebrew": "he",
    "persian": "fa",
    "farsi": "fa",
    "punjabi": "pa",
    "tamil": "ta",
    "telugu": "te",
    "marathi": "mr",
    "gujarati": "gu",
    "vietnamese": "vi",
    "thai": "th",
    "indonesian": "id",
    "malay": "ms",
    "tagalog": "tl",
    "filipino": "tl",
    "amharic": "am",
    "somali": "so",
    "hausa": "ha",
    "yoruba": "yo",
    "igbo": "ig",
    "zulu": "zu",
    "afrikaans": "af",
    "wolof": "wo",
    "lingala": "ln",
    "kinyarwanda": "rw",
    "nepali": "ne",
    "sinhala": "si",
    "pashto": "ps",
    "kurdish": "ku",
    "albanian": "sq",
    "serbian": "sr",
    "croatian": "hr",
    "bulgarian": "bg",
    "czech": "cs",
    "slovak": "sk",
    "hungarian": "hu",
    "swedish": "sv",
    "norwegian": "no",
    "danish": "da",
    "finnish": "fi",
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
    #: La lengua en la que se ESCRIBIÓ la respuesta, cuando no es la de búsqueda. 24-sep-2026:
    #: una consulta en suajili se buscaba en inglés —el corpus está en inglés— y se apuntaba
    #: «en» en el registro aunque la respuesta fuera en suajili. Ese campo es el único sitio
    #: donde se ve en qué lenguas escribe la gente, y decía que nadie escribía en suajili.
    wrote_in: str | None = None

    @property
    def written_lang(self) -> str:
        """El código de la lengua en la que lo lee el padre.

        Sin nada dicho, es el idioma de búsqueda. Con una lengua que el sitio no habla, su
        código ISO; y si tampoco lo conocemos, su nombre en minúsculas, que es feo pero cierto:
        un registro con «quechua» se puede contar, y uno con «en» esconde la pregunta.
        """
        if not self.wrote_in:
            return self.lang
        nombre = self.wrote_in.strip().lower()
        return OTRAS_LENGUAS.get(nombre, nombre)

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


def load_prompt(version: str = "answer_v7") -> tuple[str, str]:
    text = (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")
    return version, text


@dataclass(frozen=True)
class ToolLink:
    """A page of this site that answers the same question better than prose can.

    `kind` and not a label: the words live in i18n.ts in eight languages, and a Spanish string
    coming out of the engine would be a ninth copy waiting to drift.
    """

    kind: str  # "vaccines" | "dose" | "growth" | "emergency"
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
    elif kind == "emergency":
        # /emergency/{país} existe para los 90; sin país, el índice, que es una tabla entera
        tail = f"/emergency/{country.lower()}" if country else "/emergency"
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
            "sw": f"🚨 Piga simu {numbers['emergency']} sasa hivi au nenda hospitali.",
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
            "sw": "🚨 Kwa dalili hizi mtoto anapaswa kuonwa hospitali leo, bila kusubiri.",
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
            "sw": f"💛 Hili ni jambo muhimu na hauko peke yako. Piga simu {mental}"
            + (f" (au {also} kama kuna hatari ya papo hapo)" if also else "")
            + ". Kama mtoto tayari amejidhuru, nenda hospitali sasa.",
        }
    # 18-sep-2026. Ocho países —siete donde la fuente dice que NO existe número nacional y
    # Zambia, donde no hemos podido verificarlo— tienen ficha pero no tienen número. Las
    # plantillas de arriba lo meten en la frase sin preguntar, y `f"{None}"` es «None»: el aviso
    # decía «💛 This matters and you are not alone. Call None.» a un padre que acababa de
    # escribir que su hijo quiere morirse.
    #
    # Donde no hay número no se escribe un número. Se escribe la única instrucción que sirve
    # cuando no hay ambulancia a la que llamar: ir al hospital o centro de salud más cercano.
    # Se sustituye la tabla entera y no sólo el idioma pedido, para que el respaldo en inglés
    # tampoco nombre un número que no existe.
    if tr.level == "emergency" and not numbers.get("emergency"):
        heads = {lg: tool_strings(lg)["banner_emergency_no_number"] for lg in STRINGS}
    elif tr.level == "mental_health" and not (numbers.get("mental") or numbers.get("emergency")):
        heads = {lg: tool_strings(lg)["banner_mental_no_number"] for lg in STRINGS}
    head = heads.get(lang, heads["en"])
    why = {
        "es": "Motivo",
        "fr": "Raison",
        "de": "Grund",
        "ru": "Причина",
        "ar": "السبب",
        "pt": "Motivo",
        "hi": "कारण",
        "sw": "Sababu",
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


def brand_in_query(query: str, drugs: DrugCatalog | None) -> tuple[str, object] | None:
    """(molécula, marca) de lo que el padre ha escrito, si el catálogo lo conoce.

    Devuelve las dos cosas y no sólo la marca **a propósito**: Dalsy es ibuprofeno y el
    paracetamol tiene una presentación con su misma concentración, así que sin la molécula al
    lado se puede acabar poniendo el nombre de un bote encima de la fila de otro fármaco.

    Mismo barrido por espacios que `dose_intent`, por el mismo motivo: `\\w` parte el devanagari
    en trozos de una letra. Devuelve la marca, no la molécula: la molécula ya la saca la otra.
    """
    if drugs is None:
        return None
    for tok in (query or "").lower().translate(_A_ESPACIO).split():
        if len(tok) < 4:
            continue
        r = drugs.resolve(tok)
        if r and r[1] is not None:
            return (r[0], r[1])
    return None


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


#: Lenguas que ya se escriben en alfabeto latino: a ésas no hay que pedirles nada. Se comparan
#: por el nombre en inglés, que es como el redactor recibe la lengua.
ESCRITURA_LATINA = frozenset(
    {
        "Spanish",
        "English",
        "French",
        "German",
        "Portuguese",
        "Italian",
        "Dutch",
        "Polish",
        "Romanian",
        "Swahili",
        "Catalan",
        "Galician",
        "Basque",
        "Turkish",
        "Indonesian",
        "Malay",
        "Vietnamese",
        "Swedish",
        "Norwegian",
        "Danish",
        "Finnish",
        "Icelandic",
        "Czech",
        "Slovak",
        "Hungarian",
        "Croatian",
        "Slovenian",
        "Estonian",
        "Latvian",
        "Lithuanian",
        "Albanian",
        "Filipino",
        "Tagalog",
        "Somali",
        "Hausa",
        "Yoruba",
        "Igbo",
        "Zulu",
        "Xhosa",
        "Afrikaans",
        "Quechua",
        "Guarani",
    }
)


def instruccion_de_alfabeto(sistema: str, idioma: str, latino: bool) -> str:
    """La instrucción de traducir, con el alfabeto del padre dentro cuando hace falta.

    24-sep-2026. El redactor sabe desde L231 que a quien escribe «bukhar hai» hay que
    contestarle en alfabeto latino. La coletilla del final no lo sabía: en las lenguas que el
    sitio no habla se traduce con el modelo, y a «tradúcelo al urdu» contesta en nastaliq. La
    respuesta salía en urdu latino y remataba con una línea que ese padre puede no leer.

    A una lengua que ya se escribe en latino no se le dice nada: sería ruido en el prompt.
    """
    if not latino or idioma in ESCRITURA_LATINA:
        return sistema
    return (
        sistema + " The reader wrote in the Latin alphabet, so write the translation in the Latin "
        "alphabet too, even if this language is normally written in another script."
    )


def escritura_latina(texto: str) -> bool:
    """¿El padre escribió en alfabeto latino?

    23-sep-2026, séptima tanda: «bachay ko bukhar hai aur doodh kam pee raha hai» recibió la
    respuesta en urdu **en escritura árabe**, y «bukhar hai lekin thermometer nahi funciona» en
    devanagari. Media India y medio Pakistán escriben su lengua en teclado latino — la tabla de
    sinónimos tiene las formas romanizadas desde agosto — y quien escribe «bukhar» con letras
    latinas puede no leer nastaliq.

    Se cuentan las letras, no las palabras: una palabra inglesa dentro de una frase en devanagari
    no la vuelve latina, y una palabra urdu dentro de una frase inglesa tampoco al revés.
    """
    latinas = otras = 0
    for c in texto or "":
        if not c.isalpha():
            continue
        if "a" <= c.lower() <= "z" or "\u00c0" <= c <= "\u024f":
            latinas += 1
        else:
            otras += 1
    return latinas > otras


#: Cuando la pregunta dice, con todas las letras, que no es sobre un niño (23-sep-2026, octava
#: tanda). «Tengo fiebre, pero la pregunta es sobre mí, no sobre mi hijo» recibió la respuesta
#: de la fiebre infantil, empezando por «si el niño tiene menos de 3 meses». Y «mi perro tiene
#: diarrea» acabó en «no tengo información fiable en mis fuentes», que para un perro es absurdo.
#:
#: Pide una marca EXPLÍCITA. Un padre que escribe «tengo un bebé con fiebre» o «me preocupa mi
#: hija» no está hablando de sí mismo, y ésos no se tocan.
_NO_ES_UN_NINO = re.compile(
    r"(?:la (?:pregunta|consulta|duda) es (?:sobre|para) m[íi]|es para m[íi] |para m[íi], no)"
    r"|no (?:es )?(?:sobre|para) (?:mi|el|la) (?:hijo|hija|ni[ñn][oa]|beb[ée])"
    r"|soy yo (?:el|la) que"
    r"|\bmi (?:perro|perra|gato|gata|mascota|conejo|h[áa]mster|loro)\b"
    r"|(?:my|our) (?:dog|cat|pet)\b"
    r"|(?:the )?question is about me\b|it'?s for me, not",
    re.I | re.U,
)


def no_es_un_nino(texto: str) -> bool:
    """¿El propio texto dice que no pregunta por un niño?"""
    return bool(_NO_ES_UN_NINO.search(texto or ""))


def _mentions_child(text: str) -> bool:
    return bool(_CHILD.search(text))


#: Lo que dice que el niño no es un lactante aunque no dé la edad (21-sep-2026). «Mi hijo tiene
#: 39.8 pero está jugando», «my toddler has a fever», «bebé 8m 39 fiebre»: las tres empezaban por
#: «si tiene menos de 3 meses, que lo vea un médico hoy», que a ese padre no le dice nada.
_PARECE_MAYOR = re.compile(
    r"toddler|preschool|school|\bcole\b|colegio|guarder[ií]a|kindergarten|[ée]cole|creche|"
    r"corr(e|iendo|eteando)|running around|runs? around|jugando|juega|playing|spielt|joue|"
    r"brinca|camina|anda ya|walks|walking|\b\d{1,2}\s*(años|years?|ans|jahre?|anos|anni)\b|"
    # el niño que habla no es un lactante: «me ha dicho que quiere ver dibujos», «says it hurts»
    r"me ha dicho|me dice|dice que|se queja|says|told me|complains|sagt|dit qu|diz que|"
    r"\b([3-9]|1[0-9]|2[0-4])\s?m\b(?!\s*(de altura|etro))",
    re.I,
)


def _age_context(tr: TriageResult, texto: str = "") -> str:
    """Age line for the prompt. Under 3 months: home medication advice is never appropriate."""
    if tr.age_months is None and not tr.has_fever:
        return "CHILD AGE: unknown\n"
    if tr.age_months is None and _PARECE_MAYOR.search(texto):
        return (
            "CHILD AGE: not given, but the message shows the child is not a young baby. Do NOT "
            "mention babies under 3 months. Give NO specific medication dose (no mg, no ml).\n"
        )
    if tr.age_months is None:
        # Sólo con fiebre. Del 12 al 13-sep-2026 esta orden iba en toda respuesta sin edad y el
        # modelo la obedecía: el queroseno o el escozor al orinar abrían hablando de fiebre.
        return (
            "CHILD AGE: unknown. Open with ONE sentence: if the child is under 3 months old, a "
            "fever needs a doctor the same day. Then answer for an older child. Give NO specific "
            "medication dose (no mg, no ml): the dose depends on the age and weight you do not "
            "have.\n"
        )
    if tr.age_months < 3 and (tr.has_fever or tr.level != "routine"):
        return (
            f"CHILD AGE: {tr.age_months:g} months — UNDER 3 MONTHS. Do NOT suggest giving any "
            "medication at home (no paracetamol, no ibuprofen); do not describe home management "
            "of fever. Say that babies this young must be assessed by a doctor the same day and "
            "keep the answer short.\n"
        )
    if tr.age_months < 3:
        # 21-sep-2026: «mi bebé de 2 semanas estornuda mucho pero no tiene mocos» recibía «que lo
        # vea un médico hoy mismo». Sin fiebre ni alarma, lo de «hoy» sobra y asusta.
        return (
            f"CHILD AGE: {tr.age_months:g} months — UNDER 3 MONTHS. Do NOT suggest giving any "
            "medication at home. Answer what was asked; if a source says when a baby this young "
            "should see a doctor, say it.\n"
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


#: El texto negando tener un número de urgencias, en las ocho lenguas. El aviso de arriba SÍ
#: lo tiene —es nuestro, sale de la tabla de 90 países y va en el idioma del lector—, así que
#: una frase así no es humildad: es una contradicción dentro de la misma pantalla, y encima le
#: cuenta al padre cómo funciona esto por dentro. Visto en vivo el 20-sep-2026 con Nigeria y
#: un niño atragantado.
NIEGA_NUMERO = re.compile(
    r"(?:can'?t|cannot|unable to|am not able to)[^.]{0,40}(?:give|provide|tell)[^.]{0,30}(?:emergency|number)"
    r"|(?:no puedo|no me es posible)[^.]{0,40}(?:dar|darte|proporcionar)[^.]{0,30}(?:número|numero)"
    r"|(?:je ne peux pas|je ne suis pas en mesure)[^.]{0,40}(?:donner|fournir)[^.]{0,30}num[ée]ro"
    r"|(?:kann ich|ich kann)[^.]{0,40}(?:keine|nicht)[^.]{0,30}(?:Notrufnummer|Nummer)"
    r"|(?:не могу)[^.]{0,40}(?:дать|сообщить)[^.]{0,30}(?:номер)"
    r"|(?:لا أستطيع|لا يمكنني)[^.]{0,40}(?:إعطاء|تقديم)[^.]{0,30}(?:رقم)"
    r"|(?:não posso|não consigo)[^.]{0,40}(?:dar|fornecer)[^.]{0,30}(?:número|numero)"
    r"|my sources only (?:mention|cover|include)[^.]{0,40}(?:number|country)"
    r"|(?:mis|las) fuentes s[óo]lo (?:mencionan|cubren)[^.]{0,40}(?:n[úu]mero|pa[íi]s)",
    re.I,
)


def denies_the_number_problem(text: str) -> str | None:
    """El mensaje de rechazo para un texto que niega lo que el aviso de arriba ya dice."""
    m = NIEGA_NUMERO.search(text)
    if not m:
        return None
    return (
        f"denies_the_number ({m.group(0)!r}): the banner above your text already carries the"
        " reader's own emergency number. Never write that you cannot give one, or that your"
        " sources only cover one country. Say nothing about numbers: write what the sources"
        " say to do while help arrives."
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


#: El padre no necesita oír hablar de «las fuentes» (21-sep-2026). La regla 15 del prompt lo
#: pide y el modelo lo seguía haciendo en 17 de 260 respuestas, casi siempre en la forma «no hay
#: información en las fuentes sobre X; lo que sí describen es Y», con Y de otra cosa. Es de
#: estilo, no de seguridad: da un reintento con la nota concreta, nunca manda al «no sé».
_HABLA_DE_FUENTES = re.compile(
    r"\b(las fuentes|mis fuentes|estas fuentes|the sources|my sources|these sources|les sources|"
    r"mes sources|die quellen|meinen quellen|as fontes|nas fontes|minhas fontes|"
    r"la informaci[oó]n (que tengo|de la que dispongo|disponible)|the information i have|"
    r"lo que s[ií] (describen|dicen|indican)|what the sources|ning[uú]n (pasaje|documento|dato)|"
    r"no (passage|document))\b",
    re.I,
)


#: Una primera frase que dice que lo preguntado no está cubierto. Si sobrevive al reintento, la
#: respuesta entera es relleno de otra cosa (ver el final del bucle de redacción).
_EMPIEZA_SIN_INFO = re.compile(
    r"(no hay (ning[uú]n dato|informaci[oó]n|nada)|no encuentro|no aparece(n)? (descrit|en)|"
    r"ninguna de las fuentes|informaci[oó]n disponible|ning[uú]n (pasaje|documento|dato)|"
    r"there is no information|none of the (information|sources)|is not (something|described|covered)|"
    r"the sources (do not|don'?t)|information here|"
    r"il n'y a pas d'information|aucune (des )?information|"
    r"keine (informationen|angaben)|n[ãa]o h[áa] informa[çc][ãa]o|нет (информации|данных))",
    re.I,
)


def _primera_frase(texto: str) -> str:
    return re.split(r"(?<=[.!?])\s", texto.strip(), maxsplit=1)[0]


#: Con un aviso urgente o de emergencia encima, el texto no puede decir que no es urgente. «Mi
#: hija se ha metido arena en el ojo»: cartel de urgencias y, debajo, «No, no es una urgencia por
#: sí solo» (batería del 21-sep-2026). Es de SEGURIDAD: si el reintento lo repite, no sale.
_QUITA_URGENCIA = re.compile(
    r"(no es (una )?urgen|no es grave|no es (una (dosis|cantidad) )?peligros|no (hay|supone) (ning[uú]n )?peligro|"
    r"(is )?not (a )?dangerous|isn'?t (a )?dangerous|not harmful|n'est pas dangereu|nicht gef[äa]hrlich|"
    r"n[ãa]o [ée] perigos|не опасн|no hace falta (ir|acudir)|no es una emergencia|"
    r"(is )?not (an )?(urgent|emergency)|no need to (go|rush|worry)|isn'?t (urgent|an emergency)|"
    r"(ce )?n'est pas (une )?urgen|kein notfall|nicht dringend|n[ãa]o [ée] (uma )?urg[êe]n|"
    # 23-sep-2026, séptima tanda: dos respuestas con el cartel rojo encima empezaban por
    # «No es una dificultad para respirar» y «no aparece como signo de alarma». Ninguna dice
    # «no es urgente»; dicen que el signo por el que saltó el aviso no es un signo, que es
    # peor, porque suena a explicación.
    r"no (es|son) (una? )?(dificultad|signo|se[ñn]al|motivo)|no (aparece|figura|est[áa])[^.]{0,25}(como )?(signo|se[ñn]al|motivo) de (alarma|consulta)|no (es|son) (un |una )?(signo|se[ñn]al)[^.]{0,20}(de alarma|preocupante|grave)|no (es|hay) motivo de (alarma|consulta|preocupaci[óo]n)|(is|are) not (a |an )?(warning sign|sign of|cause for)|(n'est pas|ne sont pas) (un |une )?(signe|motif)|kein (warnzeichen|alarmzeichen)|не (является )?(признак\\w*|тревожн\\w*)|не (срочно|экстренн)|ليست? (حالة )?طارئ|आपातकाल नहीं|(es|son|esto es|eso es) (algo )?(normal|habitual|frecuente|lo normal)(?![^.]{0,80}(pero|aun as[íi]|de todas formas|hay que acudir|hay que ir))|no hay (ning[uú]n )?(motivo|raz[oó]n) (de|para) (alarma|preocupaci[oó]n)|no hay (ning[uú]n )?problema|no hay ingesti[oó]n|no ha pasado nada|(is|are) normal (in|for) (babies|children|infants)|(this|that) is normal\b(?![^.]{0,80}(but|still|even so))|(there is|there's) no (cause|reason) for (alarm|concern|worry)|nothing to worry about|c'est normal(?![^.]{0,80}(mais|quand m[êe]me))|il n'y a pas lieu de s'inqui[ée]ter|(das )?ist normal(?![^.]{0,80}(aber|trotzdem))|kein grund zur sorge|это нормальн\w*(?![^.]{0,80}(но|всё же))|нет повода для беспокойств)",
    re.I,
)
CONTRADICE_AVISO = (
    "contradicts_the_warning: a warning above your text already tells the parent this needs to"
    " be seen now; never write that it is not urgent or not an emergency"
)


def _insegura(texto: str, hits: list[Hit], alarma: bool) -> list[str]:
    """Los problemas de SEGURIDAD de un borrador: `verify`, más no contradecir el aviso."""
    problemas = verify(texto, hits)
    if alarma and _QUITA_URGENCIA.search(texto):
        problemas.append(CONTRADICE_AVISO)
    return problemas


REVISA = """You review one answer from a children's health chatbot before a parent sees it. The
chatbot must answer only from cited guidelines. You get the parent's MESSAGE, the WARNING LEVEL it
showed, and the ANSWER. Return ONLY a JSON object:
  "answers_question": false only if the answer is about something other than what the parent
      asked or described (another symptom, another age group, another situation),
  "padding": true if a sizeable part talks about a different condition than the parent's,
  "invented_verdict": true if it states a verdict ("it's normal", "no problem", "yes you can",
      "it is not serious") that none of its cited sentences supports,
  "note": one short English sentence telling the writer exactly what to fix, or "".
Be strict about relevance and verdicts, and do not complain about length, tone or style."""


@dataclass(frozen=True)
class Revision:
    contesta: bool
    relleno: bool
    veredicto: bool
    nota_en: str
    coste: tuple[int, int, float]

    @property
    def hay_que_rehacer(self) -> bool:
        return (not self.contesta) or self.relleno or self.veredicto


def revisa_respuesta(llm: object, pregunta: str, nivel: str, texto: str) -> Revision | None:
    """La lectura de revisión. `None` si no hay modelo o contesta algo que no se puede leer:
    entonces la respuesta sale como estaba, nunca peor."""
    if llm is None or not texto.strip():
        return None
    try:
        r = llm.complete(  # type: ignore[attr-defined]
            REVISA,
            f"MESSAGE:\n{pregunta[:1500]}\n\nWARNING LEVEL: {nivel}\n\nANSWER:\n{texto[:2500]}",
            temperature=0.0,
            max_tokens=200,
        )
    except Exception:  # noqa: BLE001 — sin revisión, la respuesta tal cual
        return None
    m = re.search(r"\{.*\}", getattr(r, "text", "") or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(d, dict):
        return None
    nota = d.get("note") if isinstance(d.get("note"), str) else ""
    return Revision(
        contesta=d.get("answers_question") is not False,
        relleno=d.get("padding") is True,
        veredicto=d.get("invented_verdict") is True,
        nota_en=(nota or "Answer only what the sources say about the parent's exact question.")[
            :300
        ],
        coste=(
            int(getattr(r, "tokens_in", 0) or 0),
            int(getattr(r, "tokens_out", 0) or 0),
            float(getattr(r, "cost_usd", 0.0) or 0.0),
        ),
    )


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
    niega = denies_the_number_problem(text)
    if niega:
        problems.append(niega)
    counts = _org_mentions(text, hits)
    if not names_a_source(text, hits):
        problems.append(
            "no_organisation_named: name the organisation in words the first time you use a"
            " source (SEUP, NHS, WHO, CDC, MedlinePlus…), with the fact first"
        )
    if _HABLA_DE_FUENTES.search(text) or _EMPIEZA_SIN_INFO.search(_primera_frase(text)):
        problems.append(
            "talks_about_the_sources: do not tell the parent what 'the sources' do or do not say,"
            " and do not add material about a different situation. Answer with what the"
            " organisations say about THIS situation, naming them; if nothing covers it, reply"
            " NO_SOURCE"
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
        prompt_version: str = "answer_v7",
        drugs: DrugCatalog | None = None,
        vaccines: Vaccines | None = None,
        guides: GuideIndex | None = None,
        growth: Growth | None = None,
    ):
        self.retriever = retriever
        self.triage = triage
        self.llm = llm
        self.numbers = numbers
        self.prompt_version, self.prompt = load_prompt(prompt_version)
        self.drugs = drugs
        self.vaccines = vaccines
        self.guides = guides
        self.growth = growth
        self._ficha: str | None = None

    def ficha_sobre_pedibot(self) -> str:
        """La ficha de hechos del servicio, con los números del sistema que está corriendo.

        No se escriben a mano en la ficha: un número escrito a mano envejece mal, y esta ficha
        se le enseña al padre como si fuera cierta. Se cuentan una vez y se guardan.
        """
        if self._ficha is None:
            try:
                docs = self.retriever.index.documents()
            except Exception:  # noqa: BLE001 — un número que falta no impide contestar
                docs = 0
            self._ficha = ficha_de(
                docs=docs,
                rules=len(self.triage.rules),
                countries=len([k for k in self.numbers.raw if k != "default"]),
                vax=len(self.vaccines.countries) if self.vaccines is not None else 0,
            )
        return self._ficha

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
        Only the last MAX_TURNS are used (PRD §5.4).

        21-sep-2026: una envoltura sobre `_ask`, por dos cosas que tienen que pasar pase lo que
        pase dentro. Una, que **la respuesta salga en la lengua en que escribió el padre** —«eso es
        básico», dicho por el operador con el panel delante—, también cuando lo que se devuelve es
        una frase fija nuestra y el padre escribe en una lengua que el sitio no tiene. Y dos, que
        lo que cuesta leer la pregunta y traducir esas frases se sume al gasto de la respuesta,
        porque el tope diario de gasto mira ese número. `ctx` es de cada llamada y no del motor:
        la API atiende varias a la vez desde hilos distintos.
        """
        ctx: dict = {"costes": [], "fuera": None}
        a = self._ask(query, country, lang, history, mode, ctx)
        # Con un aviso rojo encima, «prefiero no adivinar, consulta con tu pediatra» debajo le
        # quita fuerza al aviso justo cuando más importa: «pierde el conocimiento», «le ha dado
        # la corriente», «lleva media hora sin responder» salían así (batería del 21-sep-2026).
        # Si no hay fuente que añadir, el texto sólo apoya el aviso.
        if (
            a.banner
            and a.level in ("urgent", "emergency")
            and a.verification in ("no_source", "fallback")
        ):
            a.text = SIGUE_EL_AVISO.get(a.lang, SIGUE_EL_AVISO["en"])
        if ctx["fuera"] and a.verification in _FRASES_FIJAS:
            a.text = self._traduce(a.text, ctx["fuera"], ctx)
        if ctx["costes"]:
            ti = sum(c[0] for c in ctx["costes"])
            to = sum(c[1] for c in ctx["costes"])
            usd = sum(c[2] for c in ctx["costes"])
            if a.llm is None:
                a.llm = LLMResult("", ti, to, usd, "interpret")
            else:
                a.llm.tokens_in += ti
                a.llm.tokens_out += to
                a.llm.cost_usd += usd
        return a

    def _traduce(self, texto: str, idioma: str, ctx: dict, latino: bool = False) -> str:
        """Una frase FIJA nuestra a una lengua que el sitio no tiene, o la frase tal cual.

        Sólo pasan por aquí las que no llevan contenido médico nuevo ni cifras —«no tengo
        información fiable», «¿qué edad tiene?»—. Lo que lleva una dosis, un calendario o un
        número de teléfono **no se traduce nunca con el modelo**, y por si acaso: si la traducción
        trae una sola cifra distinta de las del original, se tira y se devuelve el original.
        """
        if self.llm is None or not texto.strip():
            return texto
        try:
            r = self.llm.complete(
                instruccion_de_alfabeto(TRADUCE, idioma, latino),
                f"LANGUAGE: {idioma}\n\n{texto}",
                temperature=0.0,
                max_tokens=500,
            )
        except Exception:  # noqa: BLE001 — sin traducción, la frase en inglés es mejor que nada
            return texto
        ctx["costes"].append((r.tokens_in, r.tokens_out, r.cost_usd))
        out = (r.text or "").strip()
        if not out or sorted(re.findall(r"\d+", out)) != sorted(re.findall(r"\d+", texto)):
            return texto
        return out

    def _ask(
        self,
        query: str,
        country: str | None,
        lang: str | None,
        history: list[dict[str, str]] | None,
        mode: str,
        ctx: dict,
    ) -> Answer:
        history = (history or [])[-MAX_TURNS:]
        prior_user = " ".join(t["text"] for t in history if t.get("role") == "user")
        context_text = f"{prior_user} {query}".strip() if prior_user else query
        lang = lang or detect_lang(query)
        # Una IA lee la pregunta antes que nada (21-sep-2026, ver `interpret`). El idioma venía
        # de la web y no del texto: un padre con la web en inglés que escribía en italiano
        # recibía inglés. Y la detección por palabras fallaba justo en las lenguas que no
        # tenemos: el italiano salía como español, el holandés como inglés, el polaco como
        # francés. Si escribe en una de las ocho, todo pasa a esa: avisos, herramientas y textos
        # fijos. Si escribe en otra, se le redacta en la suya y las frases fijas se traducen.
        # Tres palabras como mínimo para cambiar de idioma: «Dalsy 5 ml?» no dice nada de nadie.
        # todo lo que el padre ha dicho antes, no sólo el último mensaje: entre la caída y el bebé
        # que lloraba, el operador mandó un «Mi» suelto, y comparado con «Mi» nada es tema nuevo
        anterior = " / ".join(t["text"] for t in history if t.get("role") == "user") or None
        # «Otra cosa» es un botón nuestro, no una frase del padre: no se le pide opinión a la IA.
        # Salió una vez en inglés, y es la única respuesta de la conversación que ya sabemos.
        boton = (
            query.strip().lower()
            == CLARIFY_OPTIONS.get(lang, CLARIFY_OPTIONS["en"])[-1].strip().lower()
        )
        leida = None if boton else interpret(self.llm, query, previous=anterior)
        largo = len(query.split()) >= 3
        if leida is not None:
            ctx["costes"].append((leida.tokens_in, leida.tokens_out, leida.cost_usd))
            # Otro problema, conversación nueva (21-sep-2026). El operador hizo diez preguntas
            # seguidas, cada una de una cosa, y se fueron sumando: el bebé que lloraba salió con
            # «vómitos tras un golpe en la cabeza» porque el golpe era de la pregunta anterior, y
            # los ojos rojos heredaron sus dos meses. Sólo con un «sí» explícito de la lectura: si
            # no lo sabe, se junta como siempre, porque el meningococo se cuenta en dos frases.
            # «Puedes escribir en italiano» no es otro problema: es el mismo, en otra lengua.
            if leida.new_topic and leida.intent != "language_request":
                history, prior_user, context_text = [], "", query
            if leida.intent == "language_request":
                # Quien pide «Puoi scrivere in italiano?» lo pide en italiano: si la lectura no
                # dice qué lengua quiere, es la del mensaje. Se quedaba en inglés por eso.
                # Con menos de tres palabras, sólo si nombra la lengua: dos palabras no dicen
                # en qué idioma escribe nadie, y la web ya sabe cuál tiene puesta.
                pedida = leida.requested_lang or (leida.lang if largo else None)
                nombre = leida.requested_name or (leida.lang_name if largo else None)
                if pedida in SUPPORTED_LANGS:
                    lang = pedida
                elif nombre:
                    ctx["fuera"] = nombre
            elif largo and leida.lang in SUPPORTED_LANGS and leida.lang != lang:
                lang = leida.lang
            elif largo and leida.lang not in SUPPORTED_LANGS and leida.lang_name:
                ctx["fuera"] = leida.lang_name
        # El idioma del AVISO y el de la RESPUESTA pueden ser distintos, y con el suajili lo
        # son: el triaje lo lee y lo escribe, el corpus todavía no. Al padre se le da el aviso
        # rojo en su lengua —que es la parte que dice qué hacer— y la explicación en inglés,
        # con fuentes que puede abrir, en vez de un suajili sin nada detrás que citar.
        lang_aviso = lang if lang in TRIAGE_LANGS else "en"
        if leida is not None and largo and leida.intent != "language_request":
            if leida.lang in TRIAGE_LANGS:
                lang_aviso = leida.lang
        if lang not in SUPPORTED_LANGS:
            lang = "en"
        # El triaje no sabe italiano, ni holandés, ni polaco. «Mio figlio di 2 anni non respira
        # bene e ha le labbra blu» no sacaba el cartel rojo (21-sep-2026): la respuesta redactada
        # sí decía que había que llamar ya, pero sin el aviso ni el número. Si el padre escribe
        # en una lengua que el triaje no lee, se le pasa además la frase que la IA ha traducido
        # al inglés. Se SUMA al original, no lo sustituye: así sólo puede añadir alarmas, nunca
        # quitarlas, y una alarma de más es mucho menos grave que una de menos. El cartel sale
        # en inglés con el número del país, que el modelo no toca nunca.
        traducida = (
            f" {leida.query_en}"
            if leida is not None and leida.lang not in TRIAGE_LANGS and leida.query_en
            else ""
        )
        tr = self.triage.assess(context_text + traducida)
        tr_now = self.triage.assess(query + traducida)
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
        nums = self.numbers.get(country, lang_aviso)
        banner = build_banner(tr, lang_aviso, nums)

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
            # La marca que el padre ha escrito, para poner SU bote el primero. El catálogo ya la
            # resolvía para elegir la molécula y el dato se tiraba (20-sep-2026).
            encontrada = brand_in_query(query, self.drugs) or brand_in_query(
                context_text, self.drugs
            )
            clave, marca = encontrada if encontrada else (None, None)
            text = format_result(
                calculate(drug, kg, tr.age_months),
                lang,
                brand=marca,
                brand_key=clave,
                country_forms=bottles_in_country(self.drugs, drug, country),
                country_name=country_name(country.upper(), lang) if country else None,
            )
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

        # Pide una dosis, da el peso y no dice de qué: falta una palabra y la tiene él.
        if (
            tr.level == "routine"
            and intent is None
            and _WEIGHT.search(query)
            and _ASKS_DOSE.search(query)
            and not _DRUG.search(query)
            and not (
                self.drugs
                and any(
                    self.drugs.resolve(x)
                    for x in query.lower().translate(_A_ESPACIO).split()
                    if len(x) >= 4
                )
            )
        ):
            return Answer(
                WHICH_DRUG[lang],
                tr.level,
                None,
                [],
                lang,
                None,
                None,
                [],
                "which_drug",
                tool=tool_link("dose", lang),
            )

        # El número de urgencias, de la tabla y no del corpus (20-sep-2026). Probado en vivo:
        # un padre en Nigeria preguntaba el número y el chat contestaba «no tengo información
        # fiable sobre esto en mis fuentes» mientras el aviso de arriba llevaba el 112 escrito.
        # Teníamos el dato de 90 países, comprobado uno a uno, y la pregunta más básica de todas
        # se iba a buscar un pasaje que no existe.
        if tr.level == "routine" and is_emergency_number_question(context_text):
            cc = (country or "").upper() or (country_in_question(context_text) or "").upper()
            datos = self.numbers.raw.get(cc) if cc else None
            if not datos:
                # sin país no hay un número suyo, y eso no es no saber nada
                return Answer(
                    NUMBER_NO_COUNTRY[lang],
                    tr.level,
                    None,
                    [],
                    lang,
                    None,
                    None,
                    [],
                    "emergency_number",
                    tool=tool_link("emergency", lang, None),
                )
            if datos:
                return Answer(
                    format_numbers(dict(datos), country_name(cc, lang), lang),
                    tr.level,
                    None,
                    [],
                    lang,
                    None,
                    None,
                    [],
                    "emergency_number",
                    tool=tool_link("emergency", lang, cc),
                )
            # sin país elegido no se adivina: se cae al corpus, que dirá que no lo sabe

        if self.vaccines is not None and tr.level == "routine" and is_vaccine_question(query):
            # "Quels vaccins pour un bébé de 3 mois EN FRANCE ?" used to fall through to the
            # corpus and come back as "I have no reliable information", with the country sitting
            # in the sentence the whole time. Read only when the reader picked none, and only a
            # name they wrote themselves — never inferred from the language.
            # 23-sep-2026, del registro: «cual es el calendario de vacunas CHILENO» devolvió el
            # de España, porque el selector iba primero y Chile no se reconocía. Escribir el
            # país es lo más explícito que hace un padre: manda sobre lo que eligió en la
            # pantalla. Y si ese país no está entre los transcritos, no se le sirve el de al
            # lado: se sigue al corpus, que dirá lo que tenga o que no tiene nada.
            escrito = country_in_question(context_text)
            # el país escrito manda, pero sólo cuando lo que se pide es un calendario: «una
            # reacción a una vacuna que recibió en Francia» no es pedir el calendario francés
            if escrito is not None and pide_calendario(context_text):
                c = self.vaccines.resolve_country(escrito)
            elif escrito is not None and not pide_calendario(context_text):
                c = None
                escrito = None
            else:
                c = self.vaccines.resolve_country(country)
            if c is None and escrito is not None:
                # nombró un país y no lo tenemos: se dice cuál falta, no «no tengo información»
                return Answer(
                    NO_SCHEDULE[lang].format(country=country_name(escrito, lang)),
                    tr.level,
                    None,
                    [],
                    lang,
                    None,
                    None,
                    [],
                    "no_schedule",
                    tool=tool_link("vaccines", lang, None),
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

        # La cinta del brazo (20-sep-2026). Donde va este proyecto no siempre hay báscula: hay
        # una cinta de papel, y la mide un agente comunitario o la propia madre. Es el método
        # que la OMS recomienda para cribar en la comunidad, y aquí no estaba.
        #
        # Va ANTES de la curva a propósito: «el brazo le mide 11 cm» trae una medida en
        # centímetros, y la curva la leería como una talla de 11 cm, que no existe.
        if is_muac_question(query):
            mm = read_mm(query)
            edad_muac = tr_now.age_months if tr_now.age_months is not None else tr.age_months
            lectura = muac_assess(mm, edad_muac) if mm is not None else None
            if lectura is not None:
                # El aviso se construye con la CINTA como hallazgo, no con el triaje: el
                # mensaje del padre no trae ningún síntoma de alarma, trae una medida, así que
                # `build_banner(tr, …)` devolvía None y una respuesta marcada como urgente salía
                # sin el recuadro rojo, que es lo primero que se mira (20-sep-2026).
                aviso = TriageResult(
                    level=lectura.level,
                    matched=[],
                    age_months=tr.age_months,
                    has_fever=tr.has_fever,
                    reasons_override=[muac_reason(lectura, lang_aviso)],
                )
                return Answer(
                    muac_explain(lectura, lang),
                    lectura.level,
                    build_banner(aviso, lang_aviso, nums),
                    [],
                    lang,
                    None,
                    None,
                    [],
                    "muac",
                    tool=tool_link("growth", lang, country or country_in_question(context_text)),
                )

        # La curva de la OMS, calculada aquí y no descrita (16-sep-2026). Hasta hoy el chat
        # contestaba «no puedo decirte el percentil exacto» teniendo delante el sexo, la edad y el
        # peso, y la tabla en el mismo servidor. Hacen falta las tres cosas: sin SEXO no hay curva
        # (la de una niña no es la de un niño) y sin edad no hay fila que mirar. Y la pregunta
        # tiene que ser de crecimiento: «pesa 7 kg y tiene fiebre» no es un percentil.
        if (
            self.growth is not None
            and tr.level == "routine"
            and (
                is_growth_question(context_text)
                or gives_both_measurements(query)
                # 20-sep-2026: «pesa 8 kg, ¿está bien?» es esta pregunta, y es como se
                # hace de verdad. La puerta pedía la palabra «percentil» o las dos
                # medidas, y un keniano con un hijo de 18 meses y 8 kilos —por debajo
                # del percentil 3— recibía «no puedo saberlo con el peso solo».
                or asks_if_a_measure_is_normal(query)
            )
        ):
            # **El peso y la talla salen de UN SOLO mensaje.** Leyendo la conversación entera se
            # cruzaban los datos de dos niños, y eso lo vi dos veces probando contra lo vivo: «mi
            # niña de 8 meses que pesa 7 kg» seguido de «mi niño de 3 años que pesa 13 kg y mide
            # 92 cm» daba 7 kg para 92 cm, o sea un aviso de desnutrición aguda grave a un niño
            # sano. Vale el mensaje de ahora; si hoy no trae ninguna medida, el último que trajera
            # alguna, con las dos de ese mismo mensaje. El sexo y la edad sí son contexto: no
            # cambian de un turno a otro, y son justo lo que el padre cuenta en la frase anterior.
            sexo, peso, talla = measurements(query)
            edad = tr_now.age_months
            previos = [t["text"] for t in history if t.get("role") == "user"]
            if peso is None and talla is None:
                for texto in reversed(previos):
                    s_ant, p_ant, t_ant = measurements(texto)
                    if p_ant is not None or t_ant is not None:
                        peso, talla = p_ant, t_ant
                        sexo = sexo or s_ant
                        break
            if sexo is None:
                sexo = next((s for s in (measurements(t)[0] for t in reversed(previos)) if s), None)
            if edad is None:
                edad = tr.age_months
            if sexo and edad is not None and (peso is not None or talla is not None):
                try:
                    valoracion = self.growth.assess(sexo, edad, weight_kg=peso, height_cm=talla)
                except ValueError:
                    valoracion = None  # fuera de rango: lo dicen las fichas, no una excepción
                if valoracion is not None and valoracion.indicators:
                    return Answer(
                        explain(valoracion, lang, sexo, edad),
                        valoracion.level,
                        None,
                        [],
                        lang,
                        None,
                        None,
                        [],
                        "growth_chart",
                        tool=tool_link(
                            "growth", lang, country or country_in_question(context_text)
                        ),
                    )

        # el botón «otra cosa», que ofrecemos nosotros y no es un síntoma. Se compara con la
        # lista que le acabamos de enseñar, en su idioma, para no confundirlo con una pregunta
        # de verdad que empiece igual.
        if query.strip().lower() == CLARIFY_OPTIONS[lang][-1].strip().lower():
            return Answer(DESCRIBE_IT[lang], tr.level, banner, [], lang, None, None, [], "clarify")

        # 21-sep-2026, batería: «Puoi scrivere in italiano?» o «¿por qué me hablas en inglés?»
        # como PRIMER mensaje no traen pregunta que repetir, y se contestaban con pasajes al azar
        # sobre gastroenteritis. Se le dice que sí, en su lengua, y que cuente qué pasa. Y lo
        # mismo a un mensaje sin una sola letra («???», que llegó así al registro).
        pide_idioma = (
            leida is not None
            and leida.intent == "language_request"
            and not any(t.get("role") == "user" for t in history)
        )
        if tr.level == "routine" and (pide_idioma or not re.search(r"[^\W\d_]", query)):
            return Answer(DESCRIBE_IT[lang], tr.level, banner, [], lang, None, None, [], "clarify")

        # vague first message -> offer options. The topic is read from the query PLUS its synonym
        # expansion, the same as retrieval does: "se ha desmayado" or "llora sin parar" are clear
        # questions that the taxonomy does not name literally, and clarifying them is a bad answer.
        # «¿Qué es PediBot?» y lo que no tiene que ver con la salud de un niño (21-sep-2026).
        # Las dos se contestan con un texto FIJO nuestro, nunca redactado por el modelo. Y sólo
        # cuando el triaje no ha visto nada: si hay la menor señal de alarma, la pregunta es de
        # salud diga lo que diga la lectura. Para «fuera de tema» se pide además que la lista de
        # temas no reconozca nada ni en la pregunta ni en lo que la IA entendió de ella: un
        # «mi hijo se ha tragado una pila» mal leído como «otra cosa» no puede recibir un «eso no
        # es de PediBot».
        # 23-sep-2026: el padre ha dicho que no es un niño. Se le cree, y se le dice que no con
        # amabilidad en vez de contarle la fiebre infantil o dejarle sin fuentes.
        if tr.level == "routine" and not tr.is_alarm and no_es_un_nino(query):
            return Answer(OFF_TOPIC[lang], tr.level, banner, [], lang, None, None, [], "off_topic")

        if leida is not None and tr.level == "routine" and not tr.is_alarm:
            # 22-sep-2026: preguntarle AL CHAT si sabe hacer algo es una pregunta sobre el chat,
            # aunque lo que se le pida no tenga que ver con la salud de un niño. «¿Puede decirme
            # dónde está el hospital infantil más cercano?» recibía «eso no es de PediBot» en vez
            # de un «no, no sé buscar sitios cerca de ti; esto sí sé hacerlo».
            preguntan_por_el = leida.intent == "about_pedibot" or (
                leida.intent == "other" and ASISTENTE.search(query) is not None
            )
            if preguntan_por_el:
                # 22-sep-2026: se contesta LA pregunta, con la ficha de hechos del servicio.
                # Antes, «¿puedo subirle una foto de la erupción?» y «¿guarda mis
                # conversaciones?» recibían las dos el párrafo de presentación.
                nombre = (
                    LANGUAGE_NAME.get(lang, "English")
                    if leida.lang in SUPPORTED_LANGS
                    else (leida.lang_name or LANGUAGE_NAME.get(lang, "English"))
                )
                dicho = responde_sobre(self.llm, query, nombre, self.ficha_sobre_pedibot())
                return Answer(
                    dicho or ABOUT_PEDIBOT[lang],
                    tr.level,
                    banner,
                    [],
                    lang,
                    None,
                    None,
                    [],
                    "about",
                )
            # «Mi» —enviado sin querer— recibía «eso no es de PediBot»: con menos de tres
            # palabras no hay pregunta que juzgar, y se le pide que la cuente
            if (
                leida.intent == "other"
                and largo
                # «¿puedo darle apiretal y cómo se hace una bechamel?» salió «fuera de tema»: un
                # medicamento nombrado es una pregunta de salud aunque venga con una receta
                and not _DRUG.search(query)
                and dose_intent(query, self.drugs) is None
                # 22-sep-2026: si en la pregunta hay un hijo, la pregunta es de aquí. «Mi hija
                # llora cuando se acaba la batería del móvil», «mi hijo se pone nervioso si no
                # hay wifi», «tiene miedo después de ver un vídeo de monstruos»: cinco preguntas
                # de crianza recibieron «eso no es de PediBot». Este texto se escribió para el
                # perro que come chocolate y para la bechamel, y ésos no nombran a ningún niño.
                # Si no hay fuente, ya hay una respuesta honesta para eso, y no echa a nadie.
                and not _mentions_child(query)
                and (
                    self.retriever.taxonomy is None
                    # las palabras del padre y la frase médica de la IA, pero no su lista de palabras
                    # clave: para «¿mi perro puede comer chocolate?» la IA añade «toxicity», que la
                    # lista de temas reconoce, y la pregunta del perro acababa en «consulta a tu
                    # pediatra». Lo peligroso de verdad —pilas, lejía, pastillas— ya lo para el
                    # triaje antes de llegar aquí (comprobado el 21-sep-2026).
                    or self.retriever.taxonomy.topic_for(f"{query} {leida.search_text}") is None
                )
            ):
                return Answer(
                    OFF_TOPIC[lang], tr.level, banner, [], lang, None, None, [], "off_topic"
                )

        # 21-sep-2026: y con lo que la IA ha entendido de la pregunta, si la ha leído. «My son broke
        # his ankle and has a cast» caía aquí, en «descríbemelo mejor», porque la lista de temas
        # no conoce «broke» ni «cast»; la lectura dice «ankle fracture, fractura de tobillo», y
        # eso sí lo conoce. Una pregunta clara no se contesta con otra pregunta.
        leido_tema = f" {leida.search_text} {' '.join(leida.keywords)}" if leida else ""
        # Y si la IA la ha leído como una pregunta de salud CONCRETA, no se pregunta nada: la
        # batería del operador (21-sep-2026) dio «¿qué es lo principal que le pasa?» a quince
        # preguntas claras —se chupa el dedo, un ganglio desde hace 3 semanas, pus en una uña,
        # hipo desde hace 40 minutos— porque la lista de temas no las conoce. Quien decide si
        # es vaga es quien la ha leído.
        concreta = leida is not None and leida.intent == "health" and not leida.vague
        # Y al revés: si la IA dice que es vaga —«mi hijo está malo»—, se pregunta, aunque la
        # lista de temas encuentre algo en las palabras clave que la propia IA le ha añadido
        # («fiebre» para «está malo»): esa pregunta se contestaba hablando de fiebre.
        vaga = leida is not None and leida.intent == "health" and leida.vague
        if (
            tr.level == "routine"
            and not history
            and not concreta
            and (
                vaga
                or (
                    self.retriever.taxonomy is not None
                    and self.retriever.taxonomy.topic_for(
                        query + " " + " ".join(self.retriever.expand(query, lang)) + leido_tema
                    )
                    is None
                    and (len(query.split()) <= 3 or _mentions_child(query))
                )
            )
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
        # Donde la guía de la OMS es la norma nacional, sus palabras compiten por entrar aunque
        # el padre no las diga: un padre asustado describe un síntoma, no pide un tratamiento, y
        # con «mi hijo tiene diarrea» en Kenia ganaban las fuentes europeas, que no hablan de
        # zinc porque en Europa no se usa así (20-sep-2026, ver `who_first`).
        push = who_first_terms(context_text, country)
        search_lang = lang
        answer_lang = LANGUAGE_NAME.get(lang, "English")
        draft_q = query

        # Una IA lee la pregunta antes de buscar (21-sep-2026, ver `interpret`). Un padre desde
        # Italia, con la web en inglés, recibió en inglés una respuesta sacada de la página
        # brasileña de la polio: «gesso» es escayola también en portugués. Medido antes de
        # construirlo: en las lenguas que el sitio no tiene, reescribir la pregunta pasa de traer
        # VIH o fiebre tifoidea a traer la fiebre infantil del NHS; en las que sí tiene, la
        # búsqueda de siempre ya va bien y la reescritura a veces la empeora. Así que se reescribe
        # sólo fuera de las ocho, y en todas se contesta en la lengua en que escribió el padre.
        # El triaje ya ha corrido, sobre el texto original: esto no decide nada de seguridad.
        previa = None
        if leida is not None:
            if leida.intent == "language_request" and prev_user:
                # «Puoi scrivere in italiano?»: no es una pregunta médica, es la de antes en otra
                # lengua. Tratarla como médica buscó salud mental, chikunguña y alcohol.
                if leida.requested_name or leida.lang_name:
                    answer_lang = leida.requested_name or leida.lang_name
                # la última pregunta de verdad, no el último mensaje: «¿por qué me hablas en
                # inglés?» llegó después de un «Otra cosa», y se volvió a contestar «Otra cosa»
                prev_user = next(
                    (
                        t["text"]
                        for t in reversed(history)
                        if t.get("role") == "user" and len(t["text"].split()) >= 3
                    ),
                    prev_user,
                )
                draft_q = prev_user
                search_q = prev_user
                previa = interpret(self.llm, prev_user)
                if previa is not None:
                    ctx["costes"].append((previa.tokens_in, previa.tokens_out, previa.cost_usd))
                if previa is not None and previa.lang not in SUPPORTED_LANGS:
                    search_q, search_lang = previa.search_text, "en"
                    push = [*push, *previa.keywords]
            else:
                # Tres palabras como mínimo para cambiar de idioma: «Dalsy 5 ml?» no dice en qué
                # lengua escribe nadie, y la web ya sabe cuál tiene puesta.
                if leida.lang_name and leida.lang != lang and len(query.split()) >= 3:
                    answer_lang = leida.lang_name
                if leida.lang not in SUPPORTED_LANGS and leida.intent == "health":
                    search_q, search_lang = leida.search_text, "en"
                    push = [*push, *leida.keywords]

        # Segunda búsqueda, con las palabras de la IA (21-sep-2026). «¿Cuándo puedo darle una
        # chuleta?», «¿y una salchicha?», «¿y cacahuetes?» salieron las tres sin fuente, y el
        # corpus tiene las guías de alimentación complementaria: el padre dice «chuleta» y la guía
        # dice «carne». En las ocho lenguas la búsqueda por las palabras del padre va primero,
        # porque medido es la mejor; pero si no encuentra nada, o el redactor dice que lo
        # encontrado no contesta, se busca UNA vez más con la frase médica que leyó la IA. Sólo
        # puede convertir un «no tengo información» en una respuesta con fuente, nunca cambiar
        # una que ya la tenía.
        segunda = (
            leida is not None
            and leida.intent == "health"
            and bool(leida.search_text)
            and search_q != leida.search_text
        )
        alarma = tr.level in ("urgent", "emergency")
        for intento in (1, 2):
            hits, extra = self.retriever.search(
                search_q,
                search_lang,
                red_flag_boost=tr.is_alarm,
                push=push,
            )
            hits = self._inject_rule_sources(tr, hits)
            otra_vez = intento == 1 and segunda and leida is not None
            if not hits:
                if otra_vez and leida is not None:
                    search_q = f"{leida.search_text} {' '.join(leida.keywords)}"
                    push = [*push, *leida.keywords]
                    continue
                return Answer(
                    NO_SOURCE[lang], tr.level, banner, [], lang, None, None, [], "no_source", extra
                )

            user = (
                f"ANSWER LANGUAGE: {answer_lang} — the parent wrote in {answer_lang}; "
                "the sources may be in another language, translate faithfully.\n"
                # 23-sep-2026: y en el alfabeto en que escribió él. Un padre que teclea
                # «bachay ko bukhar hai» en letras latinas recibía urdu en escritura árabe.
                + (
                    "SCRIPT: the parent wrote in the Latin alphabet. Write your whole answer in "
                    "the Latin alphabet too, even if this language is normally written in "
                    "another script.\n"
                    if escritura_latina(draft_q) and answer_lang not in ESCRITURA_LATINA
                    else ""
                )
                + f"{_age_context(tr, context_text)}"
                f"{who_first_note(context_text, country)}"
                f"{tropical_note(context_text, country)}"
                f"{_history_block(history)}"
                f"{CHILD_MODE if mode == 'child' else ''}"
                f"PARENT MESSAGE:\n{draft_q}\n\nSOURCES:\n{_format_sources(hits)}"
            )
            result = self.llm.complete(self.prompt, user, temperature=0.2)
            if otra_vez and leida is not None and _dice_sin_fuente(result.text):
                # el borrador tirado también se paga: va al gasto del día
                ctx["costes"].append((result.tokens_in, result.tokens_out, result.cost_usd))
                search_q = f"{leida.search_text} {' '.join(leida.keywords)}"
                push = [*push, *leida.keywords]
                continue
            problems: list[str] = []
            retry: LLMResult | None = None
            if not _dice_sin_fuente(result.text):
                problems = verify_answer(result.text, hits)
                if alarma and _QUITA_URGENCIA.search(result.text):
                    problems.append(CONTRADICE_AVISO)
                if problems:
                    retry = self.llm.complete(
                        self.prompt
                        + "\n\nYour previous draft failed verification: "
                        + ", ".join(problems)
                        + ". Fix it.",
                        user,
                        temperature=0.0,
                    )
                    # La reescritura tampoco vale: antes de rendirse, la segunda búsqueda. «Darf
                    # ich meinem 9 Monate alten Baby Honig geben?» acababa así en «no sé» teniendo
                    # el NHS la respuesta (batería del 21-sep-2026).
                    if (
                        otra_vez
                        and leida is not None
                        and (_dice_sin_fuente(retry.text) or _insegura(retry.text, hits, alarma))
                    ):
                        for r_ in (result, retry):
                            ctx["costes"].append((r_.tokens_in, r_.tokens_out, r_.cost_usd))
                        search_q = f"{leida.search_text} {' '.join(leida.keywords)}"
                        push = [*push, *leida.keywords]
                        continue
            break
        # «NO_SOURCE»: el redactor dice que ninguno de los pasajes contesta (regla 1 del prompt).
        # Antes lo decía en prosa y citaba igual los pasajes que no servían para explicarlo, y al
        # padre le salían debajo «Poliomielite», «Chikungunya» y «alcohol» por una pregunta sobre
        # un tobillo escayolado (21-sep-2026). Ahora se le da el aviso de siempre, sin fuentes.
        if _dice_sin_fuente(result.text):
            return Answer(
                NO_SOURCE[lang],
                tr.level,
                banner,
                [],
                lang,
                self.prompt_version,
                result,
                [h.chunk.chunk_id for h in hits],
                "no_source",
                extra,
            )
        verification = "ok"
        if problems and retry is not None:
            verification = "regenerated"
            # `verify`, not `verify_answer`: only the SAFETY checks can send an answer to the
            # fallback. A style problem — the same body named three times, nobody named at all —
            # gets its one retry and then ships as written. Turning a medically sound answer into
            # "I have no reliable information on this" because it reads stiffly would be a far
            # worse failure than the stiffness.
            if _dice_sin_fuente(retry.text) or _insegura(retry.text, hits, alarma):
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
            # Excepción a lo de arriba, y sólo una: si después del reintento la PRIMERA frase
            # sigue diciendo que la información no cubre lo preguntado, lo que viene detrás es
            # relleno de otra cosa —la ingurgitación de la madre para el pecho del recién nacido,
            # la otitis para el bebé que se frota la cabeza (batería del 21-sep-2026)—. Mejor el
            # «no tengo información fiable» honesto que media respuesta sobre otra cosa.
            if _EMPIEZA_SIN_INFO.search(_primera_frase(retry.text)):
                return Answer(
                    NO_SOURCE[lang],
                    tr.level,
                    banner,
                    [],
                    lang,
                    self.prompt_version,
                    retry,
                    [h.chunk.chunk_id for h in hits],
                    "no_source",
                    extra,
                    problems=problems,
                )
            result = retry

        # La revisión (21-sep-2026). Una lectura corta de lo ya redactado, con la pregunta al
        # lado: ¿contesta lo que se preguntó?, ¿mete otra enfermedad?, ¿se inventa un veredicto?
        # Salió de revisar 300 respuestas con este mismo criterio: «le tiembla la barbilla al
        # llorar» contestado con cólicos, «¿le faltan vitaminas?» con el sarampión, «no hay
        # ningún problema en que siga con el biberón» sin fuente que lo diga. Si falla, un
        # reintento con la nota concreta; si el reintento tampoco contesta lo preguntado, el
        # «no tengo información fiable» honesto. Nunca toca el aviso, que es del triaje.
        revision = revisa_respuesta(self.llm, query, tr.level, result.text)
        if revision is not None:
            ctx["costes"].append(revision.coste)
        if revision is not None and revision.hay_que_rehacer:
            otra = self.llm.complete(
                self.prompt + "\n\nA reviewer read your draft: " + revision.nota_en + " Fix it.",
                user,
                temperature=0.0,
            )
            ctx["costes"].append((result.tokens_in, result.tokens_out, result.cost_usd))
            fallida = (
                _dice_sin_fuente(otra.text)
                or bool(_insegura(otra.text, hits, alarma))
                or bool(_EMPIEZA_SIN_INFO.search(_primera_frase(otra.text)))
            )
            if fallida and not revision.contesta:
                return Answer(
                    NO_SOURCE[lang],
                    tr.level,
                    banner,
                    [],
                    lang,
                    self.prompt_version,
                    otra,
                    [h.chunk.chunk_id for h in hits],
                    "no_source",
                    extra,
                    problems=[*problems, "review: " + revision.nota_en],
                )
            if not fallida:
                result = otra
                verification = "regenerated"

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
        elif (
            is_growth_question(context_text)
            or gives_both_measurements(context_text)
            or asks_if_a_measure_is_normal(context_text)
        ):
            tool = tool_link("growth", lang, country or country_in_question(context_text))
        text = result.text.strip()
        if ask_age:
            text += "\n\n" + (
                self._traduce(
                    AGE_REFINES["en"], ctx["fuera"], ctx, latino=escritura_latina(context_text)
                )
                if ctx["fuera"]
                else AGE_REFINES[lang]
            )
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
            # en qué lengua se escribió, cuando no es una de las ocho: el registro anónimo es el
            # único sitio donde se ve que alguien escribe en suajili (24-sep-2026)
            wrote_in=(answer_lang if answer_lang != LANGUAGE_NAME.get(lang, "English") else None),
        )
