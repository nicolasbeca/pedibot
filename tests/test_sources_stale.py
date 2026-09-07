"""Una fuente puede caducar sin morir (7-sep-2026).

`sources_alive.py` busca fuentes ROTAS: direcciones que no responden, que redirigen a una página de
retirada o que acaban en otro tema. El calendario de vacunas de Portugal pasaba las tres
comprobaciones —HTTP 200, sin redirección, misma página— y llevaba **desde octubre de 2025
derogado**: la Direção-Geral da Saúde lo había sustituido por el PNV 2025, que cambia el MenC de
los 12 meses por MenACWY y el neumococo Pn13 por Pn20.

O sea: estuvimos publicando el calendario de vacunas equivocado de un país entero, y nada podía
notarlo, porque **una dirección viva no dice nada sobre si su contenido sigue siendo el mismo**.

El detector nuevo no lo demuestra, lo sugiere: si la página de una fuente cuya edición citamos
como 2020 habla de 2025, puede ser una edición nueva o puede ser una nota al pie. Por eso el
informe dice «conviene mirar» y la decisión sigue siendo de una persona con el documento delante.

Se prueba con una función `traer` de mentira: estas pruebas no salen a internet.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from pedibot.ops.sources_alive import superseded

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture
def catalogo(tmp_path: pathlib.Path):
    """Un config/vaccines.yaml mínimo, para no atar la prueba a los calendarios de verdad."""

    def hacer(paises: dict[str, tuple[str, str]]) -> pathlib.Path:
        d = tmp_path / "config"
        d.mkdir(exist_ok=True)
        datos = {
            "countries": {
                code: {"source": fuente, "source_url": url, "schedule": []}
                for code, (fuente, url) in paises.items()
            }
        }
        (d / "vaccines.yaml").write_text(yaml.safe_dump(datos), encoding="utf-8")
        return tmp_path

    return hacer


def test_the_portuguese_case_that_started_this(catalogo) -> None:
    """El caso real, tal y como ocurrió."""
    raiz = catalogo({"PT": ("PNV 2020, Norma 18/2020 de 27/09/2020", "https://dgs.example/pnv")})
    fuera = superseded(
        raiz,
        ahora=2026,
        traer=lambda u: "O presente PNV substitui, a partir de outubro de 2025, o PNV 2020",
    )
    assert fuera == [("calendario PT", 2020, 2025, "https://dgs.example/pnv")]


def test_a_source_that_still_matches_its_edition_is_quiet(catalogo) -> None:
    raiz = catalogo({"GB": ("NHS schedule 2026", "https://nhs.example/v")})
    assert superseded(raiz, ahora=2026, traer=lambda u: "Page last reviewed 2026") == []


def test_an_older_year_on_the_page_is_not_news(catalogo) -> None:
    """Una página que menciona años ANTERIORES al nuestro no dice nada: casi todas lo hacen, en
    el historial de cambios o en la bibliografía."""
    raiz = catalogo({"ES": ("calendario 2026", "https://san.example/c")})
    pagina = "Sustituye a los calendarios de 2019, 2020, 2021, 2023 y 2025."
    assert superseded(raiz, ahora=2026, traer=lambda u: pagina) == []


def test_a_year_too_far_ahead_is_not_an_edition(catalogo) -> None:
    """Los calendarios se aprueban en diciembre para el año siguiente —el español de 2026 se
    aprobó el 12 de diciembre de 2025—, así que un año de margen es creíble. Cuatro no: eso es un
    objetivo de salud pública o una fecha de caducidad, y tomarlo por una edición nueva llenaría
    el informe de ruido hasta que nadie lo lea."""
    raiz = catalogo({"ES": ("calendario 2026", "https://san.example/c")})
    pagina = "Objetivo de cobertura para 2030. Plan estratégico 2028."
    assert superseded(raiz, ahora=2026, traer=lambda u: pagina) == []


def test_a_source_without_a_year_is_skipped_not_guessed(catalogo) -> None:
    """Sin año citado no hay nada con qué comparar. Se calla, no se inventa."""
    raiz = catalogo({"XX": ("Un calendario cualquiera", "https://x.example/c")})
    assert superseded(raiz, ahora=2026, traer=lambda u: "edición de 2026") == []


def test_a_dead_page_does_not_break_the_weekly_report(catalogo) -> None:
    """Esto corre dentro del informe semanal: una web caída no puede dejar al operador sin él.
    De las fuentes rotas ya avisa la otra mitad del fichero."""

    def revienta(url: str) -> str:
        raise OSError("la red no va")

    raiz = catalogo({"PT": ("PNV 2020", "https://dgs.example/pnv")})
    assert superseded(raiz, ahora=2026, traer=revienta) == []


def test_the_real_calendars_all_state_an_edition_year() -> None:
    """Sin año en la cita, el detector no puede mirar por ese país — se saltaría en silencio."""
    from pedibot.ops.sources_alive import _edicion_citada

    raw = yaml.safe_load((RAIZ / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    sin_año = [c for c, d in raw["countries"].items() if _edicion_citada(str(d["source"])) is None]
    assert not sin_año, f"el detector de caducados no puede vigilar: {sin_año}"
