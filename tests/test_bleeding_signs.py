"""El sangrado: cuatro huecos, y uno era una fractura de base de cráneo (9-sep-2026).

Barrido el sangrado contra las advertencias de las 483 guías.

**Sangre o líquido claro por la nariz o los oídos después de un golpe en la cabeza** no tenía
patrón en ninguna lengua. Es el signo de la fractura de base de cráneo, sale en las guías de
traumatismo craneal de las ocho, y el triaje lo leía como rutina. El proyecto tenía dos reglas
para el golpe en la cabeza —la pérdida de conocimiento y los vómitos— y no ésta.

**El sangrado que no para** ya estaba, pero sólo dicho como «no deja de sangrar». Las guías lo
dicen por reloj («dura más de 10 a 15 minutos») y por cantidad («parece excesivo»), y un padre
lo dice mirando la hora: «no para desde hace veinte minutos».

**«Deposiciones con mucha sangre»** no casaba porque el patrón pedía «con sangre» pegado y la
guía mete «mucha» en medio.

**Sangre en el pis** no tenía regla. Las guías de infección de orina de las ocho lo ponen bajo
«ve al médico», así que urgente y no emergencia.

Dos cosas cazó el proyecto solo, y merece anotarlas: el candado de densidad rechazó la regla
nueva porque le había escrito catorce patrones latinos y uno árabe, y el barrido de las ocho
lenguas destapó que el ruso pone el complemento delante —«Из носа или ушей выходит кровь»—,
que es la familia de errores que más veces ha aparecido aquí.

Abajo, lo que no puede avisar: un sangrado de nariz que ya paró, un corte pequeño, unas encías
que sangran al cepillarse y la regla de una adolescente.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: La fractura de base de cráneo, en las ocho lenguas.
POR_LA_NARIZ_O_EL_OIDO = [
    ("es", "le sale sangre por el oído después del golpe en la cabeza"),
    ("en", "Blood or clear fluid coming from the nose or ears"),
    ("fr", "du sang ou un liquide clair par le nez ou les oreilles"),
    ("de", "Austritt von Blut oder klarer Flüssigkeit aus Nase oder Ohren"),
    ("pt", "sangue ou líquido claro pelo nariz ou pelos ouvidos"),
    ("ru", "Из носа или ушей выходит кровь или прозрачная жидкость"),
    ("ar", "دم أو سائل صاف من الأنف أو الأذنين"),
    ("hi", "सिर में चोट के बाद नाक से खून आ रहा है"),
]

#: El sangrado que no para, dicho por reloj y por cantidad.
NO_PARA = [
    ("es", "El sangrado dura más de 10 a 15 minutos"),
    ("es", "le sangra la nariz y no para desde hace 20 minutos"),
    ("es", "El sangrado parece excesivo"),
    ("en", "The nosebleed lasts longer than 10 to 15 minutes"),
    ("en", "The bleeding seems excessive"),
    ("fr", "Le saignement dure plus de 10 à 15 minutes"),
    ("de", "Die Blutung länger als 10 bis 15 Minuten dauert"),
]

#: La sangre en el pis, en las ocho.
EN_EL_PIS = [
    ("es", "hay sangre en el pis"),
    ("en", "There is blood in the pee"),
    ("fr", "du sang dans les urines"),
    ("de", "Blut im Urin"),
    ("pt", "sangue no xixi"),
    ("ru", "кровь в моче"),
    ("ar", "دم في البول"),
    ("hi", "पेशाब में खून आ रहा है"),
]

#: Lo corriente. Un sangrado de nariz que paró es el motivo de consulta más frecuente que hay
#: sobre sangre, y si avisa, el aviso deja de significar nada.
LO_CORRIENTE = [
    ("es", "le ha sangrado la nariz un poco y ya ha parado"),
    ("es", "se ha hecho un corte pequeño en el dedo y sangra un poquito"),
    ("es", "mi hija tiene la regla y le duele la tripa"),
    ("es", "le sangran las encías cuando se lava los dientes"),
    ("en", "he had a small nosebleed and it stopped"),
    ("en", "she has her period"),
    ("fr", "il a saigné du nez une minute et ça s'est arrêté"),
]


@pytest.mark.parametrize(("lang", "texto"), POR_LA_NARIZ_O_EL_OIDO)
def test_sangre_o_liquido_por_la_nariz_o_el_oido_es_emergencia(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "emergency", f"[{lang}] «{texto}» → {nivel}"


@pytest.mark.parametrize(("lang", "texto"), NO_PARA)
def test_el_sangrado_que_no_para_es_emergencia(triage: Triage, lang: str, texto: str) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "emergency", f"[{lang}] «{texto}» → {nivel}"


@pytest.mark.parametrize(("lang", "texto"), EN_EL_PIS)
def test_la_sangre_en_el_pis_no_es_rutina(triage: Triage, lang: str, texto: str) -> None:
    nivel = triage.assess(texto).level
    assert nivel != "routine", f"[{lang}] «{texto}» → rutina"


@pytest.mark.parametrize(("lang", "texto"), LO_CORRIENTE)
def test_el_sangrado_corriente_no_avisa(triage: Triage, lang: str, texto: str) -> None:
    resultado = triage.assess(texto)
    assert resultado.level == "routine", (
        f"[{lang}] «{texto}» → {resultado.level} por {[r.id for r in resultado.matched]}"
    )
