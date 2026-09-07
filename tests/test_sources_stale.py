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


#: Una página real tiene miles de bytes de menús, avisos de cookies y pie. Las de estas pruebas se
#: rellenan hasta ese tamaño a propósito: desde el 7-sep-2026 una respuesta demasiado corta se
#: considera ILEGIBLE y se dice, en vez de pasar por «no hay nada nuevo».
RELLENO = "<p>menú, migas de pan, aviso de cookies, pie de página. </p>" * 60


def pagina(texto: str) -> str:
    return RELLENO + texto + RELLENO


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
        traer=lambda u: pagina("O presente PNV substitui, a partir de outubro de 2025, o PNV 2020"),
    )
    assert fuera == [("calendario PT", 2020, 2025, "https://dgs.example/pnv")]


def test_a_source_that_still_matches_its_edition_is_quiet(catalogo) -> None:
    raiz = catalogo({"GB": ("NHS schedule 2026", "https://nhs.example/v")})
    assert superseded(raiz, ahora=2026, traer=lambda u: pagina("Page last reviewed 2026")) == []


def test_an_older_year_on_the_page_is_not_news(catalogo) -> None:
    """Una página que menciona años ANTERIORES al nuestro no dice nada: casi todas lo hacen, en
    el historial de cambios o en la bibliografía."""
    raiz = catalogo({"ES": ("calendario 2026", "https://san.example/c")})
    texto = pagina("Este calendario sustituye a los de 2019, 2020, 2021, 2023 y 2025.")
    assert superseded(raiz, ahora=2026, traer=lambda u: texto) == []


def test_a_year_too_far_ahead_is_not_an_edition(catalogo) -> None:
    """Los calendarios se aprueban en diciembre para el año siguiente —el español de 2026 se
    aprobó el 12 de diciembre de 2025—, así que un año de margen es creíble. Cuatro no: eso es un
    objetivo de salud pública o una fecha de caducidad, y tomarlo por una edición nueva llenaría
    el informe de ruido hasta que nadie lo lea."""
    raiz = catalogo({"ES": ("calendario 2026", "https://san.example/c")})
    texto = pagina("Calendario vigente. Objetivo de cobertura para 2030. Plan 2028.")
    assert superseded(raiz, ahora=2026, traer=lambda u: texto) == []


def test_a_source_without_a_year_is_skipped_not_guessed(catalogo) -> None:
    """Sin año citado no hay nada con qué comparar. Se calla, no se inventa."""
    raiz = catalogo({"XX": ("Un calendario cualquiera", "https://x.example/c")})
    assert superseded(raiz, ahora=2026, traer=lambda u: pagina("edición de 2026")) == []


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


# --- lo que se aprendió al usarlo de verdad (7-sep-2026) ---------------------------------------


def test_a_cohort_or_a_campaign_year_is_not_an_edition(catalogo) -> None:
    """El aviso saltaba por años que no son ediciones.

    La página del NHS dice «MenB ... until March 2027» (una campaña de repesca) y «born on or
    after 1 January 2025» (una cohorte). Con la primera versión el aviso habría salido cada
    semana por esos años, y un aviso que sale siempre deja de leerse — que es como muere un aviso.
    Medido sobre la página real: de cuatro años señalados se pasó a uno, y ese uno era su
    `dateModified` de verdad.
    """
    raiz = catalogo({"GB": ("NHS schedule, consultada 2026", "https://nhs.example/v")})
    ruido = pagina(
        "The MenB vaccine is now offered, until March 2027, to young people who were born "
        "between 2007 and 2008. MMRV for children born on or after 1 January 2025."
    )
    assert superseded(raiz, ahora=2026, traer=lambda u: ruido) == []


def test_an_edition_word_next_to_the_year_still_fires(catalogo) -> None:
    """La otra mitad: estrechar el detector no puede dejarlo ciego."""
    raiz = catalogo({"GB": ("NHS schedule 2023", "https://nhs.example/v")})
    fuera = superseded(
        raiz, ahora=2026, traer=lambda u: pagina("This schedule was last reviewed in 2026.")
    )
    assert [f[2] for f in fuera] == [2026]


