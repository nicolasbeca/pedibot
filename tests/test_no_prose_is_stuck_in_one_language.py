"""Nada que el padre lea como frase se queda en una sola lengua (20-sep-2026).

Tres fallos de la misma familia en una noche, y ninguno daba error:

1. los nombres de vacuna, en inglés dentro de una respuesta en árabe («Vitamin A (a supplement,
   not a vaccine)»);
2. la fecha de consulta, con «consultado el» en español dentro de una cita en inglés leída en
   hindi;
3. las 25 notas de urgencias, en inglés, y veintitrés de ellas de países africanos.

Los tres eran lo mismo: **una cadena suelta en un fichero de datos, servida igual a las ocho
lenguas**. Se encontraron probando el sitio a mano, uno detrás de otro, y el cuarto habría
tardado lo mismo en aparecer.

Esto es el candado. Recorre los YAML de configuración y falla si un campo **de prosa** —una
nota, un aviso, una explicación, una etiqueta— es una cadena en vez de un mapa por idiomas.

Lo que NO señala, y es la mitad importante de la regla: una cita que nombra un documento real,
una URL, un número de teléfono, un patrón de expresión regular, una lista de palabras para
buscar y el nombre propio de una tabla. Nada de eso se traduce, y un candado que también los
persiguiera se desactivaría en una semana.
"""

from __future__ import annotations

import re

import pytest
import yaml

from pedibot.settings import ROOT

#: Campos que la interfaz pinta como FRASE para el lector. Se amplía cuando aparezca otro; lo
#: que no se hace nunca es quitar uno para que el candado calle.
DE_PROSA = {
    "advice",
    "aviso",
    "body_text",
    "caption",
    "description",
    "explain",
    "help",
    "label",
    "note",
    "notes_reader",
    "reason",
    "summary",
    "text",
    "warning",
}

#: «Hay dos palabras seguidas de letra minúscula»: «112 / 15» no es una frase, «no hay servicio
#: nacional» sí. Se mira en los alfabetos que el sitio escribe.
_FRASE = re.compile(r"[a-záéíóúñçüßа-яё]{3,}\s+[a-záéíóúñçüßа-яё]{3,}")


def _prosa_suelta(valor: object, camino: str, fichero: str, fuera: list[str]) -> None:
    if isinstance(valor, dict):
        # ya está por idiomas: se da por buena y no se entra
        if {"en", "es"} <= set(valor):
            return
        for clave, dentro in valor.items():
            _prosa_suelta(dentro, f"{camino}.{clave}" if camino else str(clave), fichero, fuera)
        return
    if isinstance(valor, list):
        for i, dentro in enumerate(valor):
            _prosa_suelta(dentro, f"{camino}[{i}]", fichero, fuera)
        return
    if not isinstance(valor, str) or not _FRASE.search(valor):
        return
    ultimo = camino.split(".")[-1].split("[")[0]
    if ultimo in DE_PROSA:
        fuera.append(f"{fichero}: {camino} = «{valor[:80]}»")


@pytest.mark.parametrize("fichero", sorted(p.name for p in (ROOT / "config").glob("*.yaml")))
def test_ningun_campo_de_prosa_es_una_cadena_suelta(fichero: str) -> None:
    ruta = ROOT / "config" / fichero
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        pytest.fail(f"{fichero} no se puede leer: {e}")
    fuera: list[str] = []
    _prosa_suelta(datos, "", fichero, fuera)
    assert not fuera, (
        "esto se le enseña al lector en una sola lengua y saldrá igual en las ocho:\n  "
        + "\n  ".join(fuera[:8])
    )


def test_el_candado_encuentra_lo_que_encontro_a_mano() -> None:
    """La prueba del propio candado, con la nota de Nigeria tal y como estaba esta mañana.

    Un candado que no se comprueba a sí mismo es una función que devuelve una lista vacía.
    """
    fuera: list[str] = []
    _prosa_suelta(
        {"NG": {"emergency": "112", "note": "There is no national ambulance service."}},
        "",
        "prueba.yaml",
        fuera,
    )
    assert fuera and "NG.note" in fuera[0]


def test_el_candado_deja_en_paz_lo_que_no_se_traduce() -> None:
    """Una cita, una dirección y un teléfono. Si esto fallara, el candado duraría una semana."""
    fuera: list[str] = []
    _prosa_suelta(
        {
            "KE": {
                "emergency": "999",
                "source": "WHO/UNICEF — national immunization schedule as reported by Kenya",
                "source_url": "https://immunizationdata.who.int/kenya",
                "note": {"en": "Ambulances are limited.", "es": "Las ambulancias son limitadas."},
            }
        },
        "",
        "prueba.yaml",
        fuera,
    )
    assert fuera == []
