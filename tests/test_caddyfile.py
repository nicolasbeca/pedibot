"""Reglas del servidor web que se pueden comprobar sin servidor (7-sep-2026).

El Caddyfile no tenía ningún candado, y decide cosas que se ven desde fuera: qué dirección es la
buena, qué se cachea, qué llega al API. Este fichero comprueba lo que se puede comprobar leyendo
el texto — no sustituye a `caddy validate`, que el despliegue ejecuta contra el fichero real.

Lo que motivó escribirlo: **cada página vivía en dos direcciones**, con barra final y sin ella, las
dos contestando 200. Google las trata como páginas distintas y les da puestos distintos — medido
en Search Console a 90 días:

    /dose      10 impresiones, puesto 49,2        /es/dose   35 impresiones, puesto 80,8
    /dose/     17 impresiones, puesto 70,6        /es/dose/   6 impresiones, puesto 61,2

Eso no es un duplicado inofensivo: es la señal de una página repartida entre dos direcciones en
lugar de sumada.
"""

from __future__ import annotations

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[1]
CADDY = (RAIZ / "ops" / "Caddyfile").read_text(encoding="utf-8")


def test_there_is_one_address_per_page() -> None:
    """La barra final redirige a la forma sin barra, que es la que usan el sitemap, las canónicas
    y todos los enlaces internos (comprobado antes de elegir la dirección del arreglo)."""
    assert "@trailingslash" in CADDY, "no está la regla de la barra final"
    assert re.search(r"redir @trailingslash \{re\.tslash\.1\} permanent", CADDY), (
        "la redirección de la barra final tiene que ser permanente (301): una temporal le dice "
        "a Google que siga contando las dos direcciones"
    )


def test_the_api_and_the_panel_are_left_out_of_that_redirect() -> None:
    """Un 301 sobre un POST lo rompe: el navegador reenvía la petición como GET y el cuerpo se
    pierde. El API y el panel tienen que quedar fuera de la regla."""
    bloque = CADDY[CADDY.index("@trailingslash") : CADDY.index("redir @trailingslash")]
    for ruta in ("/api/*", "/a/*", "/admin"):
        assert ruta in bloque, f"{ruta} no está excluido de la redirección de barra final"
    assert bloque.count("not path") == 1


def test_the_root_cannot_be_redirected_to_nothing() -> None:
    """`^(/.+)/$` exige al menos un carácter antes de la barra, así que «/» no casa. Con `(/.*)/$`
    la portada redirigiría a la cadena vacía."""
    m = re.search(r"path_regexp tslash (\S+)", CADDY)
    assert m, "no se encuentra la expresión de la barra final"
    patron = re.compile(m.group(1))
    assert not patron.match("/"), "la portada entraría en la redirección"
    for ruta in ("/dose/", "/es/", "/es/guides/algo/"):
        assert patron.match(ruta), f"{ruta} debería redirigir"
    for ruta in ("/dose", "/es/guides/algo", "/_astro/x.css"):
        assert not patron.match(ruta), f"{ruta} no debería redirigir"


def test_the_static_handler_still_serves_the_slashless_form_directly() -> None:
    """`disable_canonical_uris` sigue haciendo falta: sin él, Caddy contesta un 308 a /guides/x
    mandándolo a /guides/x/, o sea un salto extra en cada dirección del sitemap (26-ago-2026).
    La regla nueva y esta línea son complementarias, no alternativas."""
    assert "disable_canonical_uris" in CADDY


def test_a_broken_config_is_not_applied_in_silence() -> None:
    """El despliegue validaba y mandaba el error a /dev/null, así que un Caddyfile roto se quedaba
    sin aplicar y el despliegue seguía imprimiendo «done» (familia de la L33)."""
    deploy = (RAIZ / "ops" / "deploy.sh").read_text(encoding="utf-8")
    assert "caddy validate" in deploy
    assert "EL CADDYFILE NO VALIDA" in deploy, "el fallo de validación vuelve a ser mudo"
    assert "caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1" not in deploy


def test_the_manifest_is_served_as_a_manifest() -> None:
    """19-sep-2026. La cabecera `X-Content-Type-Options: nosniff` está puesta desde el principio
    y es buena, pero convierte el tipo en obligatorio: Caddy deduce el tipo de la extensión y
    `.webmanifest` no está en su tabla, así que saldría como `octet-stream` y Chrome lo
    rechazaría. Efecto: la web dejaría de poder instalarse, en silencio y sólo en móviles."""
    assert "nosniff" in CADDY, "si esto se cae, el tipo del manifiesto deja de ser crítico"
    assert 'Content-Type "application/manifest+json"' in CADDY, (
        "el manifiesto tiene que salir con su tipo o el teléfono no lo acepta"
    )


def test_the_service_worker_is_never_cached_for_long() -> None:
    """Es el interruptor de emergencia: si algún día hay que apagar el modo sin conexión, se
    despliega un `sw.js` que se desregistra. Servido con caché larga, esa orden tardaría un año
    en llegar a quien ya lo tiene instalado."""
    assert "/sw.js" in CADDY, "el trabajador no tiene regla propia de caché"
    assert 'Cache-Control "no-cache, max-age=0"' in CADDY
