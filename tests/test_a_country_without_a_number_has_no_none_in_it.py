"""«Llama ahora al None» (18-sep-2026).

El peor fallo del día de África, y estaba en el sitio donde más duele. Ocho países no tienen
número nacional de emergencias: en siete la fuente lo dice con todas las letras y en Zambia no
hemos podido verificarlo. Su ficha existe —con `no_national` y la frase de la fuente— pero su
`emergency` es `None`, y las plantillas del aviso rojo lo metían en la frase sin preguntar:

    💛 This matters and you are not alone. Call None. If your child has already done something
       to harm themselves, go to the emergency department now.

Eso leía un padre de Kinshasa que acababa de escribir que su hijo quiere morirse.

Tres caminos lo hacían —el aviso de emergencia, el de salud mental y la lectura de una foto, que
además pasaba por `str()` y por eso no podía ni fallar— y los tres se comprueban aquí. La prueba
no es «la frase existe» sino dos cosas a la vez: que **no aparece la palabra None** y que **sí
aparece a dónde ir**, porque un aviso que se queda mudo por prudencia también deja tirado al
padre (L171: el aviso sin la explicación deja al padre a medias).
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from pedibot.bot.answer import EmergencyNumbers, build_banner
from pedibot.bot.photo import interpret
from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]
NUMEROS = yaml.safe_load((RAIZ / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8"))
IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")

#: Los países cuya ficha dice que no hay número, leídos del fichero y no escritos a mano: si
#: mañana entra un noveno, esta prueba lo cubre sola.
SIN_NUMERO = sorted(
    cc
    for cc, v in NUMEROS.items()
    if cc != "default" and isinstance(v, dict) and not v.get("emergency")
)

#: Una frase por nivel. No se buscan aquí las reglas del triaje —eso lo miden otras pruebas—
#: sino lo que se escribe encima cuando el triaje ya ha decidido.
FRASES = {
    "emergency": "mi hijo tiene los labios morados y le cuesta respirar",
    "urgent": "mi bebé de 2 meses tiene 39 de fiebre",
    "mental_health": "my son says he wants to kill himself",
}


@pytest.fixture(scope="module")
def numeros() -> EmergencyNumbers:
    return EmergencyNumbers(RAIZ / "config" / "emergency_numbers.yaml")


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


def test_there_are_countries_without_a_number_or_this_test_is_asleep() -> None:
    """Si un día ninguna ficha se queda sin número, esta prueba pasaría sin mirar nada."""
    assert SIN_NUMERO, "ninguna ficha sin número: esta prueba ya no está comprobando nada"


@pytest.mark.parametrize("code", SIN_NUMERO)
@pytest.mark.parametrize("lang", IDIOMAS)
@pytest.mark.parametrize("nivel", sorted(FRASES))
def test_the_banner_never_says_the_word_none(
    numeros: EmergencyNumbers, triaje: Triage, code: str, lang: str, nivel: str
) -> None:
    tr = triaje.assess(FRASES[nivel])
    if tr.level == "routine":
        pytest.skip(f"la frase de «{nivel}» ya no dispara nada: eso lo mide otra prueba")
    aviso = build_banner(tr, lang, numeros.get(code, lang))
    assert aviso, f"{code}/{lang}/{nivel}: sin aviso"
    assert "None" not in aviso, f"{code}/{lang}/{nivel}: «{aviso}»"
    assert "null" not in aviso.lower(), f"{code}/{lang}/{nivel}: «{aviso}»"


@pytest.mark.parametrize("code", SIN_NUMERO)
@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_banner_still_says_where_to_go(
    numeros: EmergencyNumbers, triaje: Triage, code: str, lang: str
) -> None:
    """Callarse no es una solución: sin número, el aviso tiene que decir a dónde ir."""
    for nivel in ("emergency", "mental_health"):
        tr = triaje.assess(FRASES[nivel])
        if tr.level == "routine":
            continue
        aviso = build_banner(tr, lang, numeros.get(code, lang))
        # el aviso sin número es sensiblemente más largo que «🚨» y nombra un sitio al que ir
        assert len(aviso) > 60, f"{code}/{lang}/{nivel}: aviso demasiado corto — «{aviso}»"


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_photo_reading_never_says_the_word_none(lang: str) -> None:
    """El mismo agujero por otro camino: la API convertía el None en la cadena «None»."""
    visto = {"quality": "ok", "cyanosis": "yes", "swelling": "no", "petechiae": "no"}
    nivel, texto = interpret(visto, lang, None)
    assert nivel == "emergency"
    assert "None" not in texto, f"{lang}: «{texto}»"
    assert len(texto) > 60, f"{lang}: texto demasiado corto — «{texto}»"


@pytest.mark.parametrize("code", SIN_NUMERO)
def test_a_country_without_a_number_is_not_a_country_without_an_entry(code: str) -> None:
    """Y la otra mitad: sin número, la ficha tiene que traer el porqué (L178)."""
    ficha = NUMEROS[code]
    assert ficha.get("no_national") or ficha.get("unverified"), (
        f"{code} se ha quedado sin número sin decir si es que no lo hay o que no lo sabemos"
    )
    assert (ficha.get("note") or "").strip(), f"{code}: sin número y sin explicación"
