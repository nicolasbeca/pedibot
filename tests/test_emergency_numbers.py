"""El número al que llamar es la cifra más consecuente de todo el producto (7-sep-2026).

Todo lo demás de una respuesta se puede leer con calma. El número del banner de emergencia se
marca con un niño en brazos, y si no está —o está mal— el resto de la respuesta da igual.

Al cruzarlos por primera vez contra lo que el proyecto sirve de verdad, la cobertura era buena:
los siete calendarios de vacunas, todos los países de las marcas de la calculadora, y siete de
los ocho idiomas con su país cubierto. Faltaba uno: **India**, el país del idioma en el que se
publican sesenta guías. Un padre allí, con una alarma de emergencia en pantalla, no veía ninguna
cifra — y la frase por defecto en hindi era la única de las ocho que tampoco daba ninguna,
mientras las otras siete llevan «112 en la UE, 911 en América».

Lo que este fichero NO hace: comprobar que los números son correctos. Eso no se puede automatizar
—hay que ir a la fuente oficial de cada país— y se hace a mano al añadirlos. Lo que sí comprueba
es que no falte ninguno donde el producto promete estar, que es la parte que se olvida sola.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from pedibot.bot.answer import SUPPORTED_LANGS

RAIZ = pathlib.Path(__file__).resolve().parents[1]
NUMEROS = yaml.safe_load((RAIZ / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8"))
PAISES = {k for k in NUMEROS if k != "default"}

#: El país que un lector de cada idioma da por supuesto si no elige ninguno. No es el único país
#: de cada lengua —el español se habla en veinte— pero sí el mínimo que no puede faltar.
PAIS_DE_LA_LENGUA = {
    "es": "ES",
    "en": "GB",
    "fr": "FR",
    "de": "DE",
    "ru": "RU",
    "ar": "SA",
    "pt": "PT",
    "hi": "IN",
}


def test_every_language_the_site_speaks_has_a_country_with_a_number() -> None:
    """El hueco que dio origen a este fichero: se añadió el hindi y no el número de India."""
    faltan = {
        lang: PAIS_DE_LA_LENGUA.get(lang)
        for lang in SUPPORTED_LANGS
        if PAIS_DE_LA_LENGUA.get(lang) not in PAISES
    }
    assert not faltan, (
        f"idiomas cuyo país no tiene número de emergencias: {faltan}. "
        "Un padre que reciba una alarma en ese idioma no verá ninguna cifra."
    )


def test_the_map_of_languages_to_countries_is_complete() -> None:
    """El candado del candado: si llega un idioma nuevo y nadie lo añade aquí, la comprobación de
    arriba lo daría por bueno sin mirarlo."""
    sin_pais = [lang for lang in SUPPORTED_LANGS if lang not in PAIS_DE_LA_LENGUA]
    assert not sin_pais, f"añade el país de referencia de {sin_pais} a este fichero"


def test_every_country_the_project_serves_has_a_number() -> None:
    """Un calendario de vacunas o una marca de la calculadora son una promesa de estar ahí."""
    vac = set(
        yaml.safe_load((RAIZ / "config" / "vaccines.yaml").read_text(encoding="utf-8"))["countries"]
    )
    drugs = yaml.safe_load((RAIZ / "config" / "drugs.yaml").read_text(encoding="utf-8"))["drugs"]
    marcas: set[str] = set()
    for ficha in drugs.values():
        for b in ficha.get("brands") or []:
            marcas |= set(b.get("countries") or [])
    faltan = sorted((vac | marcas) - PAISES)
    assert not faltan, f"países que el proyecto sirve y no tienen número de emergencias: {faltan}"


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_the_fallback_phrase_exists_in_every_language(lang: str) -> None:
    """Es una FRASE, no un número, porque se interpola dentro de la oración del banner: la
    versión alemana llegó a leer «Rufen Sie jetzt your local emergency number an»."""
    frase = (NUMEROS["default"]["emergency"] or {}).get(lang)
    assert frase, f"[{lang}] sin frase por defecto"
    assert len(frase) > 8


@pytest.mark.parametrize("lang", sorted(SUPPORTED_LANGS))
def test_the_fallback_phrase_names_at_least_one_number(lang: str) -> None:
    """La frase existe para quien no ha elegido país, y sin una cifra no sirve de nada. La hindi
    era la única de las ocho que no daba ninguna."""
    frase = NUMEROS["default"]["emergency"][lang]
    assert any(c.isdigit() for c in frase), (
        f"[{lang}] la frase por defecto no nombra ningún número: «{frase}»"
    )


@pytest.mark.parametrize("code", sorted(PAISES))
def test_a_country_entry_always_carries_an_emergency_number(code: str) -> None:
    """`poison` y `mental` pueden estar vacíos —India se añadió sin centro de intoxicaciones
    porque no se pudo verificar en fuente oficial, y un número inventado es peor que ninguno—,
    pero el de emergencias no puede faltar: es el motivo de que exista la ficha."""
    ficha = NUMEROS[code]
    assert ficha.get("emergency"), f"{code} no tiene número de emergencias"
    assert any(c.isdigit() for c in str(ficha["emergency"])), (
        f"{code}: «{ficha['emergency']}» no contiene ninguna cifra"
    )


# --------------------------------------------------------------------------------------------
# El desplegable con el que un padre elige su país era una TERCERA lista, escrita a mano
# --------------------------------------------------------------------------------------------


def test_every_country_with_a_number_can_actually_be_chosen() -> None:
    """Tener el número puesto no sirve de nada si el lector no puede seleccionar su país.

    El desplegable del chat era un array a mano dentro de `Chat.astro` y se había quedado corto:
    los números conocían 31 países y el selector ofrecía 29. India acababa de añadirse, pero
    **Perú llevaba así desde siempre** — su número estaba puesto y ningún padre peruano podía
    elegirlo, así que siempre recibía la frase genérica. Nada fallaba, como en todos los clones.

    Ahora la lista se deriva del catálogo en `scripts/export_catalog.py`. Esto comprueba que el
    fichero exportado sigue al día: si alguien añade un país y no reexporta, la web no lo ofrece.
    """
    import json

    exportado = json.loads(
        (RAIZ / "web" / "site" / "src" / "data" / "countries.json").read_text(encoding="utf-8")
    )
    assert set(exportado) == PAISES, (
        "countries.json no coincide con emergency_numbers.yaml: "
        f"sobran {sorted(set(exportado) - PAISES)}, faltan {sorted(PAISES - set(exportado))}. "
        "Ejecuta scripts/export_catalog.py."
    )


def test_the_chat_does_not_keep_its_own_hand_written_country_list() -> None:
    """El candado del candado: si alguien vuelve a escribir el array a mano, las dos listas
    empiezan a separarse otra vez y el test de arriba seguiría en verde."""
    chat = (RAIZ / "web" / "site" / "src" / "components" / "Chat.astro").read_text(encoding="utf-8")
    assert "from '../data/countries.json'" in chat, "el desplegable ya no se deriva del catálogo"
    assert "['GB','UK'],['ES','ES']" not in chat, "ha vuelto la lista escrita a mano"
