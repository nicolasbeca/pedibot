"""Tercera oleada: lo que señaló contar los patrones por escritura (8-sep-2026).

Las dos oleadas anteriores se escribieron a mano, situación por situación. Ésta la dirigió un
detector: contar cuántos patrones tiene cada regla en cada alfabeto y dividir el latino entre
cinco, que son las lenguas que comparten ese alfabeto. Señaló cuatro reglas, y la peor era

    neuro_deficit (EMERGENCIA):  30 patrones latinos,  2 en cirílico,  2 en árabe

o sea catorce signos distintos en las lenguas latinas —boca torcida, pérdida de fuerza, habla
arrastrada, visión doble de repente, marcha inestable, desorientación— y **dos** en ruso y en
árabe. De 96 combinaciones probadas fallaron 39.

Y salió el segundo falso positivo del día, en el idioma con más usuarios:

    «está aprendiendo a andar y se cae mucho, ¿es normal?»  →  EMERGENCIA

El patrón aceptaba «anda … se cae», y caerse aprendiendo a andar es lo más normal que hay. Un
signo neurológico de la marcha es un CAMBIO: antes andaba bien y ahora no. El «se cae» suelto se
retiró y ahora se exige inestabilidad o que sea de repente.
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
 ("boca torcida", "emergency", {
  "en": "one side of his mouth is drooping", "es": "tiene la boca torcida hacia un lado",
  "fr": "sa bouche est tordue d'un côté", "de": "sein Mund hängt auf einer Seite herunter",
  "ru": "у него перекосило рот", "ar": "فمه ملتوٍ إلى جهة واحدة",
  "pt": "a boca dele está torta para um lado", "hi": "उसका मुँह एक तरफ टेढ़ा हो गया है"}),
 ("de repente ve mal", "emergency", {
  "en": "he suddenly cannot see properly", "es": "de repente ve borroso y doble",
  "fr": "il voit soudain flou et double", "de": "er sieht plötzlich verschwommen und doppelt",
  "ru": "внезапно стал плохо видеть, двоится в глазах", "ar": "فجأة صار يرى بشكل ضبابي ومزدوج",
  "pt": "de repente está vendo embaçado e dobrado", "hi": "अचानक धुंधला और दोहरा दिखने लगा"}),
 ("camina torcido", "emergency", {
  "en": "he is unsteady and keeps falling when walking",
  "es": "camina torcido y se cae todo el rato",
  "fr": "il marche de travers et tombe tout le temps",
  "de": "er geht unsicher und fällt ständig hin",
  "ru": "шатается при ходьбе и всё время падает",
  "ar": "يمشي بترنح ويسقط طوال الوقت",
  "pt": "anda cambaleando e cai o tempo todo",
  "hi": "लड़खड़ाकर चलता है और बार-बार गिरता है"}),
 ("no reconoce / desorientado", "emergency", {
  "en": "he does not recognise me and seems confused",
  "es": "no me reconoce y está desorientado",
  "fr": "il ne me reconnaît pas et semble désorienté",
  "de": "er erkennt mich nicht und wirkt verwirrt",
  "ru": "не узнаёт меня и дезориентирован",
  "ar": "لا يتعرف عليّ ويبدو مشوشا",
  "pt": "não me reconhece e está desorientado",
  "hi": "मुझे पहचान नहीं रहा और भ्रमित लग रहा है"}),
 ("cuesta despertarle", "urgent", {
  "en": "it is very hard to wake him up today", "es": "hoy cuesta muchísimo despertarle",
  "fr": "il est très difficile à réveiller aujourd'hui",
  "de": "er ist heute sehr schwer zu wecken",
  "ru": "сегодня его очень трудно разбудить", "ar": "من الصعب جدا إيقاظه اليوم",
  "pt": "hoje está muito difícil acordá-lo", "hi": "आज उसे जगाना बहुत मुश्किल हो रहा है"}),
 ("barriga que va a peor", "urgent", {
  "en": "his tummy pain is getting worse and keeps him awake",
  "es": "el dolor de barriga va a más y no le deja dormir",
  "fr": "son mal de ventre empire et l'empêche de dormir",
  "de": "seine Bauchschmerzen werden immer schlimmer und er kann nicht schlafen",
  "ru": "боль в животе всё сильнее и не даёт ему спать",
  "ar": "ألم بطنه يزداد ولا يدعه ينام",
  "pt": "a dor de barriga está piorando e não o deixa dormir",
  "hi": "पेट का दर्द बढ़ता जा रहा है और सोने नहीं दे रहा"}),
 ("adolescente se salta comidas", "mental_health", {
  "en": "my teenager keeps skipping meals and is obsessed with her weight",
  "es": "mi adolescente se salta las comidas y está obsesionada con su peso",
  "fr": "mon adolescente saute les repas et est obsédée par son poids",
  "de": "meine Jugendliche lässt Mahlzeiten aus und ist besessen von ihrem Gewicht",
  "ru": "подросток пропускает еду и одержима своим весом",
  "ar": "مراهقتي تتخطى الوجبات ومهووسة بوزنها",
  "pt": "minha adolescente pula refeições e é obcecada com o peso",
  "hi": "मेरी किशोरी खाना छोड़ रही है और वज़न को लेकर परेशान है"}),
 ("bebé flácido", "urgent", {
  "en": "the baby is floppy and very lethargic", "es": "el bebé está muy flojo y decaído",
  "fr": "le bébé est tout mou et très abattu", "de": "das Baby ist schlaff und sehr matt",
  "ru": "ребёнок вялый и обмякший", "ar": "الطفل رخو وخامل جدا",
  "pt": "o bebê está molinho e muito abatido", "hi": "बच्चा ढीला और बहुत सुस्त है"}),
]

NORMAL = [
 ("duerme la siesta", {
  "en": "he is sleepy after lunch and takes a good nap",
  "es": "después de comer tiene sueño y duerme bien la siesta",
  "fr": "il a sommeil après le déjeuner et fait une bonne sieste",
  "de": "nach dem Essen ist er müde und hält einen guten Mittagsschlaf",
  "ru": "после обеда хочет спать и хорошо спит днём",
  "ar": "بعد الغداء ينعس وينام قيلولة جيدة",
  "pt": "depois do almoço fica com sono e dorme bem a sesta",
  "hi": "खाने के बाद नींद आती है और अच्छी झपकी लेता है"}),
 ("aprende a andar", {
  "en": "he is learning to walk and falls a lot, is that normal",
  "es": "está aprendiendo a andar y se cae mucho, ¿es normal?",
  "fr": "il apprend à marcher et tombe beaucoup, est-ce normal",
  "de": "er lernt laufen und fällt oft hin, ist das normal",
  "ru": "учится ходить и часто падает, это нормально",
  "ar": "يتعلم المشي ويسقط كثيرا، هل هذا طبيعي",
  "pt": "está aprendendo a andar e cai muito, é normal",
  "hi": "चलना सीख रहा है और बहुत गिरता है, क्या यह सामान्य है"}),
 ("adolescente come poco un día", {
  "en": "my teenager did not feel like dinner yesterday",
  "es": "ayer mi adolescente no tenía ganas de cenar",
  "fr": "hier mon adolescent n'avait pas envie de dîner",
  "de": "gestern hatte mein Teenager keine Lust auf Abendessen",
  "ru": "вчера подросток не захотел ужинать",
  "ar": "أمس لم يرغب المراهق في العشاء",
  "pt": "ontem meu adolescente não quis jantar",
  "hi": "कल मेरे किशोर का रात का खाना खाने का मन नहीं था"}),
 ("dolor de barriga leve", {
  "en": "he had a mild tummy ache and it went away after a poo",
  "es": "le dolía un poco la barriga y se le pasó al hacer caca",
  "fr": "il avait un peu mal au ventre et ça est passé après être allé aux toilettes",
  "de": "er hatte leichte Bauchschmerzen und nach dem Stuhlgang war es weg",
  "ru": "немного болел живот и прошло после туалета",
  "ar": "كان عنده ألم خفيف في البطن وزال بعد التبرز",
  "pt": "teve uma dorzinha de barriga e passou depois de evacuar",
  "hi": "हल्का पेट दर्द था और शौच के बाद ठीक हो गया"}),
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
    """Aprender a andar y caerse vive aquí, y la siesta después de comer también."""
    assert triage.assess(pregunta).level == "routine", (
        f"[{lang}] {etiqueta}: «{pregunta}» da la alarma"
    )
