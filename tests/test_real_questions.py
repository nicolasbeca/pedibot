"""Tres fallos que sólo aparecieron al mirar lo que preguntó la gente de verdad (7-sep-2026).

En la base hay **cinco** consultas de lectores reales — el resto son pruebas nuestras. Cinco. Y
dos de ellas estaban mal contestadas:

  · «My 4-year-old has a fever of 38.8 °C» (web, hoy) → el motor **preguntó la edad**, que estaba
    escrita en la propia pregunta.
  · «Cuando dalsy le doy a mi hijo?» (Telegram) → «no tengo información fiable sobre esto en mis
    fuentes», teniendo la web una página entera para el Dalsy.

Ninguno de los dos habría salido de un conjunto de pruebas escrito por nosotros, porque los dos
son formas de escribir que a nadie se le ocurren hasta que las ve. Es la L35 otra vez, y es la
razón de que este fichero exista: los casos de aquí vienen de preguntas reales, no inventadas.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.answer import SUPPORTED_LANGS
from pedibot.bot.retrieval import Synonyms
from pedibot.bot.triage import Triage, parse_age_months

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triaje():
    return Triage(RAIZ / "config" / "red_flags.yaml")


# --------------------------------------------------------------------------------------------
# 1. El guion apagaba la edad, y con ella la alarma
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pregunta", "meses"),
    [
        ("My 4-year-old has a fever of 38.8 C", 48),  # la consulta real, tal cual llegó
        ("My 2-month-old has a fever of 38.5", 2),
        ("my 6-week-old has a fever", None),  # semanas: se comprueba aparte, es decimal
        ("mi bebé de 2-meses tiene fiebre", 2),
        ("mon bébé de 2-mois a de la fièvre", 2),
        ("mein 2-Monate altes Baby hat Fieber", 2),
        ("meu bebé de 2-meses tem febre", 2),
    ],
)
def test_a_hyphen_does_not_hide_the_age(pregunta: str, meses: int | None) -> None:
    edad = parse_age_months(pregunta)
    if meses is None:
        assert edad is not None and 1.0 < edad < 2.0, f"«{pregunta}» → {edad}"
    else:
        assert edad == meses, f"«{pregunta}» → {edad}"


def test_the_hyphen_used_to_switch_off_the_infant_fever_alarm(triaje) -> None:
    """La consecuencia que importa, dicha aparte para que no se pierda entre las demás.

    La fiebre en un lactante de menos de tres meses es de las reglas más importantes que existen
    y depende de que se haya detectado la edad (L36). Hasta el 7-sep-2026:

        «My 2 month old has a fever of 38.5»  →  urgente
        «My 2-month-old has a fever of 38.5»  →  RUTINA

    y la segunda es la forma más natural de escribirlo en inglés.
    """
    con = triaje.assess("My 2-month-old has a fever of 38.5")
    sin = triaje.assess("My 2 month old has a fever of 38.5")
    assert con.level == sin.level == "urgent"
    assert con.age_months == sin.age_months == 2


def test_a_temperature_range_is_not_read_as_an_age(triaje) -> None:
    """La otra mitad: permitir el guion no puede inventar edades donde no las hay."""
    assert parse_age_months("tiene 38.8-39 de fiebre") is None
    assert parse_age_months("le doy 5-10 ml") is None
    assert parse_age_months("tiene 38.8-39 de fiebre y 4 años") == 48


# --------------------------------------------------------------------------------------------
# 2. El buscador no conocía las marcas que la calculadora sí conoce
# --------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sinonimos():
    return Synonyms(RAIZ / "config" / "synonyms.yaml", RAIZ / "config" / "drugs.yaml")


def test_the_brand_a_parent_reads_on_the_bottle_finds_the_generic(sinonimos) -> None:
    """La consulta real que lo destapó, y las marcas grandes de cada mercado."""
    assert "ibuprofeno" in sinonimos.expand("Cuando dalsy le doy a mi hijo?", "es")
    assert "paracetamol" in " ".join(sinonimos.expand("dosis de apiretal", "es"))
    assert "ibuprofeno" in sinonimos.expand("quanto Alivium posso dar", "pt")
    assert "paracetamol" in " ".join(sinonimos.expand("how much Calpol", "en"))


def test_every_brand_in_the_calculator_is_known_to_the_search(sinonimos) -> None:
    """El candado que importa: las dos listas ya no pueden separarse.

    Antes eran dos, escritas a mano: las marcas en `drugs.yaml` para la calculadora y los
    sinónimos en `synonyms.yaml` para el buscador. De 44 nombres, **39 no estaban** en la segunda.
    Ahora se derivan del catálogo, así que una marca nueva queda buscable sola — y esto lo
    comprueba."""
    import yaml

    drugs = yaml.safe_load((RAIZ / "config" / "drugs.yaml").read_text(encoding="utf-8"))["drugs"]
    faltan = []
    for ficha in drugs.values():
        nombres = [b["name"] for b in ficha.get("brands", [])] + list(ficha.get("aliases", []))
        for n in nombres:
            for parte in str(n).split("/"):
                clave = parte.strip().lower()
                if len(clave) >= 3 and clave not in sinonimos._marcas:
                    faltan.append(clave)
    assert not faltan, f"marcas que el buscador no conoce: {sorted(set(faltan))}"


def test_a_question_without_a_brand_is_not_polluted(sinonimos) -> None:
    """Y no se cuelan términos de medicamentos donde nadie ha nombrado ninguno."""
    fuera = sinonimos.expand("mi hijo de 4 años tiene fiebre", "es")
    assert not any("ibuprof" in t or "paracetamol" in t for t in fuera), fuera


# --------------------------------------------------------------------------------------------
# 3. El catálogo de fármacos hablaba seis idiomas de ocho
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("campo", ["generic", "notes"])
def test_the_drug_catalogue_speaks_every_language(campo: str) -> None:
    """`notes` es el aviso de seguridad —«no en menores de 3 meses ni de 5 kg»—, y a portugués e
    hindi les llegaba en inglés. Nada fallaba, porque la web cae a inglés cuando falta el idioma:
    por eso no lo veía nadie. Es el clon podrido (L23), y la lista de idiomas se lee del propio
    motor para que el noveno rompa esta prueba en vez de colarse."""
    import yaml

    drugs = yaml.safe_load((RAIZ / "config" / "drugs.yaml").read_text(encoding="utf-8"))["drugs"]
    faltan = {
        nombre: sorted(set(SUPPORTED_LANGS) - set(ficha[campo]))
        for nombre, ficha in drugs.items()
        if set(SUPPORTED_LANGS) - set(ficha[campo])
    }
    assert not faltan, f"{campo} sin traducir: {faltan}"


def test_every_engine_actually_gets_the_drug_catalogue() -> None:
    """El candado del montaje, no de la pieza.

    Al arreglar lo de las marcas, la prueba de arriba pasaba en verde y **en producción seguía
    sin funcionar**: `Synonyms` sabía leer el catálogo, pero ninguno de los seis sitios que
    construyen el buscador se lo pasaba. La prueba construía el objeto ella misma, así que
    validaba la pieza y no el montaje — que es donde estaba el fallo.

    Se lee el código con el AST, como en `tests/test_fronts.py`: toda llamada a `Synonyms(...)`
    en `src/` tiene que llevar el catálogo de fármacos.
    """
    import ast

    sueltas = []
    for f in sorted((RAIZ / "src").rglob("*.py")):
        arbol = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(arbol):
            if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "Synonyms":
                if len(n.args) + len(n.keywords) < 2:
                    sueltas.append(f"{f.relative_to(RAIZ)}:{n.lineno}")
    assert not sueltas, (
        "estos construyen el buscador sin el catálogo de fármacos, así que no conocerán "
        f"ninguna marca: {sueltas}"
    )
