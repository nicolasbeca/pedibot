"""Quien pregunta por las vacunas tiene que llegar al calendario, escriba en el alfabeto que sea.

Salió de mirar las 128 consultas de la base — la norma del operador: toda ronda de depuración
empieza por lo que preguntó la gente de verdad. Entre las mal contestadas había una francesa,
«Quels vaccins pour un bébé de 3 mois en France ?», que ya estaba arreglada; y al probar el
detector en los ocho idiomas apareció que **el árabe no llegaba**:

    ما اللقاحات لطفل عمره 3 أشهر     →  no se detectaba
    اللقاحات الواجبة للرضيع          →  no se detectaba

Las raíces árabes vivían dentro de un grupo `\\b(...)\\b`, y `\\b` se define sobre `\\w`: en
«اللقاحات» la raíz لقاح lleva el artículo ال delante y el plural ات detrás, los dos hechos de
caracteres de palabra, así que **no hay ninguna frontera** y el patrón no casa jamás.

Lo llamativo es que **la lección ya estaba aprendida en el mismo fichero**: el devanagari
(`टीक|वैक्सीन`) está fuera del grupo, precisamente por esto. Se arregló para un alfabeto y no para
el otro — el clon podrido de siempre, esta vez entre escrituras. Por eso este candado recorre los
ocho idiomas de golpe: para que el noveno no repita la mitad del trabajo.
"""

from __future__ import annotations

import pytest

from pedibot.bot.answer import SUPPORTED_LANGS
from pedibot.bot.vaccines import is_vaccine_question

#: Una pregunta de vacunas por idioma, escrita como la escribiría un padre — con artículo y en
#: plural donde toca, que es exactamente lo que rompía el árabe.
PREGUNTAS = {
    "es": "¿qué vacunas le tocan a mi bebé de 3 meses?",
    "en": "what vaccines does my 3 month old need?",
    "fr": "Quels vaccins pour un bébé de 3 mois en France ?",
    "de": "welche Impfungen braucht mein Baby mit 3 Monaten?",
    "ru": "какие прививки нужны ребёнку в 3 месяца?",
    "ar": "ما اللقاحات لطفل عمره 3 أشهر؟",
    "pt": "que vacinas para um bebé de 3 meses?",
    "hi": "3 महीने के बच्चे को कौन से टीके लगते हैं?",
}

#: Otras formas naturales en las escrituras donde `\b` no sirve, que es donde se esconden los
#: fallos: artículo, plural y la conjunción «و» pegada delante.
MAS_ARABE = [
    "اللقاحات الواجبة للرضيع",
    "ما هي التطعيمات لطفلي",
    "جدول التطعيمات للأطفال",
    "متى يأخذ طفلي اللقاح",
    "واللقاحات في المغرب",
]

MAS_HINDI = ["बच्चों का टीकाकरण कार्यक्रम", "मेरे बच्चे को कौन सी वैक्सीन चाहिए"]


def test_there_is_a_question_for_every_language() -> None:
    """El candado del candado: un idioma nuevo sin pregunta aquí pasaría sin comprobarse."""
    faltan = [lang for lang in SUPPORTED_LANGS if lang not in PREGUNTAS]
    assert not faltan, f"escribe una pregunta de vacunas en {faltan}"


@pytest.mark.parametrize("lang", sorted(PREGUNTAS))
def test_a_vaccine_question_is_recognised_in_every_language(lang: str) -> None:
    assert is_vaccine_question(PREGUNTAS[lang]), (
        f"[{lang}] no se reconoce como pregunta de vacunas: «{PREGUNTAS[lang]}». "
        "Quien la haga no llegará al calendario de su país."
    )


@pytest.mark.parametrize("pregunta", MAS_ARABE + MAS_HINDI)
def test_the_article_and_the_plural_do_not_hide_the_word(pregunta: str) -> None:
    """`\\b` no vale en árabe ni en devanagari: el artículo y el plural son caracteres de palabra,
    así que la frontera que el patrón busca no existe."""
    assert is_vaccine_question(pregunta), f"no se reconoce: «{pregunta}»"


@pytest.mark.parametrize(
    "pregunta",
    [
        # «حبوب اللقاح» es el POLEN. Una pregunta por la alergia no puede acabar en el calendario
        # de vacunación — y al sacar la raíz del grupo con fronteras, empezaba a casar.
        "ابني عنده حساسية من حبوب اللقاح",
        "حساسية حبوب لقاح",
        "ابني عنده حمى وسعال",
        "mi hijo tiene fiebre",
        "my child has a rash",
    ],
)
def test_a_question_about_something_else_is_left_alone(pregunta: str) -> None:
    assert not is_vaccine_question(pregunta), f"se toma por pregunta de vacunas: «{pregunta}»"


def test_the_scripts_without_word_boundaries_stay_outside_the_boundary_group() -> None:
    """La causa, anclada. Si alguien vuelve a meter el árabe o el devanagari dentro del grupo
    `\\b(...)\\b`, media pregunta deja de detectarse y ningún caso de arriba lo explicaría."""
    import inspect

    from pedibot.bot import vaccines

    fuente = inspect.getsource(vaccines)
    inicio = fuente.index("_VACC = re.compile(")
    cuerpo = fuente[inicio : fuente.index("re.I,", inicio)]
    dentro, _, fuera = cuerpo.partition(r'r")\b"')
    assert "تطعيم" not in dentro, "el árabe ha vuelto dentro del grupo con fronteras de palabra"
    assert "टीक" not in dentro, "el devanagari ha vuelto dentro del grupo"
    assert "تطعيم" in fuera and "टीक" in fuera, "las raíces no latinas ya no están fuera"
