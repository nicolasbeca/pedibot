"""Segunda oleada del barrido: las reglas que la primera no tocó (8-sep-2026).

Ocho situaciones de alarma más ocho corrientes, en los ocho idiomas. Salieron veinte agujeros
y **un falso positivo**, que es el que más enseña:

    «she has a rash that fades when I press it»  →  EMERGENCIA

Es el resultado TRANQUILIZADOR de la prueba del vaso. El patrón pedía sarpullido y la palabra
«press», sin ninguna negación, así que un padre que hace bien la prueba y cuenta que sale bien
recibía un aviso de urgencias. Es la forma más rápida de enseñarle a ignorarlos, y por eso la
mitad de abajo de este fichero pesa lo mismo que la de arriba.

Los otros diecinueve son de la familia de siempre —la regla escrita y la red más estrecha en
alguna lengua— con dos formas nuevas:

  · **el orden de la frase**: `blood_in_stool` casaba «heces … sangre» y nunca «sangre … en las
    heces», en francés, alemán, ruso, árabe y portugués. El castellano y el inglés tenían los
    DOS órdenes escritos; las otras cinco heredaron uno.
  · **el participio**: el castellano pedía «perdió el conocimiento» y un padre escribe «ha
    perdido el conocimiento», así que un golpe en la cabeza con pérdida de conciencia se
    quedaba en rutina EN EL IDIOMA DE LAS FUENTES.

Y `eating_disorder_signs` tenía seis patrones en castellano, cinco en inglés y **uno** en
francés, alemán, árabe y portugués.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ORDEN = {"routine": 0, "mental_health": 1, "urgent": 2, "emergency": 3}
IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


ALARMA = [
    (
        "atragantamiento",
        "emergency",
        {
            "en": "my son is choking on a grape",
            "es": "mi hijo se está atragantando con una uva",
            "fr": "mon fils s'étouffe avec un raisin",
            "de": "mein Sohn erstickt an einer Weintraube",
            "ru": "сын подавился виноградиной",
            "ar": "ابني يختنق بحبة عنب",
            "pt": "meu filho está engasgado com uma uva",
            "hi": "मेरा बेटा अंगूर से दम घुट रहा है",
        },
    ),
    (
        "sangrado que no para",
        "emergency",
        {
            "en": "the cut won't stop bleeding",
            "es": "la herida no deja de sangrar",
            "fr": "la plaie n'arrête pas de saigner",
            "de": "die Wunde hört nicht auf zu bluten",
            "ru": "рана не перестаёт кровоточить",
            "ar": "الجرح لا يتوقف عن النزيف",
            "pt": "o corte não para de sangrar",
            "hi": "घाव से खून नहीं रुक रहा",
        },
    ),
    (
        "golpe cabeza + inconsciencia",
        "emergency",
        {
            "en": "he fell and lost consciousness for a moment",
            "es": "se ha caído y ha perdido el conocimiento un momento",
            "fr": "il est tombé et a perdu connaissance un instant",
            "de": "er ist gefallen und war kurz bewusstlos",
            "ru": "упал и ненадолго потерял сознание",
            "ar": "سقط وفقد الوعي للحظة",
            "pt": "caiu e perdeu a consciência por um momento",
            "hi": "वह गिरा और थोड़ी देर बेहोश हो गया",
        },
    ),
    (
        "vómitos tras golpe en la cabeza",
        "urgent",
        {
            "en": "he hit his head and has vomited twice",
            "es": "se dio un golpe en la cabeza y ha vomitado dos veces",
            "fr": "il s'est cogné la tête et a vomi deux fois",
            "de": "er hat sich den Kopf gestoßen und zweimal erbrochen",
            "ru": "ударился головой и дважды вырвало",
            "ar": "ارتطم رأسه وتقيأ مرتين",
            "pt": "bateu a cabeça e vomitou duas vezes",
            "hi": "सिर टकराया और दो बार उल्टी की",
        },
    ),
    (
        "piel moteada",
        "emergency",
        {
            "en": "his skin is mottled and grey",
            "es": "tiene la piel moteada y grisácea",
            "fr": "sa peau est marbrée et grise",
            "de": "seine Haut ist marmoriert und grau",
            "ru": "кожа мраморная и серая",
            "ar": "جلده مرقط ورمادي",
            "pt": "a pele está marmorizada e acinzentada",
            "hi": "त्वचा चितकबरी और भूरी है",
        },
    ),
    (
        "quemadura",
        "urgent",
        {
            "en": "he burned his hand with boiling water",
            "es": "se ha quemado la mano con agua hirviendo",
            "fr": "il s'est brûlé la main avec de l'eau bouillante",
            "de": "er hat sich die Hand mit kochendem Wasser verbrannt",
            "ru": "обжёг руку кипятком",
            "ar": "أحرق يده بماء مغلي",
            "pt": "queimou a mão com água fervendo",
            "hi": "उबलते पानी से हाथ जल गया",
        },
    ),
    (
        "sangre en las heces",
        "urgent",
        {
            "en": "there is blood in his stool",
            "es": "tiene sangre en las heces",
            "fr": "il y a du sang dans ses selles",
            "de": "er hat Blut im Stuhl",
            "ru": "кровь в стуле",
            "ar": "يوجد دم في البراز",
            "pt": "tem sangue nas fezes",
            "hi": "मल में खून है",
        },
    ),
    (
        "adolescente deja de comer",
        "mental_health",
        {
            "en": "my teenage daughter has stopped eating and vomits after meals",
            "es": "mi hija adolescente ha dejado de comer y vomita después de comer",
            "fr": "ma fille adolescente ne mange plus et vomit après les repas",
            "de": "meine Tochter isst nicht mehr und erbricht nach dem Essen",
            "ru": "дочь-подросток перестала есть и её рвёт после еды",
            "ar": "ابنتي المراهقة توقفت عن الأكل وتتقيأ بعد الطعام",
            "pt": "minha filha adolescente parou de comer e vomita depois das refeições",
            "hi": "मेरी किशोर बेटी ने खाना छोड़ दिया है और खाने के बाद उल्टी करती है",
        },
    ),
]

NORMAL = [
    (
        "no quiere verdura",
        {
            "en": "my 4-year-old refuses to eat vegetables",
            "es": "mi hijo de 4 años no quiere comer verdura",
            "fr": "mon fils de 4 ans ne veut pas manger de légumes",
            "de": "mein 4-jähriger Sohn will kein Gemüse essen",
            "ru": "сын 4 лет не хочет есть овощи",
            "ar": "ابني عمره 4 سنوات لا يريد أكل الخضار",
            "pt": "meu filho de 4 anos não quer comer verdura",
            "hi": "मेरा 4 साल का बेटा सब्ज़ी नहीं खाना चाहता",
        },
    ),
    (
        "moratón de una caída",
        {
            "en": "she fell in the park and has a small bruise on her knee",
            "es": "se cayó en el parque y tiene un moratón pequeño en la rodilla",
            "fr": "elle est tombée au parc et a un petit bleu au genou",
            "de": "sie ist im Park gefallen und hat einen kleinen blauen Fleck am Knie",
            "ru": "упала в парке, маленький синяк на колене",
            "ar": "سقطت في الحديقة وعندها كدمة صغيرة في الركبة",
            "pt": "caiu no parque e tem um roxinho pequeno no joelho",
            "hi": "वह पार्क में गिरी और घुटने पर छोटा नील पड़ा है",
        },
    ),
    (
        "sarpullido que SÍ se va al apretar",
        {
            "en": "she has a rash that fades when I press it",
            "es": "tiene un sarpullido que desaparece al apretarlo",
            "fr": "elle a des boutons qui disparaissent quand j'appuie",
            "de": "sie hat einen Ausschlag, der beim Drücken verschwindet",
            "ru": "сыпь бледнеет при надавливании",
            "ar": "عندها طفح يختفي عند الضغط عليه",
            "pt": "tem manchinhas que somem quando aperto",
            "hi": "दबाने पर मिट जाने वाले दाने हैं",
        },
    ),
    (
        "le molesta el sol de la playa",
        {
            "en": "the bright sun at the beach bothers his eyes",
            "es": "le molesta el sol fuerte de la playa en los ojos",
            "fr": "le soleil de la plage lui gêne les yeux",
            "de": "die grelle Sonne am Strand stört seine Augen",
            "ru": "яркое солнце на пляже режет ему глаза",
            "ar": "شمس الشاطئ القوية تزعج عينيه",
            "pt": "o sol forte da praia incomoda os olhos dele",
            "hi": "समुद्र तट की तेज़ धूप उसकी आँखों को चुभती है",
        },
    ),
    (
        "vomitó una vez y está bien",
        {
            "en": "he vomited once and is playing normally now",
            "es": "vomitó una vez y ya está jugando normal",
            "fr": "il a vomi une fois et joue normalement",
            "de": "er hat einmal erbrochen und spielt jetzt normal",
            "ru": "вырвало один раз, сейчас играет как обычно",
            "ar": "تقيأ مرة واحدة والآن يلعب بشكل طبيعي",
            "pt": "vomitou uma vez e já está brincando normal",
            "hi": "एक बार उल्टी की और अब सामान्य खेल रहा है",
        },
    ),
    (
        "le bajó la fiebre",
        {
            "en": "I gave him paracetamol and the fever came down",
            "es": "le di paracetamol y le bajó la fiebre",
            "fr": "je lui ai donné du paracétamol et la fièvre est tombée",
            "de": "ich habe ihm Paracetamol gegeben und das Fieber ist gesunken",
            "ru": "дала парацетамол, температура спала",
            "ar": "أعطيته باراسيتامول وانخفضت الحرارة",
            "pt": "dei paracetamol e a febre baixou",
            "hi": "पैरासिटामोल दिया और बुखार उतर गया",
        },
    ),
    (
        "duerme y come bien",
        {
            "en": "he sleeps well and eats well, I just have a question",
            "es": "duerme bien y come bien, solo tengo una duda",
            "fr": "il dort bien et mange bien, j'ai juste une question",
            "de": "er schläft gut und isst gut, ich habe nur eine Frage",
            "ru": "хорошо спит и ест, просто вопрос",
            "ar": "ينام جيدا ويأكل جيدا، عندي سؤال فقط",
            "pt": "dorme bem e come bem, só tenho uma dúvida",
            "hi": "अच्छी नींद और अच्छा खाना, बस एक सवाल है",
        },
    ),
    (
        "guardería y mocos",
        {
            "en": "since starting nursery he catches a cold every month",
            "es": "desde que va a la guardería se acatarra cada mes",
            "fr": "depuis la crèche il attrape un rhume chaque mois",
            "de": "seit der Kita hat er jeden Monat Schnupfen",
            "ru": "с началом сада каждый месяц насморк",
            "ar": "منذ الحضانة يصاب بالزكام كل شهر",
            "pt": "desde a creche pega resfriado todo mês",
            "hi": "डे-केयर के बाद हर महीने सर्दी हो जाती है",
        },
    ),
]


@pytest.mark.parametrize(
    ("etiqueta", "esperado", "lang", "pregunta"),
    [(e, esp, idioma, pr[idioma]) for e, esp, pr in ALARMA for idioma in IDIOMAS],
)
def test_a_warning_sign_is_read_in_every_language(
    triage: Triage, etiqueta: str, esperado: str, lang: str, pregunta: str
) -> None:
    nivel = triage.assess(pregunta).level
    assert ORDEN[nivel] >= ORDEN[esperado], (
        f"[{lang}] {etiqueta}: «{pregunta}» sale {nivel}, se espera al menos {esperado}"
    )


@pytest.mark.parametrize(
    ("etiqueta", "lang", "pregunta"),
    [(e, idioma, pr[idioma]) for e, pr in NORMAL for idioma in IDIOMAS],
)
def test_an_ordinary_situation_stays_ordinary_in_every_language(
    triage: Triage, etiqueta: str, lang: str, pregunta: str
) -> None:
    """La prueba del vaso con resultado bueno vive aquí: enseñar una alarma a quien acaba de
    comprobar que no la hay es peor que no tener alarma."""
    assert triage.assess(pregunta).level == "routine", (
        f"[{lang}] {etiqueta}: «{pregunta}» da la alarma"
    )


#: La fotofobia SOLA no es una alarma: la produce una conjuntivitis, una migraña o leer con mala
#: luz. Con fiebre o con dolor de cabeza sí lo es. Decisión del operador del 8-sep-2026 al pedir
#: «lo más seguro»: aplicado en serio, eso son dos cosas — subir la rigidez de nuca a emergencia
#: y bajar la fotofobia suelta a rutina, porque una alarma que salta con leer con mala luz enseña
#: a ignorar las alarmas, que es el otro lado de la seguridad.
FOTOFOBIA_SOLA = [
    ("es", "le molesta la luz cuando lee"),
    ("es", "tiene fotofobia desde ayer"),
    ("es", "le molesta el sol fuerte de la playa en los ojos"),
    ("en", "the bright light bothers his eyes"),
    ("fr", "la lumière le gêne un peu"),
    ("pt", "a luz incomoda os olhos dele"),
]

FOTOFOBIA_CON_FIEBRE = [
    ("es", "le molesta la luz y tiene fiebre"),
    ("es", "fiebre alta y le molesta mucho la luz"),
    ("en", "headache and sensitive to light"),
    ("fr", "la lumière le gêne et il a de la fièvre"),
    ("de", "Fieber und lichtempfindlich"),
    ("pt", "febre e a luz incomoda"),
]

CUELLO_NO_RIGIDO = [
    ("es", "tiene tortícolis"),
    ("es", "le duele el cuello de dormir mal"),
    ("en", "my child has neck pain after sports"),
    ("de", "mein Kind hat Nackenschmerzen vom Schlafen"),
    ("de", "er hat einen steifen Arm"),
    ("pt", "tem dor no pescoço"),
    ("hi", "सोने से गर्दन में दर्द है"),
]

RIGIDEZ_DE_NUCA = [
    ("es", "tiene el cuello rígido y fiebre alta"),
    ("es", "no puede doblar el cuello"),
    ("en", "stiff neck and fever"),
    ("fr", "il a la nuque raide"),
    ("de", "er hat einen steifen Nacken"),
    ("de", "mit steifem Nacken"),
    ("ru", "у ребёнка ригидность затылка"),
    ("ar", "رقبته متيبسة"),
    ("hi", "गर्दन में अकड़न है"),
]


@pytest.mark.parametrize(("lang", "pregunta"), RIGIDEZ_DE_NUCA)
def test_a_stiff_neck_is_an_emergency(triage: Triage, lang: str, pregunta: str) -> None:
    """Una meningitis se mide en horas, y ninguna causa banal hace que un padre escriba esto."""
    assert triage.assess(pregunta).level == "emergency", f"[{lang}] «{pregunta}»"


@pytest.mark.parametrize(("lang", "pregunta"), FOTOFOBIA_CON_FIEBRE)
def test_light_hurting_with_fever_or_headache_is_urgent(
    triage: Triage, lang: str, pregunta: str
) -> None:
    assert triage.assess(pregunta).level == "urgent", f"[{lang}] «{pregunta}»"


@pytest.mark.parametrize(("lang", "pregunta"), FOTOFOBIA_SOLA + CUELLO_NO_RIGIDO)
def test_neither_a_sore_neck_nor_light_alone_raises_the_alarm(
    triage: Triage, lang: str, pregunta: str
) -> None:
    assert triage.assess(pregunta).level == "routine", f"[{lang}] «{pregunta}» da la alarma"
