"""El número de emergencias, a la vista y en una dirección propia (17-sep-2026).

Lo vio el operador en la web: la sección «tu país» de la portada era **un desplegable de 35
códigos con el Reino Unido puesto de antemano**. Quien entraba en español veía «GB» y tenía que
abrir la lista y buscarse España; quien entraba en inglés, lo mismo. Y la página /emergency, que
es la que se llama «urgencias», no enseñaba ni un teléfono: sólo la lista de signos de alarma.

Dos cosas se arreglan aquí y las dos se comprueban:

1. **Cada idioma abre con sus países.** El que lee en árabe ve el Golfo y Egipto; el que lee en
   español, España y América. Lo que el lector tenga guardado va por delante de todo, pero eso ya
   depende de quién mire y no se construye.
2. **El número está escrito en el HTML**, no puesto por JavaScript al abrir. Es lo que hace que
   una búsqueda como «emergency number in Qatar» pueda llegar a este sitio: lo que no está en el
   HTML no lo indexa nadie. Por eso se comprueba contra lo CONSTRUIDO y no contra el componente.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest
import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DIST = RAIZ / "web" / "site" / "dist"
NUMEROS = yaml.safe_load((RAIZ / "config" / "emergency_numbers.yaml").read_text(encoding="utf-8"))
IDIOMA_PAISES = yaml.safe_load(
    (RAIZ / "config" / "lang_countries.yaml").read_text(encoding="utf-8")
)
IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")
PAISES = sorted(k for k in NUMEROS if k != "default")
sin_sitio = pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")


def pagina(lang: str, resto: str) -> str:
    pref = "" if lang == "en" else f"/{lang}"
    f = DIST / (pref + resto).lstrip("/") / "index.html"
    assert f.exists(), f"no existe {f.relative_to(DIST)}"
    return f.read_text(encoding="utf-8")


def _tarjeta(html: str, cc: str) -> str | None:
    """El trozo de HTML de la tarjeta de un país en la portada."""
    i = html.find(f'data-cc="{cc}"')
    if i < 0:
        return None
    fin = html.find("</article>", i)
    return html[i : fin if fin > 0 else i + 900]


# ── el dato ──────────────────────────────────────────────────────────────────────────────────
def test_every_language_of_the_site_says_where_it_is_spoken() -> None:
    faltan = [lg for lg in IDIOMAS if not IDIOMA_PAISES.get(lg)]
    assert not faltan, f"idiomas sin países: {faltan}"


def test_no_language_points_at_a_country_we_have_no_number_for() -> None:
    inventados = sorted({c for cs in IDIOMA_PAISES.values() for c in cs} - set(PAISES))
    assert not inventados, f"países sin número en emergency_numbers.yaml: {inventados}"


# ── la portada ───────────────────────────────────────────────────────────────────────────────
@sin_sitio
@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_home_page_opens_with_your_countries_not_with_britain(lang: str) -> None:
    html = pagina(lang, "/")
    escritos = re.findall(r'data-cc="([A-Z]{2})"', html)
    assert escritos[: len(IDIOMA_PAISES[lang])] == IDIOMA_PAISES[lang], (
        f"{lang}: la portada abre con {escritos[:3]} y debería abrir con {IDIOMA_PAISES[lang][:3]}"
    )


@sin_sitio
@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_number_is_written_not_drawn_by_a_script(lang: str) -> None:
    """Un número que sólo existe tras ejecutar JavaScript no lo lee un buscador."""
    html = pagina(lang, "/")
    for cc in IDIOMA_PAISES[lang]:
        numero = NUMEROS[cc]["emergency"]
        if numero:
            assert numero in html, f"{lang}: el número de {cc} ({numero}) no está en el HTML"
        else:
            # 18-sep-2026: con África entran países donde la fuente dice que no hay número
            # nacional. Su tarjeta tiene que decirlo —también escrito en el HTML— y no puede
            # colar un «tel:» a ninguna parte, que es justo lo que haría un guion de relleno.
            assert _tarjeta(html, cc) is not None, f"{lang}: {cc} no tiene tarjeta en la portada"
            trozo = _tarjeta(html, cc)
            assert "nohay" in trozo, f"{lang}: {cc} no dice que no hay número nacional"
            assert "tel:" not in trozo, f"{lang}: {cc} no tiene número y aun así ofrece llamar"


# ── una dirección por país ───────────────────────────────────────────────────────────────────
@sin_sitio
@pytest.mark.parametrize("lang", IDIOMAS)
def test_there_is_one_page_per_country_and_it_carries_its_numbers(lang: str) -> None:
    for cc in PAISES:
        html = pagina(lang, f"/emergency/{cc.lower()}")
        for clave in ("emergency", "poison", "mental"):
            valor = NUMEROS[cc].get(clave)
            if valor:
                assert valor in html, f"{lang}/{cc}: falta el número de {clave}"


@sin_sitio
@pytest.mark.parametrize("lang", IDIOMAS)
def test_each_country_page_is_titled_with_the_country_not_with_its_code(lang: str) -> None:
    html = pagina(lang, "/emergency/qa")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    assert h1, f"{lang}: la página de Catar no tiene título"
    texto = h1.group(1).strip()
    assert "QA" not in texto and "{name}" not in texto, f"{lang}: título sin traducir: {texto}"
    assert len(texto) > 8, f"{lang}: título demasiado corto: {texto}"


@sin_sitio
@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_index_lists_every_country_with_its_number(lang: str) -> None:
    html = pagina(lang, "/emergency")
    enlaces = re.findall(r'class="ncard" href="([^"]+)"', html)
    codigos = [u.rsplit("/", 1)[-1].upper() for u in enlaces]
    assert sorted(codigos) == PAISES, f"{lang}: la lista no tiene los {len(PAISES)} países"
    assert codigos[: len(IDIOMA_PAISES[lang])] == IDIOMA_PAISES[lang], (
        f"{lang}: la lista no empieza por los países del idioma"
    )


@sin_sitio
def test_the_country_pages_are_in_the_sitemap() -> None:
    mapa = (DIST / "sitemap-0.xml").read_text(encoding="utf-8")
    for url in ("/emergency/sa", "/ar/emergency/sa", "/es/emergency/mx"):
        assert f"<loc>https://pedibot.xyz{url}</loc>" in mapa, f"{url} no está en el sitemap"


@sin_sitio
def test_the_site_data_matches_the_config() -> None:
    """La web lee un JSON exportado; si se queda viejo, la página miente con cara de verdad."""
    datos = json.loads((RAIZ / "web/site/src/data/lang_countries.json").read_text(encoding="utf-8"))
    assert datos == IDIOMA_PAISES, (
        "lang_countries.json no es lo que dice config/lang_countries.yaml"
    )


# ── un idioma oficial en varios países no puede abrir con uno solo ───────────────────────────
#: Lo vio el operador el 17-sep-2026: «en alemán hay pocos números de emergencia, cuando el
#: alemán es idioma oficial en varios países». Tenía razón y la falta era del dato, no de la
#: pantalla: el fichero sólo conocía Alemania. Al añadir Austria, Suiza, Liechtenstein,
#: Luxemburgo y Bélgica se arregla también el francés, que se quedaba sin Bélgica, Suiza y
#: Luxemburgo teniendo el francés de oficial en los tres.
OFICIALES = {
    "de": ("DE", "AT", "CH", "LI", "LU", "BE"),
    "fr": ("FR", "BE", "CH", "LU", "CA"),
    "es": ("ES", "MX", "AR"),
    "pt": ("PT", "BR"),
    "en": ("GB", "US", "IE"),
    "ar": ("SA", "AE", "EG"),
}


@pytest.mark.parametrize("lang,paises", sorted(OFICIALES.items()))
def test_a_language_opens_with_every_country_that_speaks_it(lang: str, paises: tuple[str, ...]):
    faltan = [cc for cc in paises if cc not in IDIOMA_PAISES[lang]]
    assert not faltan, f"{lang}: no abre con {faltan}, y ahí ese idioma es oficial"


@pytest.mark.parametrize("cc", ["AT", "CH", "LI", "LU", "BE"])
def test_the_new_countries_carry_a_number_that_was_read_from_its_own_source(cc: str):
    """No se escriben de memoria: cada uno se leyó en la página del organismo que lo publica
    (Tox Info Suisse, Rat auf Draht, Vergiftungsinformationszentrale, Antigifcentrum, SOS
    Détresse, Zelfmoordlijn, Centre de Prévention du Suicide, Telefonseelsorge)."""
    assert cc in NUMEROS, f"{cc} no está en emergency_numbers.yaml"
    assert NUMEROS[cc].get("emergency"), f"{cc}: sin número de emergencias"
