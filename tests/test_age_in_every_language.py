"""La edad, dicha como se dice en cada lengua (8-sep-2026).

Salió de una prueba de punta a punta contra producción: la misma pregunta corriente en los ocho
idiomas, y **el alemán fue el único que contestó preguntando la edad** — que estaba escrita en la
frase. «Meine 3-jährige Tochter hat 38,5 Fieber» devolvía None.

El alemán pega el número a la unidad y le añade la terminación del adjetivo (`3-jährige`,
`2-monatiges`, `achtwöchiges`), y era la única de las ocho lenguas cuya forma natural no estaba
recogida: las demás separan el número de la unidad con un espacio, que es lo que los patrones
esperaban. Con ella se caía también «mein 2-monatiges Baby hat Fieber», o sea la regla del
lactante menor de tres meses en su redacción más normal.

La mitad de abajo importa igual: una edad que nadie ha escrito no puede inventarse. Si el motor
cree saber la edad, la regla del lactante decide con ella.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import parse_age_months

#: Un niño de tres años, en las ocho lenguas y en las formas en que se escribe.
TRES_ANOS = [
    ("en", "my 3-year-old has a fever"),
    ("en", "my daughter is 3 years old"),
    ("es", "mi hija de 3 años tiene fiebre"),
    ("fr", "ma fille de 3 ans a de la fièvre"),
    ("de", "meine 3-jährige Tochter hat Fieber"),
    ("de", "meine dreijährige Tochter hat Fieber"),
    ("de", "mein Kind ist 3 Jahre alt"),
    ("ru", "моей дочери 3 года"),
    ("ar", "ابنتي عمرها 3 سنوات"),
    ("pt", "minha filha de 3 anos está com febre"),
    ("hi", "मेरी 3 साल की बेटी को बुखार है"),
]


@pytest.mark.parametrize(("lang", "pregunta"), TRES_ANOS)
def test_three_years_old_is_read_in_every_language(lang: str, pregunta: str) -> None:
    assert parse_age_months(pregunta) == 36.0, f"[{lang}] «{pregunta}»"


#: Y un lactante de dos meses, que es la edad de la que depende la regla más importante.
DOS_MESES = [
    ("en", "my 2-month-old has a fever"),
    ("en", "my 2 month old baby has a fever"),
    ("es", "mi bebé de 2 meses tiene fiebre"),
    ("fr", "mon bébé de 2 mois a de la fièvre"),
    ("de", "mein 2-monatiges Baby hat Fieber"),
    ("de", "mein Baby ist 2 Monate alt und hat Fieber"),
    ("ru", "моему ребёнку 2 месяца, температура"),
    ("ar", "ابني عمره شهرين وعنده حرارة"),
    ("pt", "meu bebê de 2 meses está com febre"),
    ("hi", "मेरे 2 महीने के बच्चे को बुखार है"),
]


@pytest.mark.parametrize(("lang", "pregunta"), DOS_MESES)
def test_two_months_old_is_read_in_every_language(lang: str, pregunta: str) -> None:
    edad = parse_age_months(pregunta)
    assert edad is not None and edad < 3, f"[{lang}] «{pregunta}» → {edad}"


SIN_EDAD = [
    ("de", "mein Kind ist krank"),
    ("en", "my child is unwell and I don't know what to do"),
    ("es", "mi hijo está malito"),
    ("fr", "mon enfant ne va pas bien"),
    ("ru", "ребёнок плохо себя чувствует"),
    ("ar", "طفلي متعب"),
    ("pt", "meu filho está doente"),
    ("hi", "मेरा बच्चा ठीक नहीं है"),
]


@pytest.mark.parametrize(("lang", "pregunta"), SIN_EDAD)
def test_an_age_nobody_wrote_is_not_invented(lang: str, pregunta: str) -> None:
    """Si el motor cree saber la edad, la regla del lactante decide con ella — y una edad
    inventada decide mal en las dos direcciones."""
    assert parse_age_months(pregunta) is None, f"[{lang}] «{pregunta}»"
