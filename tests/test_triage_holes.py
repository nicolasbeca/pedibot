"""Urgencias dichas como las diría un padre, no como las escribiría un manual (6-sep-2026).

El conjunto dorado iba al 100 % en las seis métricas con cero fallos sobre 111 casos. Un examen
que se aprueba siempre ha dejado de examinar: solo medía lo que ya sabíamos que funcionaba.

Se escribieron 31 preguntas para colarse — la misma urgencia con otras palabras — y **veinte se
colaron**. Ninguna por falta de regla: cada regla casaba solo con la redacción exacta con la que
se escribió.

    estaba:  se le marcan las costillas    se colaba:  se le marcan MUCHO las costillas
    estaba:  doesn't fade                  se colaba:  does NOT fade
    estaba:  manchas que no desaparecen    se colaba:  SARPULLIDO que no desaparece
    estaba:  blaue Lippen                  se colaba:  die Lippen SIND BLAU
    estaba:  swallowed ... battery         se colaba:  swallowed ... batteries

Y la causa más honda no era ningún patrón: la regla del lactante menor de 3 meses exige entender
la edad **y** detectar fiebre, y «está calentita» no contaba como fiebre. Un padre con un bebé de
seis semanas en brazos a las tres de la mañana no escribe «presenta fiebre».

Este fichero es ese examen, para que no se vuelva a estrechar. La otra mitad importa igual: las
preguntas de rutina tienen que seguir saliendo de rutina. Una regla ensanchada que salta con unos
mocos no protege a nadie — enseña a ignorar la alarma, que es peor que no tenerla.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

ROOT = pathlib.Path(__file__).resolve().parents[1]
ORDEN = {"routine": 0, "mental_health": 1, "urgent": 2, "emergency": 3}


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


#: (pregunta, idioma, nivel MÍNIMO aceptable). Cada una se coló alguna vez.
DEBEN_SALTAR = [
    # emergencias, dichas sin la palabra del manual
    ("tiene los labios azulados", "es", "emergency"),
    ("his lips look blue", "en", "emergency"),
    ("die Lippen sind blau", "de", "emergency"),
    ("se le marcan mucho las costillas al respirar", "es", "emergency"),
    ("I can see his ribs pulling in when he breathes", "en", "emergency"),
    ("le ha salido un sarpullido que no desaparece al apretarlo con un vaso", "es", "emergency"),
    ("he has a rash that does not fade when I press a glass on it", "en", "emergency"),
    ("se ha quedado rígido y con los ojos en blanco un momento", "es", "emergency"),
    ("está muy flojito y no responde igual que siempre", "es", "emergency"),
    ("lleva dormido desde ayer y no se despierta ni para comer", "es", "emergency"),
    # la pila de botón: quema el esófago en horas, y estaba con las monedas en «urgente»
    ("se ha tragado una pila de las redondas", "es", "emergency"),
    ("he swallowed one of those flat round batteries", "en", "emergency"),
    # fiebre en un lactante muy pequeño, sin termómetro delante
    ("mi hija de 6 semanas está calentita y no quiere comer", "es", "urgent"),
    ("my 7 week old feels hot and is feeding badly", "en", "urgent"),
    ("mi bebé de 2 meses tiene 38 de fiebre", "es", "urgent"),
    ("mein Baby ist 6 Wochen alt und hat Fieber", "de", "urgent"),
    ("mon bébé de 5 semaines a de la fièvre", "fr", "urgent"),
    # veneno: en casa nada se llama por su nombre químico
    ("mi hijo se ha bebido algo del armario de la limpieza", "es", "urgent"),
    # ideación suicida, que casi nunca se dice con esas palabras
    ("mi hija de 14 dice que no quiere seguir aquí", "es", "mental_health"),
    ("my teenager said she would be better off gone", "en", "mental_health"),
    ("mi hijo adolescente se hace cortes en los brazos", "es", "mental_health"),
]

#: La otra mitad: esto es rutina y tiene que seguir siéndolo.
NO_DEBEN_SALTAR = [
    ("mi hijo de 4 años tiene mocos", "es"),
    ("cuándo empiezo con la fruta", "es"),
    ("qué vacunas le tocan a los 12 meses", "es"),
    ("le están saliendo los dientes y babea mucho", "es"),
    ("my toddler has a runny nose", "en"),
    ("cuánto paracetamol le doy si pesa 14 kg", "es"),
    ("a qué edad empiezan a andar", "es"),
]


@pytest.mark.parametrize(("pregunta", "lang", "minimo"), DEBEN_SALTAR)
def test_an_emergency_in_a_parents_words_still_raises_the_alarm(
    triage: Triage, pregunta: str, lang: str, minimo: str
) -> None:
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, -1) >= ORDEN[minimo], (
        f"[{lang}] «{pregunta}» sale {nivel} y debería ser al menos {minimo}"
    )


@pytest.mark.parametrize(("pregunta", "lang"), NO_DEBEN_SALTAR)
def test_an_ordinary_question_does_not_raise_an_alarm(
    triage: Triage, pregunta: str, lang: str
) -> None:
    """Media hora antes de escribir esto se ensancharon seis reglas. Una alarma que salta con unos
    mocos enseña a ignorarla, y entonces no salta cuando importa."""
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, 9) < ORDEN["urgent"], f"[{lang}] falsa alarma en «{pregunta}»: {nivel}"


#: Lo que la hoja «Dolor abdominal» de la SEUP (2025) enumera como motivo de consulta, y que el
#: triaje no miraba: las cuatro salían RUTINA el 6-sep-2026, estando escritas en un documento que
#: la web ya cita. Se encontraron preguntando al corpus por los cinco umbrales que el operador
#: quería revisar — tres de los cinco cambiaron de respuesta al leer la fuente, y estas cuatro no
#: las había preguntado nadie.
DE_LA_HOJA_SEUP = [
    ("vomita verde", "es", "urgent"),
    ("está vomitando algo verdoso", "es", "urgent"),
    ("he vomited something green", "en", "urgent"),
    ("ha vomitado con sangre", "es", "urgent"),
    ("hace caca negra como alquitrán", "es", "urgent"),
    ("tiene sangre roja en la caca", "es", "urgent"),
    ("there is blood in his poo", "en", "urgent"),
    ("le duele mucho la tripa en el lado derecho al saltar", "es", "urgent"),
    ("my son has stomach pain on the right side", "en", "urgent"),
    ("le duele la tripa cada vez más y no puede dormir", "es", "urgent"),
    # y la hoja de trastornos de la conducta alimentaria, en nivel de aviso, no de alarma roja
    ("mi hija de 15 años se salta las comidas y se obsesiona con el peso", "es", "mental_health"),
    ("vomita después de comer para no engordar", "es", "mental_health"),
]

#: Las trampas de esas mismas reglas. Un niño que no come verdura y un bebé que devuelve la toma
#: son el pan de cada día; si esto salta, la alarma deja de significar nada.
NI_SE_LE_OCURRA = [
    ("le duele un poco la tripa", "es"),
    ("mi hijo no come verdura", "es"),
    ("my toddler will not eat his vegetables", "en"),
    ("mi bebé ha vomitado la toma", "es"),
    ("le está saliendo un diente", "es"),
]


@pytest.mark.parametrize(("pregunta", "lang", "minimo"), DE_LA_HOJA_SEUP)
def test_what_our_own_source_lists_as_a_reason_to_consult(
    triage: Triage, pregunta: str, lang: str, minimo: str
) -> None:
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, -1) >= ORDEN[minimo], (
        f"[{lang}] «{pregunta}» sale {nivel}; la hoja de la SEUP lo lista como motivo de consulta"
    )


@pytest.mark.parametrize(("pregunta", "lang"), NI_SE_LE_OCURRA)
def test_the_everyday_version_of_those_same_rules_stays_quiet(
    triage: Triage, pregunta: str, lang: str
) -> None:
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, 9) < ORDEN["urgent"], f"[{lang}] falsa alarma en «{pregunta}»: {nivel}"


#: Del barrido completo de los 161 trozos marcados como signos de alarma en el índice (6-sep-2026).
#: Lo más grave: «pérdida de conciencia» y «perdió el conocimiento» NO figuraban en español, ni
#: «lost consciousness» en inglés — solo «inconsciente», «unconscious» y el francés «perte de
#: connaissance». Y no había ninguna regla de signos neurológicos, que la hoja de cefalea de la
#: SEUP enumera: «ve mal, no mueve bien los brazos o las piernas, camina o habla con dificultad».
DEL_BARRIDO = [
    ("dice que ve mal y le cuesta hablar", "es", "emergency"),
    ("no mueve bien un brazo desde esta mañana", "es", "emergency"),
    ("camina con dificultad y arrastra una pierna", "es", "emergency"),
    ("está desorientado y no sabe dónde está", "es", "emergency"),
    ("he cannot move his arm properly and his speech is slurred", "en", "emergency"),
    ("duerme mucho más de lo habitual y es difícil despertarle", "es", "urgent"),
    ("el dolor de cabeza le despierta por la noche", "es", "urgent"),
]

#: Las trampas de las reglas neurológicas. Un bebé de doce meses que no camina bien y una niña que
#: necesita gafas son lo normal; si esto salta, la regla sobra.
NEURO_TRAMPAS = [
    ("mi bebé de 12 meses todavía no camina bien", "es"),
    ("mi hijo de 2 años habla poco todavía", "es"),
    ("mi hija necesita gafas, ve mal de lejos", "es"),
    ("mi hijo duerme mucho, es un dormilón", "es"),
    ("le duele un poco la cabeza", "es"),
]


@pytest.mark.parametrize(("pregunta", "lang", "minimo"), DEL_BARRIDO)
def test_the_warning_signs_the_sweep_found(
    triage: Triage, pregunta: str, lang: str, minimo: str
) -> None:
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, -1) >= ORDEN[minimo], f"[{lang}] «{pregunta}» sale {nivel}"


@pytest.mark.parametrize(("pregunta", "lang"), NEURO_TRAMPAS)
def test_normal_development_is_not_a_neurological_sign(
    triage: Triage, pregunta: str, lang: str
) -> None:
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, 9) < ORDEN["urgent"], f"[{lang}] falsa alarma en «{pregunta}»: {nivel}"


@pytest.mark.parametrize(
    "pregunta",
    [
        "se ha desmayado en el colegio, tiene 12 años",
        "mi hija se desmayó al levantarse de golpe",
        "he fainted during assembly at school",
    ],
)
def test_a_plain_faint_is_not_an_emergency(triage: Triage, pregunta: str) -> None:
    """Se probó meterlo en `not_responding` el 6-sep-2026 y la precisión de las alarmas cayó de
    1.0 a 0.978. La hoja de síncope de la SEUP dice que «en general no se producen por problemas
    médicos importantes» y define el síncope como «una pérdida de conocimiento de forma brusca y
    de corta duración» — exactamente las palabras que se habían añadido.

    `not_responding` es para quien NO responde AHORA. Un niño que se desmayó y se recuperó es
    otra cosa, y tratarlo de emergencia manda a urgencias a quien no lo necesita."""
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, 9) < ORDEN["emergency"], f"«{pregunta}» sale {nivel}"


#: La peor clase de fallo de esta capa. Encontrado cruzando la hoja /emergency con el triaje: uno
#: de sus puntos de nivel «no urgente» es «Tos o mocos SIN dificultad para respirar», y el chat lo
#: devolvía como EMERGENCIA. Un padre que dice explícitamente que su hijo respira bien recibía una
#: alarma roja — no se pierde una urgencia, se enseña a ignorar la alarma.
NEGADAS = [
    ("tiene tos y mocos pero sin dificultad para respirar", "es"),
    ("tose mucho pero no tiene dificultad para respirar", "es"),
    ("está bien, no le cuesta respirar", "es"),
    ("no tiene fiebre ni le cuesta respirar", "es"),
    ("he has a cough but no difficulty breathing", "en"),
    ("Husten aber keine Atemnot", "de"),
]

#: La otra mitad, y la que hace que la regla anterior sea segura: una negación que iba con OTRA
#: cosa no puede apagar la señal. «sin fiebre PERO le cuesta respirar» afirma la segunda mitad.
NEGADAS_PERO_NO = [
    ("sin fiebre pero le cuesta mucho respirar", "es", "emergency"),
    ("no tiene fiebre pero se le marcan las costillas", "es", "emergency"),
    ("sin manchas pero no responde", "es", "emergency"),
    ("kein Fieber aber die Lippen sind blau", "de", "emergency"),
    # y los patrones que EMPIEZAN por una negación tienen que seguir saltando
    ("no responde a estímulos", "es", "emergency"),
    ("no deja de sangrar", "es", "emergency"),
    ("no puede respirar", "es", "emergency"),
    ("no se despierta", "es", "emergency"),
]

#: Variantes de forma que no casaban. «cannot» no aparecía en NINGUNA regla inglesa: todas
#: escriben `can't`, que cubre «can't» y «cant» pero no «cannot» ni «can not». Sin respirar, sin
#: dejar de sangrar, sin despertarse — las tres salían rutina por una apóstrofe.
VARIANTES = [
    ("he cannot breathe", "en", "emergency"),
    ("she cannot stop bleeding", "en", "emergency"),
    ("he cannot wake up", "en", "emergency"),
    # la hoja de la SEUP dice «pérdida de conocimiento»; la regla pedía el verbo «perdió»
    ("se cayó y tuvo una pérdida de conocimiento", "es", "emergency"),
    ("se dio un golpe en la cabeza con pérdida de conocimiento", "es", "emergency"),
    # también de la hoja, y sin regla
    ("le noto pérdida de fuerza en un lado", "es", "emergency"),
    ("tiene un sangrado abundante que no cede", "es", "emergency"),
    ("está con una somnolencia excesiva", "es", "urgent"),
    # la edad de un recién nacido se dice en semanas, y en letra
    ("mi bebé de tres semanas tiene fiebre", "es", "urgent"),
    ("my six week old has a fever", "en", "urgent"),
]


@pytest.mark.parametrize(("pregunta", "lang"), NEGADAS)
def test_saying_the_child_is_fine_does_not_raise_an_alarm(
    triage: Triage, pregunta: str, lang: str
) -> None:
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, 9) < ORDEN["urgent"], (
        f"[{lang}] «{pregunta}» sale {nivel}: el padre está diciendo que NO"
    )


@pytest.mark.parametrize(("pregunta", "lang", "minimo"), NEGADAS_PERO_NO)
def test_a_negation_about_something_else_does_not_silence_the_alarm(
    triage: Triage, pregunta: str, lang: str, minimo: str
) -> None:
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, -1) >= ORDEN[minimo], f"[{lang}] «{pregunta}» sale {nivel}"


@pytest.mark.parametrize(("pregunta", "lang", "minimo"), VARIANTES)
def test_the_same_thing_said_another_way(
    triage: Triage, pregunta: str, lang: str, minimo: str
) -> None:
    nivel = str(triage.assess(pregunta).level)
    assert ORDEN.get(nivel, -1) >= ORDEN[minimo], f"[{lang}] «{pregunta}» sale {nivel}"
