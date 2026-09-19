"""¿En qué idioma cree el motor que le están hablando? (8-sep-2026)

Es la decisión más temprana de todas y de ella cuelga el resto: el idioma de la respuesta, qué
tabla de sinónimos se usa y en qué lengua se le explica al padre por qué hay que ir a urgencias.
No estaba medida.

Diez preguntas por lengua, escritas como las escribe un padre —cortas, y varias **sin acentos**,
que es como se teclea en un móvil— y salieron 15 fallos de 81:

    portugués   3 de 10 correctas
    francés     6 de 11

Un padre portugués recibía la respuesta en inglés o en castellano. Y «Qu'est-ce que la rougeole
et comment la soigner ?» se contestaba EN CASTELLANO.

La causa de fondo no era que faltaran palabras, sino que sobraban las **compartidas**: « que » y
« para » se escriben igual en las tres lenguas latinas y estaban contando como marcador del
castellano, así que le regalaban un punto en cada pregunta francesa o portuguesa. Un marcador
que no separa no es un marcador.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import detect_lang

PREGUNTAS = {
    "es": [
        "mi hijo de 3 años tiene fiebre",
        "¿cuánto paracetamol para 14 kg?",
        "se ha dado un golpe en la cabeza",
        "no quiere comer nada desde ayer",
        "tiene tos por la noche",
        "le han salido manchas en la tripa",
        "cuanto dura la varicela",
        "mi bebe llora mucho",
        "que hago si vomita",
        "cuando puedo darle ibuprofeno",
    ],
    "en": [
        "my 3-year-old has a fever",
        "how much paracetamol for 14 kg?",
        "he hit his head on the floor",
        "she has not eaten since yesterday",
        "coughing at night",
        "spots on her tummy",
        "how long does chickenpox last",
        "my baby cries a lot",
        "what do I do if he vomits",
        "when can I give ibuprofen",
    ],
    "fr": [
        "mon fils de 3 ans a de la fievre",
        "combien de paracetamol pour 14 kg ?",
        "il s'est cogne la tete",
        "elle ne mange rien depuis hier",
        "il tousse la nuit",
        "des boutons sur le ventre",
        "combien de temps dure la varicelle",
        "mon bebe pleure beaucoup",
        "que faire s'il vomit",
        "quand puis-je donner de l'ibuprofene",
        "Qu'est-ce que la rougeole et comment la soigner ?",
    ],
    "de": [
        "mein Sohn ist 3 Jahre alt und hat Fieber",
        "wie viel Paracetamol für 14 kg?",
        "er hat sich den Kopf gestoßen",
        "sie isst seit gestern nichts",
        "er hustet nachts",
        "Flecken am Bauch",
        "wie lange dauern Windpocken",
        "mein Baby weint viel",
        "was tun wenn er erbricht",
        "wann darf ich Ibuprofen geben",
    ],
    "pt": [
        "meu filho de 3 anos esta com febre",
        "quanto paracetamol para 14 kg?",
        "ele bateu a cabeca",
        "ela nao come nada desde ontem",
        "tosse a noite",
        "manchas na barriga",
        "quanto tempo dura a varicela",
        "meu bebe chora muito",
        "o que faco se ele vomitar",
        "quando posso dar ibuprofeno",
    ],
    "ru": [
        "моему сыну 3 года, температура",
        "сколько парацетамола на 14 кг?",
        "ударился головой",
        "не ест со вчерашнего дня",
        "кашляет по ночам",
        "пятна на животе",
        "сколько длится ветрянка",
        "малыш много плачет",
        "что делать если рвота",
        "когда можно давать ибупрофен",
    ],
    "ar": [
        "ابني عمره 3 سنوات وعنده حمى",
        "كم باراسيتامول لوزن 14 كيلو؟",
        "ارتطم رأسه",
        "لم تأكل شيئا منذ أمس",
        "يسعل في الليل",
        "بقع على البطن",
        "كم تدوم الجديري",
        "طفلي يبكي كثيرا",
        "ماذا أفعل إذا تقيأ",
        "متى أعطيه إيبوبروفين",
    ],
    "hi": [
        "मेरे बेटे की उम्र 3 साल है और बुखार है",
        "14 किलो के लिए कितना पैरासिटामोल?",
        "उसके सिर में चोट लगी",
        "कल से कुछ नहीं खाया",
        "रात में खाँसी आती है",
        "पेट पर दाने हैं",
        "चिकनपॉक्स कितने दिन रहता है",
        "मेरा बच्चा बहुत रोता है",
        "उल्टी हो तो क्या करूँ",
        "आइबुप्रोफेन कब दे सकते हैं",
    ],
}


@pytest.mark.parametrize(
    ("esperado", "pregunta"),
    [(lg, q) for lg, lista in PREGUNTAS.items() for q in lista],
)
def test_the_language_a_parent_wrote_in_is_the_one_detected(esperado: str, pregunta: str) -> None:
    got = detect_lang(pregunta)
    assert got == esperado, f"«{pregunta}» → {got}, se esperaba {esperado}"


def test_a_marker_that_separates_nothing_is_not_a_marker() -> None:
    """El candado de la causa: si « que » o « para » vuelven a la lista española, vuelven los
    fallos, porque el francés y el portugués las escriben igual."""
    from pedibot.bot.retrieval import detect_lang as _d

    assert _d("que faire s'il vomit") == "fr"
    assert _d("o que faco se ele vomitar") == "pt"
    assert _d("quanto paracetamol para 14 kg?") == "pt"
