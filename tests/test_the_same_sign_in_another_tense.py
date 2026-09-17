"""La misma señal, en otro tiempo y en otra boca (17-sep-2026).

Todas las medidas anteriores preguntan por la SEÑAL. Ésta pregunta por el marco, que es lo que
hace que la misma frase signifique cosas contrarias:

    «está convulsionando»                   → emergencia
    «tuvo una convulsión hace dos años»      → un antecedente que el padre cuenta de paso
    «¿qué hago si le da una convulsión?»     → una pregunta de preparación, que uno hace
                                               justamente CUANDO NO está pasando

De 31 frases así, **20 salían mal**: el pasado lejano y el condicional disparaban el aviso rojo en
las nueve lenguas probadas. Un padre que pregunta «¿qué hago si se atraganta?» y recibe un «llama
al 112 ahora» aprende en un segundo que el rojo de esta web no significa nada — y ése es el que
algún día será de verdad.

Hay dos guardianes nuevos, `PASADO_REMOTO` y `CONDICIONAL`, con el corte en semanas: lo de hace
horas o días SIGUE saltando, porque «tuvo una convulsión esta mañana» es de hoy.

**Y una decisión que no es un fallo:** preguntar por el hijo de otra persona sigue dando alarma.
Si alguien pregunta por el bebé de su hermana con la fontanela abombada, la respuesta correcta es
la misma —eso hay que verlo— y quien pregunta suele ser justo quien puede llamar. Callarse por
una cuestión de gramática sería el peor de los dos errores.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


#: Está pasando ahora, o ha pasado hoy: tiene que saltar.
AHORA = [
    ('es', 'está convulsionando'),
    ('es', 'acaba de tener una convulsión, hace diez minutos'),
    ('es', 'lleva media hora sin responder'),
    ('en', 'he is having a seizure right now'),
    ('en', 'he had a seizure ten minutes ago'),
    ('de', 'er krampft gerade'),
    ('ar', 'يتشنج الآن'),
    ('es', 'al hijo de mi hermana le dio una convulsión, ¿es grave?'),
    ('en', "my friend's son had a seizure, what does it mean?"),
    ('en', "my sister's baby has a bulging fontanelle, is that bad?"),
    ('es', 'esta mañana tuvo una convulsión'),
    ('es', 'se ha tragado una pila hace un rato'),
    ('en', 'he had a seizure this morning'),
]


@pytest.mark.parametrize("lang,texto", AHORA, ids=lambda x: str(x)[:40])
def test_what_is_happening_now_still_fires(triaje: Triage, lang: str, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level != "routine", f"[{lang}] «{texto}» → rutina"


#: Pasó hace años, o es una pregunta de «¿y si…?»: no puede saltar.
NO_ESTA_PASANDO = [
    ('es', 'tuvo una convulsión hace dos años y nunca se repitió'),
    ('es', 'de bebé tuvo una bronquiolitis con dificultad para respirar'),
    ('es', 'el año pasado se tragó una pila y todo salió bien'),
    ('en', 'he had a febrile seizure two years ago and never again'),
    ('en', 'she swallowed a battery last year and was fine'),
    ('fr', 'il a fait une convulsion il y a deux ans'),
    ('de', 'er hatte vor zwei jahren einen fieberkrampf'),
    ('pt', 'teve uma convulsão há dois anos'),
    ('es', '¿qué hago si le da una convulsión?'),
    ('es', '¿qué tengo que hacer si se atraganta?'),
    ('en', 'what should I do if he has a seizure?'),
    ('en', 'what do I do if my baby chokes?'),
    ('fr', "que faire s'il fait une convulsion ?"),
    ('de', 'was mache ich, wenn er einen krampfanfall hat?'),
    ('ru', 'что делать, если у ребёнка судороги?'),
    ('ar', 'ماذا أفعل إذا أصيب بتشنج؟'),
    ('hi', 'अगर दौरा पड़े तो क्या करूँ?'),
]


@pytest.mark.parametrize("lang,texto", NO_ESTA_PASANDO, ids=lambda x: str(x)[:40])
def test_what_is_not_happening_stays_quiet(triaje: Triage, lang: str, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", f"[{lang}] «{texto}» → {r.level} {[m.id for m in r.matched]}"


#: Y el corte del tiempo, que es lo delicado: semanas atrás no, horas atrás sí.
EL_CORTE = [
    ("es", "tuvo una convulsión hace dos meses", False),
    ("es", "tuvo una convulsión hace dos horas", True),
    ("es", "se tragó una pila la semana pasada y la echó", False),
    ("es", "se ha tragado una pila hace un rato", True),
    ("en", "he had a seizure last month", False),
    ("en", "he had a seizure an hour ago", True),
]


@pytest.mark.parametrize("lang,texto,debe", EL_CORTE, ids=lambda x: str(x)[:40])
def test_the_line_is_drawn_at_weeks(triaje: Triage, lang: str, texto: str, debe: bool) -> None:
    r = triaje.assess(texto)
    assert (r.level != "routine") == debe, f"[{lang}] «{texto}» → {r.level}"
