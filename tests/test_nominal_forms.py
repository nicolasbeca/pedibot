"""Las reglas están escritas con verbos y las fuentes escriben nombres (9-sep-2026).

Empezó pareciendo un problema del árabe. El barrido dejaba el árabe muy por detrás de las demás
lenguas en el signo del sangrado, y al mirarlo aparecieron dos cosas.

La primera fue un error mío en la herramienta de análisis, no en el producto: buscaba «دم» por
subcadena, y «دم» vive dentro de «عدم» (ausencia de) y de «مقدم» (proveedor). Es la avería de la
L74 —«tos» dentro de «estos»— repetida por mí tres días después de escribirla.

La segunda es la de verdad. El árabe forma estos avisos con «عدم» + nombre verbal: «عدم القدرة
على البلع». Los patrones árabes eran todos verbales. Pero al probar la misma construcción en las
otras siete lenguas:

    «no responder», dicho como nombre     10 ciegos de 11
    «no poder tragar», dicho como nombre    8 ciegos de 8
    manos y pies muy fríos                  8 ciegos de 8

No era el árabe. **Todas las reglas estaban escritas con verbos** —«no responde», «cannot
swallow»— y una hoja clínica, o un padre que copia de una, escribe nombres: «ausencia de
respuesta», «incapacidad para tragar», «Bewusstlosigkeit», «отсутствие реакции».

Las manos y los pies fríos no tenían regla en ninguna lengua, y la primera versión que escribí
—metida en `mottled_skin`, emergencia— dio ocho falsos positivos de golpe: un niño descalzo
tiene los pies fríos. El signo clínico es la frialdad **con fiebre**, que es ámbar en el semáforo
del NICE, así que es regla propia, urgente, y con las dos mitades dentro del patrón, que es como
el proyecto ya escribe `meningitis_signs`.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: «No responde», dicho como nombre. Es como lo escribe una hoja clínica.
SIN_RESPUESTA = [
    ("es", "ausencia de respuesta a estímulos"),
    ("es", "falta de respuesta"),
    ("en", "lack of response to stimuli"),
    ("fr", "absence de réaction"),
    ("de", "keine Reaktion auf Ansprache"),
    ("de", "Bewusstlosigkeit"),
    ("pt", "ausência de resposta"),
    ("ru", "отсутствие реакции"),
    ("ar", "عدم الاستجابة"),
    ("hi", "प्रतिक्रिया का अभाव"),
]

#: «No puede tragar», dicho como nombre.
SIN_PODER_TRAGAR = [
    ("es", "incapacidad para tragar"),
    ("en", "inability to swallow"),
    ("fr", "incapacité à avaler"),
    ("de", "Unfähigkeit zu schlucken"),
    ("pt", "incapacidade de engolir"),
    ("ru", "невозможность глотать"),
    ("ar", "عدم القدرة على البلع"),
    ("hi", "निगलने में असमर्थता"),
]

#: La frialdad de manos y pies, que sólo cuenta acompañada de fiebre.
FRIOS_CON_FIEBRE = [
    ("es", "tiene 39 de fiebre y las manos y los pies muy fríos"),
    ("en", "he has a fever and very cold hands and feet"),
    ("fr", "il a de la fièvre et les mains et les pieds très froids"),
    ("de", "er hat Fieber und sehr kalte Hände und Füße"),
    ("pt", "está com febre e mãos e pés muito frios"),
    ("ru", "у ребёнка температура и очень холодные руки и ноги"),
    ("ar", "لديه حمى وبرودة شديدة في اليدين والقدمين"),
    ("hi", "बुखार है और हाथ-पैर बहुत ठंडे हैं"),
]

#: Sin fiebre no es nada, y esto es la mitad que decide si la regla se puede tener: un niño
#: descalzo, un niño friolero y un niño en invierno tienen los pies fríos.
FRIOS_SIN_FIEBRE = [
    ("es", "tiene los pies fríos porque va descalzo por casa"),
    ("es", "siempre tiene las manos frías, es muy friolero"),
    ("en", "his feet are cold, should I put socks on him"),
    ("en", "she always has cold hands in winter"),
    ("de", "er hat kalte Füße, weil er barfuß läuft"),
    ("fr", "il a les pieds froids, faut-il lui mettre des chaussettes"),
    # y la fiebre sola tampoco es esta regla
    ("es", "tiene fiebre de 38 y está comiendo bien"),
    # la respuesta a un TRATAMIENTO no es la respuesta a estímulos
    ("es", "no tiene respuesta a los antibióticos todavía"),
]


@pytest.mark.parametrize(("lang", "texto"), SIN_RESPUESTA)
def test_la_ausencia_de_respuesta_dicha_como_nombre_es_emergencia(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "emergency", f"[{lang}] «{texto}» → {nivel}"


@pytest.mark.parametrize(("lang", "texto"), SIN_PODER_TRAGAR)
def test_la_incapacidad_de_tragar_dicha_como_nombre_es_emergencia(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "emergency", f"[{lang}] «{texto}» → {nivel}"


@pytest.mark.parametrize(("lang", "texto"), FRIOS_CON_FIEBRE)
def test_manos_y_pies_frios_con_fiebre_avisan(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel != "routine", f"[{lang}] «{texto}» → rutina"


@pytest.mark.parametrize(("lang", "texto"), FRIOS_SIN_FIEBRE)
def test_manos_y_pies_frios_sin_fiebre_no_avisan(
    triage: Triage, lang: str, texto: str
) -> None:
    resultado = triage.assess(texto)
    assert resultado.level == "routine", (
        f"[{lang}] «{texto}» → {resultado.level} por {[r.id for r in resultado.matched]}"
    )


def test_los_patrones_estan_escritos_con_letras_no_con_escapes() -> None:
    """Un patrón clínico lo tiene que poder leer quien sepa la lengua y no sepa programar.

    Escribí la regla de la frialdad con escapes `\\uXXXX` para no pelearme con la consola. Casa
    igual —el módulo `re` los entiende— pero el fichero queda ilegible, el candado de densidad no
    encuentra ni una letra cirílica en ella, y se me coló una **н cirílica dentro de «तापमान»**,
    que es devanagari y no habría casado nunca. Escrito con letras se ve al primer vistazo.
    """
    texto = (RAIZ / "config" / "red_flags.yaml").read_text(encoding="utf-8")
    assert "\\u0" not in texto, (
        "hay patrones escritos con escapes \\uXXXX: se leen con `re` pero no los lee una persona"
    )
