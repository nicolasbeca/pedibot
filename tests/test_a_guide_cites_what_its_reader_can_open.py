"""Una guía en hindi no puede citar sólo hojas en castellano (16-sep-2026).

Medido sobre lo publicado: **20 de las 62 guías en hindi y 20 de las 62 en árabe citan
únicamente organismos que publican en castellano** —SEUP, AEP, Junta de Andalucía—, y otras 25
de cada lengua los mezclan. La guía de la fiebre en hindi lleva cinco fuentes y las cinco son la
misma hoja del SEUP, en castellano.

La causa está en una línea: `gather_hits(index, topic)` **no sabe en qué lengua se va a
escribir**. Elige las mismas anclas para las ocho, y las anclas son españolas porque el corpus
empezó en castellano. El material inglés existe para todos esos temas —de 21 a 405 pasajes por
tema— y el padre indio o del Golfo sí puede abrirlo.

Es el mismo principio que el buscador ya aplica desde hoy (`_one_readable_up_front`): comprobar
es lo único que este producto ofrece por encima de un buscador, y una fuente que el lector no
puede abrir no se puede comprobar.

Y la segunda mitad, que es de URL. Regenerar una guía le cambia el título y, con él, el nombre
del fichero — y eso hay que conservarlo: así se arreglaron slugs mal transliterados como
«was_tun_bei_einer_erk_ltung». Lo que no puede pasar es que la dirección vieja muera, como pasó
al regenerar la de la cefalea en inglés: quedó en nada con todo lo que Google tenía indexado.
Ahora el publicador anota cada renombrado en `web/content/_redirects.json` y el sitio las sirve.
"""

from __future__ import annotations

import pytest

from pedibot.index.store import READABLE_FALLBACK, Index
from pedibot.publish.articles import gather_hits
from pedibot.settings import ROOT

CONTENIDO = ROOT / "web" / "content"


@pytest.fixture(scope="module")
def index() -> Index:
    return Index(ROOT / "index" / "pedibot.db")


#: temas con guía publicada en hindi y árabe que hoy sólo citan material en castellano
TEMAS = ["fiebre", "dolor_abdominal", "bronquiolitis", "estrenimiento", "vomitos", "cefalea"]


@pytest.mark.parametrize("lang", ["hi", "ar"])
@pytest.mark.parametrize("topic", TEMAS)
def test_las_fuentes_de_una_guia_se_pueden_abrir(index: Index, lang: str, topic: str) -> None:
    legibles = {lang, READABLE_FALLBACK.get(lang, "en")}
    hits = gather_hits(index, topic, lang=lang)
    assert hits, f"{topic}/{lang} sin fuentes"
    n = sum(1 for h in hits if h.chunk.lang in legibles)
    idiomas = [h.chunk.lang for h in hits]
    # Tres, y la primera: el modelo cita por orden, y el corpus no siempre tiene diez pasajes
    # ingleses de un tema (de la fiebre hay tres). Antes eran CERO en los seis temas.
    assert n >= 3, f"{topic}/{lang}: sólo {n} de {len(hits)} fuentes se pueden abrir ({idiomas})"
    assert hits[0].chunk.lang in legibles, f"{topic}/{lang}: abre con {idiomas}"


@pytest.mark.parametrize("topic", TEMAS)
def test_y_en_castellano_no_cambia_nada(index: Index, topic: str) -> None:
    """La dirección de la que vive el corpus —inglés y castellano— se queda como estaba."""
    hits = gather_hits(index, topic, lang="es")
    assert hits and any(h.chunk.lang == "es" for h in hits)


def test_una_guia_regenerada_deja_su_direccion_redirigida(tmp_path) -> None:
    """Renombrar sí (así se arreglan slugs mal transliterados); dejar la dirección muerta, no."""
    import json

    from pedibot.bot.llm import LLMResult
    from pedibot.publish.articles import Article, redirects_path, write_article

    salida = LLMResult("x", 10, 10, 0.0, "modelo-de-prueba")
    contenido = tmp_path / "content"
    cola = tmp_path / "queue"

    def guia(titulo: str, cuerpo: str) -> Article:
        return Article(
            "fiebre",
            "hi",
            titulo,
            "resumen",
            "## X\n\n" + cuerpo,
            ["[1] NHS"],
            ["nhs_en_fever#s#1"],
            salida,
            "ok",
        )

    vieja, _ = write_article(
        guia("bukhaar hone par kya karen", "cuerpo"), contenido, cola, "https://pedibot.xyz"
    )
    nueva, _ = write_article(
        guia("bachche ko bukhaar", "otro cuerpo"), contenido, cola, "https://pedibot.xyz"
    )
    assert nueva != vieja and not vieja.exists(), "la vieja tiene que desaparecer del contenido"
    assert len(list((contenido / "hi").glob("*.md"))) == 1, "ha quedado una huérfana"
    mapa = json.loads(redirects_path(contenido).read_text(encoding="utf-8"))
    assert mapa[f"/hi/guides/{vieja.stem}"] == f"/hi/guides/{nueva.stem}"

    # y un tercer nombre no encadena dos saltos: la primera apunta ya a la última
    tercera, _ = write_article(
        guia("bukhaar ka ilaaj", "tercer cuerpo"), contenido, cola, "https://pedibot.xyz"
    )
    mapa = json.loads(redirects_path(contenido).read_text(encoding="utf-8"))
    assert mapa[f"/hi/guides/{vieja.stem}"] == f"/hi/guides/{tercera.stem}"
    assert f"/hi/guides/{tercera.stem}" not in mapa, "la dirección viva no se redirige a sí misma"


def test_el_sitio_sirve_esas_redirecciones() -> None:
    """El fichero no vale de nada si el sitio no lo lee al construirse."""
    config = (ROOT / "web" / "site" / "astro.config.mjs").read_text(encoding="utf-8")
    assert "_redirects.json" in config and "redirects:" in config