def test_a_page_too_short_to_read_is_reported_not_swallowed(catalogo) -> None:
    """Medido el 7-sep-2026: la página del CDC devuelve **427 bytes** de HTML cortado a media
    etiqueta, con un 200 limpio. Sin esta comprobación el detector no encuentra ningún año y
    concluye «no hay nada más nuevo» — una fuente ilegible leída como una fuente sana, que es el
    peor error posible en algo cuyo trabajo es avisar."""
    raiz = catalogo({"US": ("CDC schedule 2025", "https://cdc.example/c")})
    ilegibles: list[tuple[str, str, str]] = []
    fuera = superseded(
        raiz, ahora=2026, traer=lambda u: "<!DOCTYPE html><html><head>", unreadable=ilegibles
    )
    assert fuera == [], "no se puede afirmar nada de una página que no se ha podido leer"
    assert ilegibles and ilegibles[0][0] == "calendario US"
    assert "bytes" in ilegibles[0][1]


def test_a_source_that_does_not_answer_is_also_reported(catalogo) -> None:
    def revienta(url: str) -> str:
        raise OSError("la red no va")

    raiz = catalogo({"PT": ("PNV 2020", "https://dgs.example/pnv")})
    ilegibles: list[tuple[str, str, str]] = []
    assert superseded(raiz, ahora=2026, traer=revienta, unreadable=ilegibles) == []
    assert ilegibles == [("calendario PT", "no responde", "https://dgs.example/pnv")]


def test_a_build_date_in_the_page_metadata_is_not_an_edition(catalogo) -> None:
    """El aviso saltaba por la fecha de compilación del CDC, que vive en el JSON-LD y que ningún
    lector ve. La fecha con la que se generó una página no es la fuente diciendo nada sobre su
    edición: lo que cuenta es lo que se lee."""
    raiz = catalogo({"US": ("CDC schedule 2025", "https://cdc.example/c")})
    html = pagina(
        '<script type="application/ld+json">{"dateModified":"2026-09-01","name":"schedule"}'
        "</script> Recommended immunization schedule, July 2, 2025."
    )
    assert superseded(raiz, ahora=2026, traer=lambda u: html) == []


def test_a_new_edition_in_the_visible_text_still_fires(catalogo) -> None:
    """La otra mitad, otra vez: no vale quedarse ciego por quitar ruido."""
    raiz = catalogo({"US": ("CDC schedule 2025", "https://cdc.example/c")})
    html = pagina("<h1>Recommended immunization schedule for 2026</h1>")
    assert [f[2] for f in superseded(raiz, ahora=2026, traer=lambda u: html)] == [2026]


# --- el clasificador daba por mudanza inocente un cambio de tema (7-sep-2026) ------------------
#
# `_palabras()` sacaba las palabras de la dirección ENTERA, sitio incluido. Como una redirección
# casi siempre se queda dentro del mismo sitio, «medlineplus» o «nhs» aparecía en las dos y la
# regla «si no comparten ninguna palabra, cambió de tema» nunca podía dispararse dentro de un
# mismo dominio. Medido: medlineplus.gov/bedwetting.html → medlineplus.gov/childdevelopment.html
# salía como mudanza — y las mudanzas solo se cuentan si hay cinco o más, así que ni se veía.
#
# Es el caso de la L24 y es el peligroso: el enlace responde, así que nada parece roto, pero la
# página ya no sostiene lo que se cita.


def _clase(antes: str, ahora: str) -> str:
    from pedibot.ops.sources_alive import _palabras

    a, b = _palabras(antes), _palabras(ahora)
    return "tema" if a and not (a & b) else "movida"


def test_a_redirect_to_another_subject_is_not_a_move() -> None:
    assert (
        _clase(
            "https://medlineplus.gov/bedwetting.html",
            "https://medlineplus.gov/childdevelopment.html",
        )
        == "tema"
    )


def test_a_real_move_inside_the_same_site_stays_quiet() -> None:
    """El NHS pasó /conditions/ a /symptoms/. Eso es una mudanza y no debe gritar."""
    assert (
        _clase(
            "https://www.nhs.uk/conditions/headaches-in-children/",
            "https://www.nhs.uk/symptoms/headaches/",
        )
        == "movida"
    )


def test_the_site_name_never_counts_as_a_shared_subject() -> None:
    """La causa exacta del fallo, dicha aparte: el sitio no dice nada sobre el tema."""
    from pedibot.ops.sources_alive import _palabras

    assert "medlineplus" not in _palabras("https://medlineplus.gov/bedwetting.html")
    assert "nhs" not in _palabras("https://www.nhs.uk/conditions/fever/")
