"""Los signos de alarma más graves, dichos como los diría un padre, en los ocho idiomas.

Este fichero es un barrido, no una lista de casos: la misma situación escrita en las ocho
lenguas y comparadas **entre sí**. Es la forma que ha encontrado, el 8-sep-2026, fallos que
1.400 tests no veían — porque los tests comprueban lo que ya sabemos que existe y el barrido
mira la diferencia, que es donde viven las averías de este proyecto.

De doce situaciones × ocho idiomas salieron veinte agujeros, todos del mismo tipo: la regla
estaba escrita y cada lengua había recibido una red más estrecha.

  · el hindi conjuga los verbos por GÉNERO y solo estaba el masculino, así que una hija que
    dice que quiere morir no disparaba la regla del 024 y un hijo sí;
  · la anafilaxia tenía el sustantivo y el adjetivo («labios hinchados») y no el verbo («se le
    están hinchando los labios»), que es como se cuenta algo que está pasando ahora — faltaba
    en cinco lenguas;
  · la lejía, que es la intoxicación doméstica más común, solo estaba nombrada en castellano,
    inglés y francés;
  · «lleva doce horas sin mojar el pañal» no casaba en NINGUNA de las ocho, teniendo todas el
    pañal seco como sustantivo;
  · y el alemán pone el producto delante del verbo («Bleichmittel getrunken»), que es al revés
    de lo que el patrón esperaba.

La segunda mitad —las situaciones corrientes— importa igual: una regla ensanchada que salta con
unos mocos no protege a nadie.
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


SITUACIONES = [
    (
        "convulsión",
        "emergency",
        {
            "en": "my child is having a seizure",
            "es": "mi hijo está teniendo una convulsión",
            "fr": "mon enfant fait une convulsion",
            "de": "mein Kind hat einen Krampfanfall",
            "ru": "у ребёнка судороги",
            "ar": "طفلي عنده تشنجات",
            "pt": "meu filho está tendo uma convulsão",
            "hi": "मेरे बच्चे को दौरा पड़ रहा है",
        },
    ),
    (
        "no responde",
        "emergency",
        {
            "en": "my child is unresponsive",
            "es": "mi hijo no responde",
            "fr": "mon enfant ne réagit pas",
            "de": "mein Kind reagiert nicht",
            "ru": "ребёнок не реагирует",
            "ar": "طفلي لا يستجيب",
            "pt": "meu filho não responde",
            "hi": "मेरा बच्चा प्रतिक्रिया नहीं दे रहा",
        },
    ),
    (
        "manchas que no desaparecen",
        "emergency",
        {
            "en": "a rash that doesn't fade when I press it",
            "es": "unas manchas que no desaparecen al apretar",
            "fr": "des taches qui ne disparaissent pas à la pression",
            "de": "Flecken, die beim Draufdrücken nicht verschwinden",
            "ru": "сыпь не бледнеет при надавливании",
            "ar": "طفح لا يختفي عند الضغط عليه",
            "pt": "manchas que não somem quando aperto",
            "hi": "दबाने पर न मिटने वाले दाने",
        },
    ),
    (
        "reacción alérgica grave",
        "emergency",
        {
            "en": "his lips and face are swelling up after eating",
            "es": "se le están hinchando los labios y la cara",
            "fr": "ses lèvres et son visage gonflent",
            "de": "seine Lippen und sein Gesicht schwellen an",
            "ru": "у него отекают губы и лицо",
            "ar": "شفتاه ووجهه ينتفخان",
            "pt": "os lábios e o rosto dele estão inchando",
            "hi": "उसके होंठ और चेहरा सूज रहे हैं",
        },
    ),
    (
        "ha tragado un producto",
        "urgent",
        {
            "en": "my child drank bleach",
            "es": "mi hijo se ha bebido lejía",
            "fr": "mon enfant a bu de l'eau de javel",
            "de": "mein Kind hat Bleichmittel getrunken",
            "ru": "ребёнок выпил отбеливатель",
            "ar": "طفلي شرب مبيّض الكلور",
            "pt": "meu filho bebeu água sanitária",
            "hi": "मेरे बच्चे ने ब्लीच पी लिया",
        },
    ),
    (
        "pila de botón",
        "emergency",
        {
            "en": "my daughter swallowed a button battery",
            "es": "mi hija se ha tragado una pila de botón",
            "fr": "ma fille a avalé une pile bouton",
            "de": "meine Tochter hat eine Knopfbatterie verschluckt",
            "ru": "дочь проглотила батарейку-таблетку",
            "ar": "ابنتي بلعت بطارية زر",
            "pt": "minha filha engoliu uma pilha botão",
            "hi": "मेरी बेटी ने बटन सेल निगल ली",
        },
    ),
    (
        "deshidratación",
        "urgent",
        {
            "en": "she hasn't had a wet nappy in 12 hours",
            "es": "lleva 12 horas sin mojar el pañal",
            "fr": "elle n'a pas mouillé sa couche depuis 12 heures",
            "de": "sie hat seit 12 Stunden keine nasse Windel",
            "ru": "12 часов подгузник сухой",
            "ar": "لم تبلل الحفاض منذ 12 ساعة",
            "pt": "faz 12 horas que não molha a fralda",
            "hi": "12 घंटे से डायपर गीला नहीं हुआ",
        },
    ),
    (
        "cuello rígido",
        "emergency",
        {
            "en": "stiff neck and he can't stand the light",
            "es": "tiene el cuello rígido y le molesta la luz",
            "fr": "la nuque raide et la lumière le gêne",
            "de": "steifer Nacken und Licht stört ihn",
            "ru": "ригидность затылка и светобоязнь",
            "ar": "تيبس في الرقبة وحساسية للضوء",
            "pt": "pescoço rígido e a luz incomoda",
            "hi": "गर्दन अकड़ी है और रोशनी चुभती है",
        },
    ),
    (
        "ideación suicida",
        "mental_health",
        {
            "en": "my daughter says she wants to die",
            "es": "mi hija dice que se quiere morir",
            "fr": "ma fille dit qu'elle veut mourir",
            "de": "meine Tochter sagt, sie will sterben",
            "ru": "дочь говорит, что хочет умереть",
            "ar": "ابنتي تقول إنها تريد أن تموت",
            "pt": "minha filha diz que quer morrer",
            "hi": "मेरी बेटी कहती है कि वह मरना चाहती है",
        },
    ),
    (
        "recién nacido no come",
        "urgent",
        {
            "en": "my 5-day-old refuses to feed",
            "es": "mi bebé de 5 días rechaza las tomas",
            "fr": "mon bébé de 5 jours refuse de téter",
            "de": "mein 5 Tage altes Baby trinkt nicht",
            "ru": "новорождённый отказывается от еды",
            "ar": "مولودي الجديد يرفض الرضاعة",
            "pt": "meu bebê de 5 dias recusa mamar",
            "hi": "मेरा नवजात दूध नहीं पी रहा",
        },
    ),
]
NORMALES = [
    (
        "catarro",
        {
            "en": "my child has a runny nose and a mild cough",
            "es": "mi hijo tiene mocos y algo de tos",
            "fr": "mon enfant a le nez qui coule et un peu de toux",
            "de": "mein Kind hat Schnupfen und etwas Husten",
            "ru": "у ребёнка насморк и небольшой кашель",
            "ar": "طفلي عنده زكام وسعال خفيف",
            "pt": "meu filho está com coriza e tosse leve",
            "hi": "मेरे बच्चे को नाक बह रही है और हल्की खाँसी है",
        },
    ),
    (
        "dientes",
        {
            "en": "my baby is teething and drooling a lot",
            "es": "a mi bebé le están saliendo los dientes",
            "fr": "mon bébé fait ses dents",
            "de": "mein Baby bekommt Zähne",
            "ru": "у малыша режутся зубки",
            "ar": "طفلي يسنّن",
            "pt": "meu bebê está nascendo dentes",
            "hi": "मेरे बच्चे के दाँत निकल रहे हैं",
        },
    ),
]


@pytest.mark.parametrize(
    ("etiqueta", "esperado", "lang", "pregunta"),
    [(e, esp, idioma, preg[idioma]) for e, esp, preg in SITUACIONES for idioma in IDIOMAS],
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
    [(e, idioma, preg[idioma]) for e, preg in NORMALES for idioma in IDIOMAS],
)
def test_an_ordinary_situation_stays_ordinary_in_every_language(
    triage: Triage, etiqueta: str, lang: str, pregunta: str
) -> None:
    assert triage.assess(pregunta).level == "routine", (
        f"[{lang}] {etiqueta}: «{pregunta}» da la alarma"
    )
