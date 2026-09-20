"""La dosis también trae algo que ese lector pueda abrir (20-sep-2026).

Probado en vivo: un padre en la India pregunta en inglés la dosis de paracetamol para 12 kg y
recibe la tabla correcta, con su bote y sus mililitros, y debajo «Source: AEPap — Guía rápida de
dosificación práctica en pediatría». En español. Ese padre no puede abrirla.

La cita **no se toca**, y eso es lo importante de este fichero: los miligramos por kilo salen de
ese documento, y atribuirlos a otro sería exactamente lo que este proyecto existe para no hacer.
Lo que se añade es una segunda línea con una ficha que ese lector sí puede leer, dicho como lo
que es: «más sobre esta medicina», no «la fuente».

Y cuando no hay ninguna que pueda leer, no se pone nada. Un enlace en una lengua que no lee no es
una puerta, es una puerta pintada en la pared.
"""

from __future__ import annotations

import pytest

from pedibot.bot.dose import DRUGS, IBUPROFENO, PARACETAMOL, calculate, format_result, leer_mas

#: Lenguas que pueden abrir la ficha inglesa: la suya propia, y las que este proyecto ya tiene
#: declaradas como puente hacia el inglés (L183 y `READABLE_FALLBACK`).
CON_PUERTA = ("en", "hi", "ar", "ru", "de", "fr", "sw")
#: El español ya tiene la fuente de la tabla, que está en su idioma; el portugués puente a él.
SIN_PUERTA = ("es", "pt")


@pytest.mark.parametrize("lang", CON_PUERTA)
@pytest.mark.parametrize("medicina", [PARACETAMOL, IBUPROFENO])
def test_quien_puede_leer_ingles_recibe_la_ficha(lang: str, medicina) -> None:
    linea = leer_mas(medicina, lang)
    assert linea, f"{lang} puede abrir la ficha del NHS y no se le ofrece"
    assert "nhs.uk" in linea
    assert "{" not in linea, f"plantilla sin rellenar en {lang}: «{linea}»"


@pytest.mark.parametrize("lang", SIN_PUERTA)
def test_quien_ya_tiene_la_fuente_en_su_idioma_no_recibe_nada(lang: str) -> None:
    assert leer_mas(PARACETAMOL, lang) == ""


def test_la_fuente_de_la_tabla_no_cambia() -> None:
    """Los miligramos por kilo son de AEPap. Citar al NHS por ellos sería atribuirle un número
    que su ficha no da: el NHS dosifica por edad y esta tabla por peso."""
    for medicina in DRUGS.values():
        assert "AEPap" in medicina.source


def test_la_respuesta_inglesa_lleva_las_dos_cosas() -> None:
    """La fuente de la tabla y la puerta, en ese orden y sin mezclarse."""
    texto = format_result(calculate("paracetamol", weight_kg=12, age_months=36), lang="en")
    assert "AEPap" in texto, "la fuente de la tabla tiene que seguir estando"
    assert "nhs.uk/medicines/paracetamol-for-children" in texto
    assert texto.index("AEPap") < texto.index("nhs.uk"), "primero de dónde sale el número"


def test_la_espanola_no_repite_la_fuente_dos_veces() -> None:
    texto = format_result(calculate("paracetamol", weight_kg=12, age_months=36), lang="es")
    assert texto.count("AEPap") == 1
    assert "nhs.uk" not in texto
