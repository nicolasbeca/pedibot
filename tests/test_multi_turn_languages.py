"""La misma conversación de dos turnos, en los ocho idiomas (8-sep-2026).

Probar los turnos en castellano destapó tres huecos. Probarlos en las ocho lenguas destapó
**seis más**, y ninguno de familia nueva: orden invertido, verbo en vez de sustantivo, una
palabra intercalada, una flexión que falta.

Lo que los saca a la luz es la DISTANCIA. Cuando las dos mitades de una regla vienen en mensajes
distintos hay texto en medio, y sobre todo la frase se dice **entera** —con su verbo, su
posesivo y su adjetivo— en vez de telegráfica:

    de   el patrón pedía «Flecken … nicht verschwinden» y se dice «verschwinden nicht»
    ru   pedía «не бледнеет» en singular, y una erupción se cuenta en plural: «не бледнеют»
    pt   pedía el «que» de «manchas QUE não somem»
    de   «Kopf HART gestoßen»: una palabra en medio rompía «kopf gestoßen»
    ar   el dolor se dice con verbo («يؤلمه») y la barriga con posesivo, sin artículo
    pt   «dói» es el verbo, y el patrón solo conocía el sustantivo «dor»

Las tres primeras son la prueba del vaso, o sea el signo del meningococo, en tres idiomas.

La segunda mitad del fichero pesa igual: al ensanchar patrones para que alcancen entre mensajes,
lo primero que hay que comprobar es que el resultado TRANQUILIZADOR de la misma comprobación
siga en rutina.
"""

from __future__ import annotations

import pytest

from pedibot.eval import fake_engine_from_settings

IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


@pytest.fixture(scope="module")
def engine():
    return fake_engine_from_settings()


def conversa(eng, turnos, lang):
    hist, salida = [], []
    for t in turnos:
        a = eng.ask(t, lang=lang, history=list(hist))
        salida.append(a.level)
        hist.append({"role": "user", "text": t})
        hist.append({"role": "assistant", "text": a.text})
    return salida


#: El resultado BUENO de la misma comprobación, que se redacta con las mismas palabras que el
#: malo y por eso es donde un patrón ensanchado se rompe primero.
TRANQUILIZADORES = [
    ("de", "sie hat einen Ausschlag, der beim Drücken verschwindet"),
    ("ru", "сыпь бледнеет при надавливании"),
    ("pt", "tem manchinhas que somem quando aperto"),
    ("es", "le han salido manchas y desaparecen al apretar"),
    ("de", "er hat sich am Arm gestoßen und danach gegessen"),
    ("pt", "a barriga está boa, dói o braço direito"),
    ("ar", "يؤلمه ذراعه الأيمن"),
]


CASOS = [
    (
        "manchas → no desaparecen",
        {
            "en": ("she has red spots on her tummy", "they don't fade when I press them"),
            "es": ("le han salido unas manchas rojas en la tripa", "no desaparecen cuando aprieto"),
            "fr": (
                "elle a des taches rouges sur le ventre",
                "elles ne disparaissent pas quand j'appuie",
            ),
            "de": ("sie hat rote Flecken am Bauch", "sie verschwinden nicht beim Draufdrücken"),
            "ru": ("у неё красные пятна на животе", "они не бледнеют при надавливании"),
            "ar": ("عندها بقع حمراء على البطن", "لا تختفي عند الضغط عليها"),
            "pt": ("ela tem manchas vermelhas na barriga", "não somem quando aperto"),
            "hi": ("उसके पेट पर लाल दाने हैं", "दबाने पर नहीं मिटते"),
        },
    ),
    (
        "golpe en la cabeza → vomita",
        {
            "en": ("he hit his head hard", "now he has vomited twice"),
            "es": ("se ha dado un golpe fuerte en la cabeza", "ahora ha vomitado dos veces"),
            "fr": ("il s'est cogné fort la tête", "maintenant il a vomi deux fois"),
            "de": ("er hat sich den Kopf hart gestoßen", "jetzt hat er zweimal erbrochen"),
            "ru": ("он сильно ударился головой", "теперь его дважды вырвало"),
            "ar": ("ارتطم رأسه بقوة", "الآن تقيأ مرتين"),
            "pt": ("ele bateu a cabeça com força", "agora vomitou duas vezes"),
            "hi": ("उसके सिर पर ज़ोर से चोट लगी", "अब दो बार उल्टी की"),
        },
    ),
    (
        "bebé de 2 meses → fiebre",
        {
            "en": ("I have a 2-month-old baby", "now he has a fever of 38.5"),
            "es": ("tengo un bebé de 2 meses", "ahora tiene 38,5 de fiebre"),
            "fr": ("j'ai un bébé de 2 mois", "maintenant il a 38,5 de fièvre"),
            "de": ("ich habe ein 2-monatiges Baby", "jetzt hat es 38,5 Fieber"),
            "ru": ("у меня ребёнок 2 месяцев", "сейчас температура 38,5"),
            "ar": ("عندي طفل عمره شهران", "الآن حرارته 38.5"),
            "pt": ("tenho um bebê de 2 meses", "agora está com 38,5 de febre"),
            "hi": ("मेरा 2 महीने का बच्चा है", "अब उसे 38.5 बुखार है"),
        },
    ),
    (
        "barriga → lado derecho",
        {
            "en": (
                "his tummy has been hurting since this morning",
                "now it hurts more on the right side",
            ),
            "es": (
                "le duele la barriga desde esta mañana",
                "ahora le duele más en el lado derecho",
            ),
            "fr": (
                "il a mal au ventre depuis ce matin",
                "maintenant ça fait plus mal du côté droit",
            ),
            "de": (
                "er hat seit heute Morgen Bauchschmerzen",
                "jetzt tut es mehr auf der rechten Seite weh",
            ),
            "ru": ("у него болит живот с утра", "теперь болит сильнее справа"),
            "ar": ("يؤلمه بطنه منذ الصباح", "الآن الألم أكثر في الجهة اليمنى"),
            "pt": ("a barriga dele dói desde de manhã", "agora dói mais do lado direito"),
            "hi": ("सुबह से उसके पेट में दर्द है", "अब दाहिनी ओर ज़्यादा दर्द है"),
        },
    ),
]

