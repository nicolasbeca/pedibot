"""Las alarmas dichas como las dice un padre (5-oct-2026).

La batería escrita con el reparto de las consultas reales —sobre todo inglés de EE. UU., y
quince preguntas llanas por lengua— sacó seis señales de alarma que salían sin aviso. Las reglas
existían, pero pedían la forma de libro: «saans lene mein dikkat» y no «saas lene me taklif»,
«no apoya» y no «no puede apoyar», «طاح… راسه… يستفرغ» y no «قشع مرتين بعد ما طاح», y «anything»
donde el padre escribe «water» o «even small sips».
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.triage import Triage

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


@pytest.mark.parametrize(
    ("frase", "nivel"),
    [
        ("mon fils dort tout le temps et n arrive pas à ouvrir les yeux", "emergency"),
        ("mon fils dort tout le temps et n'arrive pas à ouvrir les yeux", "emergency"),
        ("bacche ki pasli chal rahi hai aur saas lene me taklif hai", "emergency"),
        ("قشع مرتين بعد ما طاح هل فيه خطر", "urgent"),
        ("my baby has been sick 4 times today and won't keep water down", "urgent"),
        ("my son is vomiting and cant keep even small sips down", "urgent"),
        ("mi hija de 5 años se cayo del brincolin y no puede apoyar el pie", "urgent"),
        # la primera tanda, con el reparto de las consultas reales
        ("no hay quien despierte a mi hijo y respira muy raro", "emergency"),
        ("mi hijo tiene fiebre y rigidez en el cuello", "emergency"),
        ("mi hija tiene fiebre y un sarpullido que no se blanquea al presionarlo", "emergency"),
        ("my son fell yesterday and now he is acting confused", "emergency"),
        ("my son is unusually quiet and I cant get him to respond normally", "emergency"),
        ("mi hija se ha caido de un segundo piso pero parece estar bien", "urgent"),
        ("my child fell from a second story window but seems okay", "urgent"),
        ("my son has severe headache and keeps wanting to sleep", "urgent"),
        ("my 2 week old looks more yellow than yesterday", "urgent"),
        ("my 1 year old has a dry mouth and only peed twice today", "urgent"),
        ("my child is not drinking water and has very little urine", "urgent"),
        ("mon bébé ne fait presque plus pipi aujourd'hui", "urgent"),
        ("मेरे बच्चे ने आज बहुत कम पेशाब किया है", "urgent"),
        ("my baby has been vomiting since yesterday and has fewer wet nappies", "urgent"),
        ("my child says everything looks blurry after getting hit in the face with a ball", "urgent"),
        ("mi bebe se quemo con agua de la tina", "urgent"),
        ("my 2 year old fell off the sofa and was sick once", "urgent"),
        ("my son fell from bed and vomited twice", "urgent"),
        ("mein Kind ist vom Sofa gefallen und hat danach erbrochen", "urgent"),
        ("ele caiu do sofá e vomitou duas vezes", "urgent"),
        ("मेरी बेटी बिस्तर से गिर गई और उसके बाद एक बार उल्टी हुई", "urgent"),
        ("my 2 year old is breathing with his belly moving a lot", "urgent"),
    ],
)
def test_salta(triaje: Triage, frase: str, nivel: str) -> None:
    assert triaje.assess(frase).level == nivel


@pytest.mark.parametrize(
    "frase",
    [
        "my son has pink eye and woke up with his eye stuck shut",
        "mon fils a les yeux collés le matin et n'arrive pas à ouvrir les yeux",
        "can't keep the fever down with paracetamol",
        "je n'arrive pas à le faire dormir",
        "طفلي طاح من السرير وما فيه شي",
        "ابني استفرغ بعد الأكل",
        "my baby fell asleep and was sick on the blanket",
        "my baby is 3 weeks old and has yellow poop",
        "she fell ill yesterday and vomited twice",
        "the ball hit the window",
        "mi hijo tiene un poco de rigidez en el cuello por dormir mal",
    ],
)
def test_no_salta(triaje: Triage, frase: str) -> None:
    assert triaje.assess(frase).level == "routine"
