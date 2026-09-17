"""La vida corriente de un niño no puede disparar una alarma (17-sep-2026).

Todo el trabajo del día fue buscar avisos que faltaban: 51 reglas pasaron a 75 y entraron 863
patrones nuevos. Esta prueba es la contraria, y es la que faltaba: **¿dónde salta de más?**

Un triaje que se dispara con todo hace dos daños, y el segundo es peor que el primero: manda a
urgencias a quien no lo necesita, y **enseña al padre a ignorar el aviso rojo** — que es el que
algún día será de verdad.

Dos conjuntos. El primero es la vida corriente: mocos, dientes, un chichón del columpio, la
verdura que no quiere, preguntas de información. El segundo está escrito a propósito para
engañar a las reglas nuevas, pegado a ellas en vocabulario y lejísimos en gravedad. De ése
saltaron siete, y seis eran mías de ese mismo día:

    «a bit of shampoo in his eye»        → mordedura de animal («bit», y «the BATh» daba «bat»)
    «se metió en la bañera él solo»      → casi ahogamiento (meterse en la bañera es bañarse)
    «no juega con los otros niños»       → decaimiento (eso es timidez)
    «no me mira cuando ve los dibujos»   → decaimiento (eso es la televisión)
    «no bebe mucha agua, prefiere leche» → deshidratación (eso es una manía)
    «woke up with a stiff neck»          → meningitis (eso es haber dormido mal)

Y una más que salió al arreglar la anterior: «a bit of THE biscuit fell in the bath» daba casi
ahogamiento, porque «the» contiene «he» y eso bastaba para dar por hecho que el sujeto era el
niño. Fronteras de palabra.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


#: La vida corriente de un niño, en los ocho idiomas.
CORRIENTE = [
    ('es', 'lleva tres días con mocos y tose por la noche'),
    ('es', 'tiene tos seca desde el domingo pero come bien'),
    ('en', 'she has had a runny nose and a cough for three days'),
    ('en', 'he coughs at night but is fine during the day'),
    ('fr', 'il tousse un peu la nuit depuis trois jours'),
    ('de', 'sie hat seit drei tagen schnupfen und hustet nachts'),
    ('ru', 'у неё третий день насморк и кашель по ночам'),
    ('ar', 'عندها زكام وسعال منذ ثلاثة أيام'),
    ('pt', 'tem tosse e ranho há três dias'),
    ('hi', 'तीन दिन से नाक बह रही है और खाँसी है'),
    ('es', 'tiene fiebre desde ayer y está algo apagado pero juega'),
    ('es', 'le ha bajado la fiebre con el antitérmico y está jugando'),
    ('en', 'he has had a fever since yesterday but is playing normally'),
    ('de', 'er hat seit gestern fieber, spielt aber normal'),
    ('pt', 'tem febre desde ontem mas está a brincar'),
    ('es', 'ha vomitado dos veces y ahora está bien, quiere agua'),
    ('es', 'tiene diarrea desde ayer pero bebe bien y hace pis'),
    ('en', 'he has had diarrhoea since yesterday but is drinking well'),
    ('fr', 'il a la diarrhée depuis hier mais il boit bien'),
    ('ru', 'у него понос со вчера, но пьёт хорошо'),
    ('ar', 'عنده إسهال من أمس لكنه يشرب جيدا'),
    ('es', 'se cayó del columpio y le ha salido un chichón, pero está jugando'),
    ('es', 'se dio con la esquina de la mesa y llora pero se calmó enseguida'),
    ('en', 'he bumped his head on the table and cried for a minute, now he is fine'),
    ('de', 'er ist vom sofa gefallen und hat kurz geweint, jetzt spielt er'),
    ('hi', 'वह सोफ़े से गिरा और थोड़ा रोया, अब खेल रहा है'),
    ('es', 'le han salido unos granitos en la cara desde ayer'),
    ('es', 'tiene la piel seca y se rasca las piernas'),
    ('en', 'she has a few spots on her face that fade when I press them'),
    ('fr', 'elle a des boutons sur le visage depuis hier'),
    ('es', 'no quiere comer verdura, solo pasta'),
    ('es', 'se despierta dos veces por la noche a los ocho meses'),
    ('en', 'he only wants pasta and refuses vegetables'),
    ('de', 'sie wacht nachts zweimal auf'),
    ('ar', 'يستيقظ مرتين في الليل'),
    ('hi', 'वह रात में दो बार उठता है'),
    ('es', 'le están saliendo los dientes y babea mucho'),
    ('es', 'tiene el culito irritado del pañal'),
    ('en', 'he is teething and dribbling'),
    ('pt', 'tem a fralda a irritar-lhe o rabinho'),
    ('es', '¿qué es la bronquiolitis?'),
    ('es', '¿cómo evito que se atragante con la comida?'),
    ('es', '¿cuándo empiezo con la alimentación complementaria?'),
    ('en', 'what are the signs of dehydration?'),
    ('en', 'how do I prevent nappy rash?'),
    ('fr', "qu'est-ce que la roséole ?"),
    ('de', 'was ist pseudokrupp?'),
    ('ru', 'что такое ветрянка?'),
    ('ar', 'ما هي الحصبة؟'),
    ('hi', 'रोटावायरस क्या है?'),
    ('es', 'no tiene fiebre ni le cuesta respirar'),
    ('es', 'no le duele nada, solo está resfriado'),
    ('en', 'no fever, no rash, just a cold'),
    ('de', 'kein fieber, keine atemnot'),
    ('fr', 'pas de fièvre, pas de vomissements'),
    ('es', 'mi hija de 15 años está a dieta pero come de todo'),
    ('es', 'mi hijo adolescente duerme mucho los fines de semana'),
    ('es', 'mi hijo está delgado pero come bien y crece'),
    ('es', 'quería saber si es normal que ande de puntillas a veces'),
    ('en', 'is it normal for a toddler to walk on tiptoes sometimes?'),
    ('es', 'se ha manchado la camiseta con lejía'),
    ('es', 'estuvo en la piscina toda la tarde y está cansado'),
    ('es', 'le he dado el ventolín y está mucho mejor'),
    ('en', 'I gave him the inhaler and he is much better now'),
    ('es', 'vomitó una vez después de merendar y ya está bien'),
]


@pytest.mark.parametrize("lang,texto", CORRIENTE, ids=lambda x: str(x)[:40])
def test_an_ordinary_childhood_raises_no_alarm(triaje: Triage, lang: str, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", f"[{lang}] «{texto}» → {r.level} {[m.id for m in r.matched]}"


#: Y lo escrito a propósito para engañar a las reglas nuevas.
TRAMPAS = [
    ('es', 'tos perruna leve que mejora al salir al aire fresco'),
    ('en', 'mild barking cough that gets better outside'),
    ('es', 'llora a ratos por la tarde desde que nació, creo que son cólicos'),
    ('es', 'encoge las piernas cuando le cambio el pañal'),
    ('es', 'echa un poquito de leche después de cada toma, es reflujo'),
    ('en', 'he brings up a little milk after every feed'),
    ('es', 'tiene mucha sed en verano y bebe mucha agua'),
    ('es', 'orina mucho porque le doy mucho zumo'),
    ('es', 'se mete el dedo en la nariz todo el rato'),
    ('es', 'estaba comiendo frutos secos tranquilamente en la merienda'),
    ('es', 'le da corriente el pelo con el jersey de lana'),
    ('es', 'le ha entrado champú en el ojo en la bañera'),
    ('en', 'he got a bit of shampoo in his eye in the bath'),
    ('es', 'estuvo toda la tarde en la piscina y está cansado'),
    ('es', 'se metió en la bañera él solo y se rió'),
    ('es', 'el cordón del ombligo se le está cayendo y está un poco húmedo'),
    ('en', 'the cord stump is drying and about to fall off'),
    ('es', 'tiene moratones en las espinillas de jugar al fútbol'),
    ('es', 'siempre ha sido muy blanquito de piel'),
    ('en', 'he has bruises on his shins from football'),
    ('es', 'es diabético y hoy está estupendo, le toca revisión'),
    ('es', 'se le hincha un pie cuando hace mucho calor'),
    ('es', 'está delgadito pero come bien y sigue su percentil'),
    ('es', 'mi hija de 14 años tiene dolor de regla como todos los meses'),
    ('es', 'no juega con los otros niños en el parque, es tímido'),
    ('es', 'no me mira cuando está viendo los dibujos'),
    ('en', 'he does not look at me when he is watching cartoons'),
    ('es', 'no bebe mucha agua, prefiere la leche'),
    ('en', 'he does not drink much water, he prefers milk'),
    ('es', 'mi hija de 15 años está a dieta pero come de todo'),
    ('es', 'no quiere comer verdura desde que tiene dos años'),
    ('es', 'ha olido el humo del incienso en la iglesia'),
    ('es', 'tiene la mollera blandita, ¿es normal?'),
    ('es', 'vomitó una vez y era la papilla de zanahoria, naranja'),
    ('es', 'se ha levantado con tortícolis de dormir mal'),
    ('en', 'he woke up with a stiff neck from sleeping badly'),
    ('es', 'ronca por la noche desde que está acatarrado'),
    ('es', 'se cayó jugando y se levantó corriendo'),
]


@pytest.mark.parametrize("lang,texto", TRAMPAS, ids=lambda x: str(x)[:40])
def test_what_merely_resembles_an_emergency_stays_quiet(triaje: Triage, lang: str, texto: str):
    r = triaje.assess(texto)
    assert r.level == "routine", f"[{lang}] «{texto}» → {r.level} {[m.id for m in r.matched]}"