TRANQUILAS = [
    (
        "catarro → duda",
        {
            "en": (
                "my child has a runny nose and a mild cough",
                "can I give him something to sleep better?",
            ),
            "es": ("mi hijo tiene mocos y algo de tos", "¿le puedo dar algo para dormir mejor?"),
            "fr": (
                "mon enfant a le nez qui coule et un peu de toux",
                "puis-je lui donner quelque chose ?",
            ),
            "de": (
                "mein Kind hat Schnupfen und etwas Husten",
                "kann ich ihm etwas zum Schlafen geben?",
            ),
            "ru": ("у ребёнка насморк и небольшой кашель", "можно дать что-нибудь на ночь?"),
            "ar": ("طفلي عنده زكام وسعال خفيف", "هل أعطيه شيئا لينام؟"),
            "pt": ("meu filho está com coriza e tosse leve", "posso dar algo para dormir melhor?"),
            "hi": ("मेरे बच्चे को नाक बह रही है और हल्की खाँसी है", "क्या सोने के लिए कुछ दे सकते हैं?"),
        },
    ),
]


@pytest.mark.parametrize(
    ("nombre", "lang", "turnos"),
    [(n, lg, por[lg]) for n, por in CASOS for lg in IDIOMAS],
)
def test_a_two_message_warning_sign_survives_in_every_language(
    engine, nombre: str, lang: str, turnos: tuple[str, str]
) -> None:
    niveles = conversa(engine, turnos, lang)
    assert niveles[-1] != "routine", (
        f"[{lang}] {nombre}: «{turnos[0]}» → «{turnos[1]}» acaba en {niveles[-1]}"
    )


@pytest.mark.parametrize(
    ("nombre", "lang", "turnos"),
    [(n, lg, por[lg]) for n, por in TRANQUILAS for lg in IDIOMAS],
)
def test_an_ordinary_conversation_stays_ordinary_in_every_language(
    engine, nombre: str, lang: str, turnos: tuple[str, str]
) -> None:
    niveles = conversa(engine, turnos, lang)
    assert all(n == "routine" for n in niveles), f"[{lang}] {nombre}: {niveles}"


@pytest.mark.parametrize(("lang", "frase"), TRANQUILIZADORES)
def test_the_reassuring_result_of_a_check_is_not_an_alarm(lang: str, frase: str) -> None:
    """Un padre que hace la prueba del vaso y cuenta que sale BIEN no puede recibir un aviso de
    urgencias: es la forma más rápida de enseñarle a ignorarlos."""
    import pathlib as _p

    from pedibot.bot.triage import Triage

    raiz = _p.Path(__file__).resolve().parents[1]
    assert Triage(raiz / "config" / "red_flags.yaml").assess(frase).level == "routine", (
        f"[{lang}] «{frase}» da la alarma"
    )
