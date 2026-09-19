"""Los calendarios del Golfo y de Egipto, sacados de los datos de la OMS (17-sep-2026).

Hasta hoy el sitio tenía ocho calendarios —Brasil, Alemania, España, Francia, Reino Unido, India,
Portugal y EE. UU.— y **ni uno árabe**, teniendo el árabe entre sus ocho idiomas y las tablas de
crecimiento ya cubriendo Arabia Saudí, Egipto y Jordania. Un padre en Riad preguntaba por las
vacunas de su hijo y se le ofrecía el calendario español traducido al árabe: parece una
respuesta, y no lo es.

No se puede copiar el documento saudí: sus condiciones de uso lo prohíben expresamente (leídas el
16-sep-2026). Lo que sí se puede usar es lo que **el propio país le reporta a la OMS**, que la OMS
publica como datos abiertos. `scripts/build_who_schedules.py` los baja y los traduce a la forma
del fichero; aquí se fija lo que un europeo corregiría por instinto y estropearía:

- **La BCG saudí va a los 6 meses**, no al nacer. Lo reporta así todos los años desde 2019.
- **La BCG kuwaití va a los 3 meses**, y lleva más de diez años reportándose así.
- **Egipto sigue con OPV oral en todas las citas** y con pentavalente de célula entera (DTwP),
  no con la hexavalente del Golfo.
- **El VPH saudí es sólo para niñas.** Prometerle esa vacuna al padre de un niño es mandarle a un
  centro a por algo que allí no le van a poner.
- **Dos productos en una casilla son un pinchazo, no dos.** Emiratos reporta la neumocócica de
  los 2 meses como PCV20 y como PCV15, y Kuwait la de los 2 meses como hexavalente y como
  pentavalente: son alternativas, y la tabla tiene que leerse como tal.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest
import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
PAISES = yaml.safe_load((RAIZ / "config" / "vaccines.yaml").read_text(encoding="utf-8"))[
    "countries"
]
ARABES = ("SA", "AE", "EG", "QA", "KW")
IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


def _generador():
    ruta = RAIZ / "scripts" / "build_who_schedules.py"
    spec = importlib.util.spec_from_file_location("build_who_schedules", ruta)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    sys.modules["build_who_schedules"] = m
    spec.loader.exec_module(m)
    return m


def vacunas_de(pais: str, edad: float) -> list[str]:
    citas = [s for s in PAISES[pais]["schedule"] if float(s["age"]) == edad]
    return [v for c in citas for v in c["vaccines"]]


# ── que estén, y bien formados ───────────────────────────────────────────────────────────────
def test_the_arab_world_has_its_own_calendars() -> None:
    faltan = [c for c in ARABES if c not in PAISES]
    assert not faltan, f"sin calendario: {faltan}"


@pytest.mark.parametrize("pais", ARABES)
def test_each_one_says_where_it_comes_from(pais: str) -> None:
    fuente = PAISES[pais]["source"]
    assert "WHO" in fuente and "AD_SCHEDULES" in fuente, f"{pais}: la fuente no se identifica"
    assert "2025" in fuente or "2026" in fuente, f"{pais}: la fuente no dice de qué año es el dato"
    assert PAISES[pais]["source_url"].startswith("https://"), f"{pais}: sin enlace a la fuente"


@pytest.mark.parametrize("pais", ARABES)
def test_the_note_warns_that_the_ministry_wins(pais: str) -> None:
    """El dato es de la OMS y puede ir por detrás del ministerio. Callarlo sería venderlo como
    lo que no es: un calendario oficial copiado de la fuente nacional."""
    nota = PAISES[pais]["note"]
    faltan = [lg for lg in IDIOMAS if not str(nota.get(lg, "")).strip()]
    assert not faltan, f"{pais}: nota sin traducir a {faltan}"
    assert "WHO" in nota["en"] and "health centre" in nota["en"]


@pytest.mark.parametrize("pais", ARABES)
def test_no_raw_who_code_reaches_a_parent(pais: str) -> None:
    """«PCV_15_VALENT» o «HEPB_PEDIATRIC» son códigos de un almacén de datos, no vacunas."""
    for cita in PAISES[pais]["schedule"]:
        for v in cita["vaccines"]:
            assert "_" not in v, f"{pais}: código crudo en la tabla: {v}"
            assert v == v.strip() and v[:1].isupper(), f"{pais}: nombre mal formado: {v!r}"


# ── lo que un europeo corregiría por instinto ────────────────────────────────────────────────
def test_saudi_bcg_is_at_six_months_not_at_birth() -> None:
    assert not any("BCG" in v for v in vacunas_de("SA", 0)), "BCG saudí colocada al nacer"
    assert any("BCG" in v for v in vacunas_de("SA", 6)), "falta la BCG saudí de los 6 meses"
    assert "2019" in PAISES["SA"]["note"]["es"], "la nota no avisa de la BCG a los 6 meses"


def test_kuwait_bcg_is_at_three_months() -> None:
    assert any("BCG" in v for v in vacunas_de("KW", 3)), "falta la BCG kuwaití de los 3 meses"
    assert not any("BCG" in v for v in vacunas_de("KW", 0)), "BCG kuwaití colocada al nacer"


def test_egypt_still_gives_oral_polio_at_every_visit() -> None:
    for edad in (0, 2, 4, 6):
        assert any("OPV" in v for v in vacunas_de("EG", edad)), f"EG: sin OPV a los {edad} meses"
    assert any("DTwP" in v for v in vacunas_de("EG", 2)), "EG: pentavalente de célula entera"


def test_the_saudi_hpv_says_it_is_for_girls() -> None:
    vph = [v for c in PAISES["SA"]["schedule"] for v in c["vaccines"] if "HPV" in v]
    assert vph, "SA: falta el VPH"
    assert all("girls" in v for v in vph), f"SA: el VPH no dice que es sólo para niñas: {vph}"


@pytest.mark.parametrize(
    "pais,edad,familia",
    [("AE", 2, "Pneumococcal"), ("KW", 2, "Pneumococcal"), ("KW", 2, "DT"), ("KW", 24, "measles")],
)
def test_two_products_in_one_slot_are_one_injection(pais: str, edad: float, familia: str) -> None:
    """Emiratos reporta PCV20 y PCV15 en la misma casilla, y Kuwait la hexavalente y la
    pentavalente. Si la tabla los imprime en dos líneas, el padre lee dos pinchazos."""
    de_esa_familia = [v for v in vacunas_de(pais, edad) if familia.lower() in v.lower()]
    assert len(de_esa_familia) == 1, (
        f"{pais} a los {edad} m: {familia} en {len(de_esa_familia)} líneas"
    )
    assert " or " in de_esa_familia[0], f"{pais}: {de_esa_familia[0]} no ofrece la alternativa"


def test_the_flu_slot_says_it_comes_back_every_year() -> None:
    for pais in ARABES:
        gripe = [
            s
            for s in PAISES[pais]["schedule"]
            if any("influenza" in v.lower() for v in s["vaccines"])
        ]
        assert gripe, f"{pais}: sin gripe estacional"
        for s in gripe:
            assert s.get("every_year"), f"{pais}: la gripe no está marcada como anual"
            assert "every year" in s["label"]["en"], f"{pais}: la etiqueta no lo dice"


# ── el generador, por dentro (sin red) ───────────────────────────────────────────────────────
def test_the_age_reader_understands_how_who_writes_an_age() -> None:
    g = _generador()
    assert g.lee_edad("B")[0] == 0.0
    assert g.lee_edad("M18")[0] == 18.0
    assert g.lee_edad("Y4-Y6")[:1] == (48.0,)
    assert round(g.lee_edad("W6")[0], 2) == 1.38  # el calendario indio se cita en semanas
    assert g.lee_edad(">=M6")[4] is True
    # lo que NO es una edad
    assert g.lee_edad("1st contact") is None
    assert g.lee_edad("+M6") is None
    assert g.lee_edad("<Y7") is None, "«antes de los 7 años» es un tope, no una cita"
    assert g.lee_edad(None) is None


def test_the_same_age_is_written_one_way_only() -> None:
    """Kuwait reporta los doce meses como «M12» y como «Y1»: es una visita, no dos."""
    g = _generador()
    assert g.normaliza(12.0, "Y", 1.0, None) == ("M", 12.0, None)
    assert g.normaliza(24.0, "M", 24.0, None) == ("Y", 2.0, None)
    assert g.normaliza(18.0, "M", 18.0, None) == ("M", 18.0, None)
    assert g.normaliza(1.38, "W", 6.0, None) == ("W", 6.0, None), "las semanas se quedan"


def test_an_age_is_said_the_way_each_language_says_it() -> None:
    g = _generador()
    assert g.frase_edad(2, "M", "ar", None, False) == "شهران", "el árabe tiene dual"
    assert g.frase_edad(12, "M", "ru", None, False) == "12 месяцев"
    assert g.frase_edad(2, "M", "ru", None, False) == "2 месяца"
    assert g.frase_edad(6, "M", "de", None, True) == "Ab 6 Monaten", "«Ab» rige dativo"
    assert g.frase_edad(3.6, "Y", "ru", None, False) == "3,6 года"
    assert g.frase_edad(4, "Y", "es", 6, False) == "4–6 años"


def test_a_dose_counted_from_the_previous_one_is_not_thrown_away() -> None:
    g = _generador()
    assert g.lee_intervalo("+M6") == "6 months later"
    assert g.lee_intervalo("+W4") == "4 weeks later"
    assert g.lee_intervalo("M6") is None
