"""«Er kann nicht atmen» daba RUTINA (18-sep-2026).

L173 lo dejó escrito en su día: **la negación puede SER la señal**. «No puede respirar» no es la
ausencia de un problema respiratorio: es el problema. Los patrones castellano, inglés y francés
lo tenían resuelto porque EMPIEZAN por la negación —«no puede respirar», «cannot breathe», «ne
peut pas respirer»— y el guardián respeta eso a propósito.

En alemán el verbo se va al final y la negación queda en medio: «er kann NICHT atmen». El patrón
casaba «atmen», el guardián veía el «nicht» delante y callaba la regla. La frase más urgente que
un padre alemán puede escribir daba rutina, y con ella «er kann nicht atmen und wird blau».

Se encontró barriendo esa familia —la negación como señal— en las cuatro lenguas que colocan la
negación de otra manera. De 18 frases, 3 estaban calladas: el alemán del que no respira, el
alemán del que no toma nada, el árabe del que no se despierta y el árabe de la sangre que no para.

Esta prueba las fija. Y las de abajo son el control: las mismas palabras sin la urgencia siguen
siendo rutina, porque un patrón que lleva la negación dentro es justo el que puede empezar a
saltar de más.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: (idioma, frase, regla que tiene que saltar). La negación es parte de la señal.
NEGACION_ES_SENAL = [
    ("de", "er kann nicht atmen", "severe_breathing"),
    ("de", "er kann nicht atmen und wird blau", "severe_breathing"),
    ("de", "sie kann kaum atmen", "severe_breathing"),
    ("de", "das baby atmet nicht mehr", "severe_breathing"),
    ("de", "er hört auf zu atmen", "severe_breathing"),
    ("de", "er kriegt keine luft", "severe_breathing"),
    ("de", "sie trinkt nichts mehr", "unable_to_drink_or_feed"),
    ("de", "er isst und trinkt nichts", "unable_to_drink_or_feed"),
    ("de", "er kann den arm nicht bewegen", "neuro_deficit"),
    ("de", "er wacht nicht auf", "not_responding"),
    ("de", "die blutung hört nicht auf", "severe_bleeding"),
    ("de", "er kann den kopf nicht beugen", "neck_stiffness"),
    ("ru", "он не может дышать", "severe_breathing"),
    ("ru", "он не просыпается", "not_responding"),
    ("ru", "кровь не останавливается", "severe_bleeding"),
    ("ru", "он не может пить", "unable_to_drink_or_feed"),
    ("ar", "لا يستطيع التنفس", "severe_breathing"),
    ("ar", "لا يستيقظ", "not_responding"),
    ("ar", "الدم لا يتوقف", "severe_bleeding"),
    ("ar", "لا يستطيع الشرب", "unable_to_drink_or_feed"),
    ("hi", "वह साँस नहीं ले पा रहा", "severe_breathing"),
    ("hi", "वह जाग नहीं रहा", "not_responding"),
    ("hi", "खून नहीं रुक रहा", "severe_bleeding"),
    ("es", "no puede respirar", "severe_breathing"),
    ("en", "he cannot breathe", "severe_breathing"),
    ("fr", "il ne peut pas respirer", "severe_breathing"),
    ("pt", "não consegue respirar", "severe_breathing"),
    ("sw", "hawezi kupumua", "severe_breathing"),
]

#: Y el control: las mismas palabras cuando NO son una urgencia.
NO_ES_SENAL = [
    ("de", "er atmet ruhig und schläft"),
    ("de", "er kann nicht schlafen"),
    ("de", "er trinkt gut und isst"),
    ("de", "kann mein kind mit fieber baden"),
    ("ar", "الدم توقف"),
    ("ru", "он хорошо пьёт и ест"),
    ("es", "respira bien y no tiene fiebre"),
    ("en", "he is breathing normally"),
]


@pytest.mark.parametrize("lang,texto,regla", NEGACION_ES_SENAL, ids=lambda x: str(x)[:30])
def test_the_negation_carries_the_alarm(triaje: Triage, lang: str, texto: str, regla: str) -> None:
    ids = [m.id for m in triaje.assess(texto).matched]
    assert regla in ids, (
        f"[{lang}] «{texto}» → {ids or 'nada'}. La negación es la señal, no su contrario (L173)."
    )


@pytest.mark.parametrize("lang,texto", NO_ES_SENAL, ids=lambda x: str(x)[:30])
def test_the_same_words_without_the_emergency_stay_quiet(
    triaje: Triage, lang: str, texto: str
) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", f"[{lang}] «{texto}» → {r.level} por {[m.id for m in r.matched]}"


#: Y la versión sistemática: doce reglas donde un padre dice la urgencia EN NEGATIVO, en las
#: nueve lenguas. 108 frases.
#:
#: El primer intento de hacer esto mecánico —mirar qué patrones llevan una negación dentro—
#: se descartó al validarlo: el patrón inglés es `can(?:'?t| ?not) breathe` y la palabra
#: «cannot» no aparece literal, así que el análisis estático daba falsos avisos en 35 reglas
#: (L148: la medición se comprueba antes de creerla). Escribir las frases es más lento y es lo
#: que encuentra los fallos: **21 de 108 no saltaban**, entre ellas una herida que no deja de
#: sangrar en inglés y en francés.
EN_NEGATIVO: dict[str, dict[str, str]] = {
    "cannot_swallow_drooling": {
        "es": "no puede tragar y babea mucho",
        "en": "he cannot swallow and is drooling",
        "fr": "il ne peut pas avaler et bave beaucoup",
        "de": "er kann nicht schlucken und sabbert",
        "ru": "он не может глотать и течёт слюна",
        "ar": "لا يستطيع البلع ويسيل لعابه",
        "pt": "não consegue engolir e baba muito",
        "hi": "वह निगल नहीं पा रहा और लार बह रही है",
        "sw": "hawezi kumeza na anadondosha mate",
    },
    "spinal_injury": {
        "es": "se cayó y no mueve las piernas",
        "en": "he fell and is not moving his legs",
        "fr": "il est tombé et ne bouge plus les jambes",
        "de": "er ist gestürzt und bewegt die beine nicht",
        "ru": "он упал и не двигает ногами",
        "ar": "سقط ولا يحرك رجليه",
        "pt": "caiu e não mexe as pernas",
        "hi": "वह गिरा और पैर नहीं हिला रहा",
        "sw": "ameanguka na hasogezi miguu",
    },
    "asthma_not_responding": {
        "es": "el inhalador no le hace nada",
        "en": "the inhaler is not working",
        "fr": "la ventoline ne fait plus rien",
        "de": "das spray hilft nicht mehr",
        "ru": "ингалятор не помогает",
        "ar": "البخاخ لا ينفع",
        "pt": "a bombinha não está a fazer efeito",
        "hi": "इन्हेलर काम नहीं कर रहा",
        "sw": "dawa ya pumzi haifanyi kazi",
    },
    "vomits_everything": {
        "es": "no retiene nada, lo vomita todo",
        "en": "he keeps nothing down, he vomits everything",
        "fr": "il ne garde rien, il vomit tout",
        "de": "er behält nichts bei sich und erbricht alles",
        "ru": "ничего не удерживает, всё рвёт",
        "ar": "لا يبقي شيئا في معدته ويتقيأ كل شيء",
        "pt": "não retém nada, vomita tudo",
        "hi": "कुछ भी नहीं रुक रहा, सब उल्टी कर देता है",
        "sw": "hakibaki chochote tumboni, anatapika kila kitu",
    },
    "newborn_refusing_feeds": {
        "es": "mi recién nacido rechaza el pecho desde ayer",
        "en": "my newborn is refusing feeds since yesterday",
        "fr": "le nouveau-né refuse le sein depuis hier",
        "de": "das neugeborene verweigert die brust seit gestern",
        "ru": "новорождённый отказывается от груди со вчера",
        "ar": "المولود يرفض الرضاعة منذ أمس",
        "pt": "o recém-nascido recusa a mama desde ontem",
        "hi": "नवजात कल से दूध नहीं ले रहा",
        "sw": "mchanga amekataa kunyonya tangu jana",
    },
    "limp_with_fever": {
        "es": "no quiere apoyar la pierna y tiene fiebre",
        "en": "he will not put weight on his leg and has a fever",
        "fr": "il ne veut pas poser la jambe et il a de la fièvre",
        "de": "er will das bein nicht belasten und hat fieber",
        "ru": "он не наступает на ногу и у него температура",
        "ar": "لا يستطيع الدوس على رجله وعنده حمى",
        "pt": "não quer pôr peso na perna e tem febre",
        "hi": "वह पैर नहीं रख पा रहा और बुख़ार है",
        "sw": "hawezi kukanyaga mguu na ana homa",
    },
    "lockjaw_spasms": {
        "es": "no puede abrir la boca",
        "en": "he cannot open his mouth",
        "fr": "il ne peut pas ouvrir la bouche",
        "de": "er kann den mund nicht öffnen",
        "ru": "он не может открыть рот",
        "ar": "لا يستطيع فتح فمه",
        "pt": "não consegue abrir a boca",
        "hi": "वह मुँह नहीं खोल पा रहा",
        "sw": "hawezi kufungua mdomo",
    },
    "drowsy_irritable": {
        "es": "no hay manera de despertarlo",
        "en": "i cannot wake him up",
        "fr": "je n'arrive pas à le réveiller",
        "de": "ich kann ihn nicht wach bekommen",
        "ru": "я не могу его разбудить",
        "ar": "لا أستطيع إيقاظه",
        "pt": "não consigo acordá-lo",
        "hi": "मैं उसे जगा नहीं पा रही",
        "sw": "siwezi kumwamsha",
    },
    "severe_bleeding": {
        "es": "la herida no deja de sangrar",
        "en": "the wound will not stop bleeding",
        "fr": "la plaie ne s'arrête pas de saigner",
        "de": "die wunde hört nicht auf zu bluten",
        "ru": "рана не перестаёт кровоточить",
        "ar": "الجرح لا يتوقف عن النزيف",
        "pt": "a ferida não para de sangrar",
        "hi": "घाव से खून नहीं रुक रहा",
        "sw": "jeraha halikomi kutoka damu",
    },
    "neuro_deficit": {
        "es": "no mueve bien el brazo izquierdo",
        "en": "he is not moving his left arm properly",
        "fr": "il ne bouge plus bien le bras gauche",
        "de": "er bewegt den linken arm nicht richtig",
        "ru": "он не двигает левой рукой",
        "ar": "لا يحرك ذراعه اليسرى",
        "pt": "não mexe bem o braço esquerdo",
        "hi": "वह बायाँ हाथ ठीक से नहीं हिला रहा",
        "sw": "hawezi kusogeza mkono wa kushoto",
    },
    "neck_stiffness": {
        "es": "no puede doblar el cuello",
        "en": "he cannot bend his neck",
        "fr": "il ne peut pas plier le cou",
        "de": "er kann den kopf nicht beugen",
        "ru": "он не может согнуть шею",
        "ar": "لا يستطيع ثني رقبته",
        "pt": "não consegue dobrar o pescoço",
        "hi": "वह गर्दन नहीं झुका पा रहा",
        "sw": "hawezi kuinamisha shingo",
    },
    "not_responding": {
        "es": "no responde cuando le hablo",
        "en": "he is not responding when i talk to him",
        "fr": "il ne répond plus quand je lui parle",
        "de": "er reagiert nicht wenn ich mit ihm spreche",
        "ru": "он не реагирует когда я с ним говорю",
        "ar": "لا يستجيب عندما أكلمه",
        "pt": "não responde quando falo com ele",
        "hi": "वह बुलाने पर जवाब नहीं दे रहा",
        "sw": "hajibu ninapomwita",
    },
}


def _nivel_de(regla: str) -> str:
    import yaml

    reglas = yaml.safe_load((RAIZ / "config" / "red_flags.yaml").read_text(encoding="utf-8"))
    return next(r["level"] for r in reglas["rules"] if r["id"] == regla)


@pytest.mark.parametrize(
    "regla,lang,texto",
    [(r, lg, f) for r, fr in EN_NEGATIVO.items() for lg, f in fr.items()],
    ids=lambda x: str(x)[:30],
)
def test_the_urgency_said_in_the_negative_still_fires(
    triaje: Triage, regla: str, lang: str, texto: str
) -> None:
    """Vale la regla escrita o cualquier otra de nivel igual o mayor: «no consigo despertarlo»
    puede leerse como somnolencia o como que no responde, y la segunda es más grave. Lo que no
    vale es el silencio."""
    orden = {"routine": 0, "mental_health": 1, "urgent": 2, "emergency": 3}
    r = triaje.assess(texto)
    ids = [m.id for m in r.matched]
    assert regla in ids or orden[r.level] >= orden[_nivel_de(regla)], (
        f"[{lang}] «{texto}» → {ids or 'nada'} ({r.level})"
    )
