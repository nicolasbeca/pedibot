"""¿Falta alguna REGLA entera? (17-sep-2026)

Todas las demás pruebas del triaje preguntan lo mismo: ¿reconoce las reglas que tiene? Ésta
pregunta otra cosa, y es la que más encontró en todo el día: **¿tiene las reglas que hacen
falta?** Se le presentan las urgencias pediátricas clásicas tal como las cuenta un padre.

La primera vez, **16 de 21 salían RUTINA**. No eran formas que faltaran dentro de reglas
existentes: eran puertas que no existían. Y dos de las diez preguntas reales que el bot ha
recibido en su vida eran de crup, que era una de ellas.

    crup con estridor      el ruido al coger aire, que es lo que separa el crup leve del grave
    invaginación           llanto a ratos encogiendo las piernas, caca en jalea de grosella
    estenosis de píloro    vómito a chorro tras cada toma en un lactante
    diabetes que debuta    beber mucho, orinar mucho, adelgazar
    cuerpo extraño         la tos que empieza de golpe comiendo un fruto seco
    asma sin respuesta     el inhalador dado y el niño igual
    químico en el ojo      lejía, detergente
    onfalitis              el ombligo rojo y maloliente del recién nacido
    monóxido de carbono    varios en la misma casa con dolor de cabeza y una estufa
    casi ahogamiento       sale del agua y parece bien, y hay que verlo igual

Cada una se escribió con su fuente del corpus y acotada para no convertir en alarma lo corriente:
la tos perruna sola sigue siendo rutina, y el llanto a ratos sin más, también.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


#: (tema, idioma, cómo lo cuenta un padre)
URGENCIAS = [
    ('crup con estridor', 'es', 'mi hijo tiene tos perruna y hace un ruido al coger aire'),
    ('crup con estridor', 'en', 'my child has a barking cough and noisy breathing when he breathes in'),
    ('crup en reposo', 'es', 'le oigo un pitido al respirar incluso cuando está quieto'),
    ('invaginación', 'es', 'llora a ratos y encoge las piernas, y ha hecho caca como jalea de grosella'),
    ('invaginación', 'en', 'he screams in waves and pulls his legs up, and his poo looked like redcurrant jelly'),
    ('píloro', 'es', 'mi bebé de 4 semanas vomita a chorro después de cada toma'),
    ('píloro', 'en', 'my 4 week old vomits like a fountain after every feed'),
    ('diabetes', 'es', 'bebe muchísima agua, orina todo el rato y ha adelgazado'),
    ('diabetes', 'en', 'she is drinking litres of water, weeing constantly and has lost weight'),
    ('aspiración', 'es', 'estaba comiendo frutos secos y le entró una tos de repente'),
    ('aspiración', 'en', 'he was eating peanuts and suddenly started coughing a lot'),
    ('asma', 'es', 'le he dado el ventolín y sigue igual de ahogado'),
    ('asma', 'en', 'I gave him his inhaler and he is still struggling to breathe'),
    ('ojo químico', 'es', 'le ha entrado lejía en el ojo'),
    ('ojo químico', 'en', 'he got bleach in his eye'),
    ('ombligo', 'es', 'el ombligo de mi recién nacido está rojo alrededor y huele mal'),
    ('cannabis', 'es', 'creo que se ha comido una galleta de marihuana y está muy dormido'),
    ('monóxido', 'es', 'nos duele la cabeza a todos en casa desde que encendimos la estufa'),
    ('ahogamiento', 'es', 'se cayó a la piscina y lo sacamos tosiendo'),
    ('ahogamiento', 'en', 'he fell in the pool and we pulled him out coughing'),
    ('control', 'es', 'tiene fiebre y manchas que no desaparecen al presionar'),
]


@pytest.mark.parametrize("tema,lang,texto", URGENCIAS, ids=lambda x: str(x)[:36])
def test_a_classic_emergency_has_a_door(triaje: Triage, tema: str, lang: str, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level != "routine", f"[{lang}] {tema}: «{texto}» → rutina, sin ninguna regla"


#: Y lo que se le parece y NO puede saltar: el crup leve es lo más común de la consulta, y un
#: bebé que llora a ratos es un cólico.
PARECIDOS = [
    ("es", "mi hijo tiene tos perruna desde anoche"),
    ("en", "my son has a barking cough since last night"),
    ("es", "llora a ratos por las tardes, creo que son cólicos"),
    ("es", "regurgita un poco después de cada toma"),
    ("en", "he brings up a little milk after every feed"),
    ("es", "bebe mucha agua porque hace calor"),
    ("es", "se ha manchado la camiseta con lejía"),
    ("en", "he spilled bleach on his t-shirt"),
    ("es", "estuvo en la piscina toda la tarde y está cansado"),
    ("es", "le he dado el ventolín y está mucho mejor"),
]


@pytest.mark.parametrize("lang,texto", PARECIDOS)
def test_what_looks_like_it_but_is_not(triaje: Triage, lang: str, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", f"[{lang}] «{texto}» → {r.level} {[m.id for m in r.matched]}"


# ── y la segunda vuelta: la lista PUBLICADA, no la mía ───────────────────────────────────────
#
# Las de arriba las elegí yo. Éstas salen del índice del capítulo «Urgencias y emergencias» de
# Pediatría. Diagnóstico y tratamiento —que está indexado entero— y de los signos de peligro del
# cuadro IMNCI de la India, que es el que usan media Asia y media África.
#
# **23 de 31 salían rutina.** Entre ellas: la descarga eléctrica, el objeto metido en la nariz,
# la lesión medular tras una caída, el golpe fuerte en el abdomen, el humo de un incendio, los
# moratones sin golpes con palidez (leucemia), la hipoglucemia de un diabético, la crisis de
# drepanocitosis, el recién nacido frío, y tres signos de peligro del IMNCI: no poder beber,
# vomitar todo y los dos pies hinchados.
#
# Y una que se arregló al revés: «está muy delgado, se le marcan las costillas» salía como
# dificultad respiratoria GRAVE, porque esa frase se parece al tiraje. Ahora entra por su puerta
# —la desnutrición visible— y el tiraje sigue entrando por la suya.
PUBLICADA = [
    ('paro cardiorrespiratorio', 'es', 'no respira y no responde, le estoy haciendo boca a boca'),
    ('paro cardiorrespiratorio', 'en', 'he is not breathing and I am doing cpr'),
    ('electricidad', 'es', 'le ha dado la corriente con un enchufe'),
    ('electricidad', 'en', 'he got an electric shock from a socket'),
    ('cuerpo extraño nariz', 'es', 'se ha metido una pipa en la nariz'),
    ('cuerpo extraño oído', 'es', 'se ha metido una bolita en el oído'),
    ('cuerpo extraño nariz', 'en', 'he pushed a bead up his nose'),
    ('traumatismo medular', 'es', 'se cayó de espaldas y no mueve las piernas'),
    ('traumatismo medular', 'en', 'he fell on his back and cannot move his legs'),
    ('traumatismo abdominal', 'es', 'le dio un golpe fuerte en la tripa con el manillar y está pálido'),
    ('traumatismo torácico', 'es', 'recibió un golpe fuerte en el pecho y le cuesta respirar'),
    ('inhalación de humo', 'es', 'ha respirado mucho humo en un incendio'),
    ('inhalación de humo', 'en', 'he breathed in a lot of smoke from a fire'),
    ('oncología', 'es', 'le salen moratones sin darse golpes y está muy pálido y cansado'),
    ('oncología', 'en', 'she has bruises without any knocks and is very pale and tired'),
    ('oncología', 'es', 'le duelen los huesos por la noche y se despierta llorando'),
    ('hipoglucemia', 'es', 'es diabético y está sudoroso, tembloroso y confuso'),
    ('hipoglucemia', 'en', 'he is diabetic and is sweaty, shaky and confused'),
    ('drepanocitosis', 'es', 'tiene anemia falciforme y un dolor muy fuerte en las piernas'),
    ('hipotermia neonatal', 'es', 'mi recién nacido está frío y no entra en calor'),
    ('imnci: no puede beber', 'es', 'no puede beber ni agarrar el pecho'),
    ('imnci: no puede beber', 'en', 'he is unable to drink or breastfeed'),
    ('imnci: vomita todo', 'es', 'vomita todo lo que le doy, no retiene nada'),
    ('imnci: vomita todo', 'en', 'he vomits everything, cannot keep anything down'),
    ('imnci: edema de pies', 'es', 'tiene los dos pies hinchados'),
    ('desnutrición grave', 'es', 'está muy delgado, se le marcan las costillas y no gana peso'),
    ('torsión ovárica', 'es', 'mi hija de 14 años tiene un dolor muy fuerte en el bajo vientre de repente'),
    ('CONTROL +', 'es', 'tiene fiebre y manchas que no desaparecen al presionar'),
]


@pytest.mark.parametrize("tema,lang,texto", PUBLICADA, ids=lambda x: str(x)[:36])
def test_the_published_list_has_a_door_too(triaje: Triage, tema: str, lang: str, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level != "routine", f"[{lang}] {tema}: «{texto}» → rutina, sin ninguna regla"


CONTROLES = [
    ('es', 'se ha dado un golpe en la rodilla jugando y le ha salido un moratón'),
    ('es', 'vomitó una vez después de merendar y ya está bien'),
    ('es', 'mi hijo está delgado pero come bien y crece'),
]


@pytest.mark.parametrize("lang,texto", CONTROLES)
def test_and_what_merely_resembles_them_stays_quiet(triaje: Triage, lang: str, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", f"[{lang}] «{texto}» → {r.level} {[m.id for m in r.matched]}"
