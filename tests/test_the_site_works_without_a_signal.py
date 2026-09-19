"""El sitio sin cobertura, y las dos reglas que no se pueden romper (19-sep-2026).

Fase F1 del plan de `APP.md`, y es lo primero que se construye por un motivo que no es técnico:
**sin red, una web es una pantalla en blanco**. El proyecto apunta a India, el mundo árabe y
África, donde la cobertura se acaba a mitad de mes, y lo que hace falta a las tres de la mañana
—el número al que llamar, los signos que significan ir ya, la próxima vacuna— no cambia de un día
para otro.

Esto comprueba la ESTRUCTURA, no el comportamiento: aquí no hay navegador que ejecute el
trabajador ni forma de cortarle la red. Lo que sí se puede sujetar, y es donde estaría el daño,
son las dos reglas de las que sale todo lo demás:

  1. **Las páginas van a la red primero.** Un calendario de vacunas de hace ocho meses servido
     desde el teléfono es peor que no tener nada, y aquí se corrigen datos todas las semanas.
  2. **La API no se guarda jamás.** Una respuesta del chat es para una pregunta, un niño y un
     momento. Volver a enseñarla por estar en la caché sería contestar a otra cosa.

Y lo tonto pero necesario: que los iconos que el manifiesto promete existan de verdad. Un
manifiesto que apunta a un fichero que no está no falla en ninguna parte — simplemente el
teléfono instala la app sin icono.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
SITE = RAIZ / "web" / "site"
PUBLICO = SITE / "public"
DIST = SITE / "dist"

SW = PUBLICO / "sw.js"
MANIFIESTO = PUBLICO / "manifest.webmanifest"


def test_the_worker_and_the_manifest_are_there() -> None:
    assert SW.exists(), "no hay service worker: el sitio no funciona sin cobertura"
    assert MANIFIESTO.exists(), "no hay manifiesto: el sitio no se puede instalar"


def test_the_api_is_never_cached() -> None:
    """La regla que más duele si se rompe: una respuesta guardada contestaría a otra pregunta."""
    codigo = SW.read_text(encoding="utf-8")
    assert "'/api/'" in codigo or '"/api/"' in codigo, "el trabajador no menciona la API"
    guardia = re.search(r"if \([^)]*startsWith\('/api/'\)[^{]*\{\s*return;", codigo, re.S)
    assert guardia, "la API tiene que salir del trabajador con un `return`, sin guardarse"


def test_a_page_goes_to_the_network_first() -> None:
    """Y la segunda: lo guardado sólo aparece cuando la red falla, nunca antes."""
    codigo = SW.read_text(encoding="utf-8")
    navegacion = codigo[codigo.index("esNavegacion(req)") :]
    pide_red = navegacion.index("await fetch(req)")
    mira_cache = navegacion.index("caches.match(req)")
    assert pide_red < mira_cache, (
        "el trabajador mira la caché antes que la red: un dato viejo se serviría estando "
        "disponible el bueno"
    )
    assert "catch" in navegacion[pide_red:mira_cache], (
        "la caché tiene que estar dentro del `catch` de la red, no antes"
    )


def test_the_worker_cleans_up_after_itself() -> None:
    codigo = SW.read_text(encoding="utf-8")
    assert re.search(r"const VERSION\s*=", codigo), "sin versión no hay forma de invalidar nada"
    assert "caches.delete" in codigo, "una versión nueva tiene que borrar las viejas"


def test_the_manifest_promises_only_icons_that_exist() -> None:
    datos = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    for clave in ("name", "short_name", "start_url", "display", "icons", "theme_color"):
        assert datos.get(clave), f"al manifiesto le falta «{clave}»"
    iconos = list(datos["icons"])
    for atajo in datos.get("shortcuts", []):
        iconos += atajo.get("icons", [])
    for icono in iconos:
        ruta = PUBLICO / icono["src"].lstrip("/")
        assert ruta.exists(), f"el manifiesto promete {icono['src']} y no está en public/"
    tamaños = {i["sizes"] for i in datos["icons"]}
    assert {"192x192", "512x512"} <= tamaños, f"faltan los tamaños que pide Android: {tamaños}"


@pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")
def test_the_offline_page_speaks_every_language() -> None:
    """Quien acaba en ella no tiene red para cambiar de idioma, y pudo llegar desde cualquiera
    de las ocho ediciones."""
    pagina = DIST / "offline" / "index.html"
    assert pagina.exists(), "no se construyó la página de sin conexión"
    html = pagina.read_text(encoding="utf-8")
    for frase in (
        "No connection",
        "Sin conexión",
        "Pas de connexion",
        "Keine Verbindung",
        "Нет соединения",
        "لا يوجد اتصال",
        "Sem ligação",
        "कोई कनेक्शन नहीं",
    ):
        assert frase in html, f"la página de sin conexión no dice nada en la lengua de «{frase}»"
    assert 'href="/emergency"' in html, "sin el enlace a los números no sirve de mucho"


@pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")
@pytest.mark.parametrize("rel", ["index.html", "es/index.html", "ar/emergency/index.html"])
def test_every_page_declares_the_manifest_and_registers_the_worker(rel: str) -> None:
    html = (DIST / rel).read_text(encoding="utf-8")
    assert 'rel="manifest"' in html, f"{rel}: sin manifiesto no se puede instalar"
    assert "serviceWorker" in html, f"{rel}: esta página no registra el trabajador"
    assert "location.protocol === 'https:'" in html, (
        f"{rel}: el registro tiene que estar limitado a https"
    )


@pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")
def test_the_worker_ships_at_the_root() -> None:
    """Un trabajador servido desde una subcarpeta sólo alcanza esa subcarpeta."""
    assert (DIST / "sw.js").exists(), "sw.js no llegó a la raíz del sitio construido"
    assert (DIST / "manifest.webmanifest").exists(), "el manifiesto no llegó a la raíz"


def test_a_hashed_asset_is_not_asked_for_twice() -> None:
    """Lo que lleva el hash en el nombre no cambia nunca.

    La primera versión de este trabajador lo devolvía de la caché **y además lo pedía a la red**
    para la próxima vez, que es lo correcto para lo que no lleva hash y un gasto tonto para lo
    que sí: el lector paga los datos de recibir byte a byte lo mismo que ya tiene. En un móvil
    con datos contados, que es el de casi todo el público al que apunta el proyecto, eso importa
    más que cualquier milisegundo.
    """
    codigo = SW.read_text(encoding="utf-8")
    assert re.search(r"if \(guardada && INMUTABLE\.test\([^)]*\)\) return guardada;", codigo), (
        "lo inmutable, si está guardado, se devuelve sin volver a pedirlo"
    )


#: Los datos que el trabajador guarda al instalarse. Es lo que hace que «funciona sin cobertura»
#: signifique algo el día que a alguien se le acaban los datos: los 88 países con su número, los
#: 61 calendarios y las 69 tablas, dentro del teléfono antes de hacer falta.
DATOS_SIN_RED = (
    "emergency.json",
    "vaccines.json",
    "growth_charts.json",
    "checklist.json",
    "drugs.json",
    "dose_table.json",
)


@pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")
@pytest.mark.parametrize("fichero", DATOS_SIN_RED)
def test_the_data_is_published_as_files(fichero: str) -> None:
    """Los JSON de `src/data/` los usa Astro al construir y acaban DENTRO del HTML. Eso vale con
    red y no vale sin ella, así que además se publican como ficheros y el trabajador se los
    guarda al instalarse (F1b)."""
    f = DIST / "offline-data" / fichero
    assert f.exists(), f"{fichero} no se publicó: el paso `prebuild` no corrió"
    assert f.stat().st_size > 1000, f"{fichero} se publicó vacío"
    json.loads(f.read_text(encoding="utf-8"))


def test_the_worker_asks_for_all_of_them_on_install() -> None:
    codigo = SW.read_text(encoding="utf-8")
    faltan = [f for f in DATOS_SIN_RED if f"/offline-data/{f}" not in codigo]
    assert not faltan, f"el trabajador no guarda {faltan}: sin red, esas páginas no tendrán datos"
    assert "/emergency" in codigo, "los números de emergencia son lo primero que hay que tener"


def test_the_prebuild_step_is_wired_in() -> None:
    """Si el paso se cae del package.json, el sitio sigue construyendo perfecto y la promesa de
    funcionar sin cobertura se queda en nada, en silencio."""
    paquete = json.loads((SITE / "package.json").read_text(encoding="utf-8"))
    assert "prebuild" in paquete["scripts"], "sin `prebuild` los datos no se publican"
    assert "publish-offline-data" in paquete["scripts"]["prebuild"]
