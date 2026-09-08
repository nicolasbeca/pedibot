"""Un número en synonyms.yaml no puede tumbar una respuesta (8-sep-2026).

`emergency: [urgencias, 112]` — sin comillas, el cargador de YAML lee `112` como entero, y el
motor hace `" ".join(términos)` para clasificar el tema de la pregunta. Eso lanza un TypeError
que sube hasta el API y le llega al padre como **Internal Server Error**.

Estaba vivo en producción, y no en un rincón: para cualquier pregunta en inglés con la palabra
«emergency» —«when should I take my child to the emergency department?»— en el idioma principal
del producto. Un error de comillas en un fichero de datos, invisible a la vista.

Dos candados, porque el dato y el código fallan por separado: que el fichero no tenga números
sueltos, y que aunque los tuviera, el motor siga respondiendo.
"""

from __future__ import annotations

import pathlib

import yaml

from pedibot.bot.retrieval import Synonyms

RAIZ = pathlib.Path(__file__).resolve().parents[1]
FICHERO = RAIZ / "config" / "synonyms.yaml"


def test_every_term_in_the_file_is_text() -> None:
    crudo = yaml.safe_load(FICHERO.read_text(encoding="utf-8")) or {}
    malos = [
        (tabla, disparador, termino)
        for tabla, mapa in crudo.items()
        for disparador, terminos in (mapa or {}).items()
        for termino in (terminos or [])
        if not isinstance(termino, str)
    ]
    assert not malos, (
        "términos que el cargador de YAML no lee como texto (les faltan las comillas): "
        + ", ".join(f"{t}.{d} → {x!r}" for t, d, x in malos)
    )


def test_a_number_that_slips_through_does_not_break_the_answer(tmp_path: pathlib.Path) -> None:
    """Y si un día se cuela otro, que cueste una recuperación peor y no una respuesta perdida."""
    fichero = tmp_path / "synonyms.yaml"
    fichero.write_text("en:\n  emergency: [urgencias, 112]\n", encoding="utf-8")
    syn = Synonyms(fichero)
    terminos = syn.expand("is this an emergency?", "en")
    assert terminos == ["urgencias", "112"]
    " ".join(terminos)  # esto es lo que reventaba


def test_the_word_that_was_breaking_production_expands() -> None:
    syn = Synonyms(FICHERO, RAIZ / "config" / "drugs.yaml")
    terminos = syn.expand("when should I take my child to the emergency department?", "en")
    assert terminos, "«emergency» no expande a nada"
    assert all(isinstance(t, str) for t in terminos)
    " ".join(terminos)
