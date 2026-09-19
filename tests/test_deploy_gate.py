"""La puerta del despliegue tiene que distinguir «está roto» de «no he podido mirar» (10-sep-2026).

La comprobación final de `deploy.sh` se murió en seco en la máquina del operador —un choque de
OpenSSL de Windows, ajeno al proyecto— y el despliegue imprimió:

    !! el sitio responde mal a algo, mira arriba

El sitio estaba perfecto: salud en verde, las ocho lenguas a 200, la portada a 200. La línea era
`uv run python ops/smoke.py || echo "!! el sitio responde mal"`, y `||` no distingue «he mirado y
está mal» de «no he podido mirar».

Las dos cosas son malas y piden cosas distintas —arreglar el sitio, o arreglar la comprobación y
saber que se ha desplegado a ciegas— y confundirlas tiene el precio de siempre: un aviso que a
veces miente se acaba ignorando, y entonces no sirve la vez que acierta.

El primer arreglo fue un código de salida propio, y **no valía**: el choque mata el proceso antes
de que corra ningún `except`, y el sistema devuelve 1, que es justo el código de «el sitio está
mal». Un proceso que se muere no deja escrito por qué. Así que la señal tiene que ser algo que
sólo se escribe **al llegar al final** — una firma cuya ausencia es imposible de falsificar.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DEPLOY = RAIZ / "ops" / "deploy.sh"
SMOKE = RAIZ / "ops" / "smoke.py"


def test_la_comprobacion_firma_cuando_llega_al_final() -> None:
    """`smoke.py` escribe la firma en los dos finales buenos: con fallos y sin ellos."""
    texto = SMOKE.read_text(encoding="utf-8")
    assert 'FIRMA = "SMOKE-FIN"' in texto, "la firma ha cambiado de nombre o ha desaparecido"
    # una sola línea la imprime, y está después de decidir si hay fallos
    assert texto.count('print(f"{FIRMA}') == 1, (
        "la firma debe imprimirse en un único sitio, al final de main(), o dejará de significar "
        "«he llegado hasta aquí»"
    )


def test_el_despliegue_mira_la_firma_y_no_solo_el_codigo() -> None:
    """Si vuelve el `||` a secas, un choque de la comprobación se leerá como un sitio roto."""
    texto = DEPLOY.read_text(encoding="utf-8")
    trozo = texto[texto.index("comprobación del sitio") :]
    trozo = trozo[: trozo.index("== done")]
    assert "SMOKE-FIN" in trozo, (
        "deploy.sh ya no busca la firma de la comprobación: un choque suyo volverá a contarse "
        "como que el sitio responde mal"
    )
    assert not re.search(r"smoke\.py[^\n]*\|\|", trozo), (
        "ha vuelto el `|| echo` a secas, que no distingue «he mirado y está mal» de «no he "
        "podido mirar»"
    )
    assert "ha ido a ciegas" in trozo, "falta decir que el despliegue se hizo sin comprobar"


def _rama(salida: str, codigo: int) -> str:
    """La misma decisión que toma deploy.sh, ejecutada de verdad."""
    guion = f"""
salida={salida!r}; codigo={codigo}
if ! grep -q "SMOKE-FIN" <<<"$salida"; then echo ciegas
elif [ "$codigo" -ne 0 ]; then echo sitio_mal
else echo bien; fi
"""
    return subprocess.run(
        ["bash", "-c", guion], capture_output=True, text=True, check=True
    ).stdout.strip()


def test_las_tres_ramas_deciden_lo_que_deben() -> None:
    """Las tres situaciones, con la lógica del guion corriendo de verdad y no leída."""
    assert _rama("drugs ok\ntodo en pie\nSMOKE-FIN fallos=0", 0) == "bien"
    assert _rama("checklist[ru] MAL 500\nFALLOS: 1\nSMOKE-FIN fallos=1", 1) == "sitio_mal"
    # lo que pasó: el proceso muere y el sistema devuelve 1, igual que un sitio roto
    assert _rama("OPENSSL_Uplink(...): no OPENSSL_Applink", 1) == "ciegas"
    # y el caso que más engaña: muere devolviendo 0
    assert _rama("", 0) == "ciegas"


def test_a_broken_site_build_stops_the_deploy() -> None:
    """19-sep-2026, familia de la L33.

    La línea que construye el sitio en el servidor acababa en `| grep`, así que el código de
    salida era el del grep y no el del build. El día que el build falló de verdad —faltaba una
    carpeta que el despliegue no copiaba— el servidor se quedó con el sitio de antes, el error
    pasó entre las demás líneas y el despliegue llegó hasta «done». Todo verde, nada desplegado.
    """
    deploy = (RAIZ / "ops" / "deploy.sh").read_text(encoding="utf-8")
    assert "set -o pipefail" in deploy, "sin esto, el código de salida es el del grep"
    assert "EL SITIO NO SE HA CONSTRUIDO" in deploy, "el fallo vuelve a ser mudo"


def test_the_deploy_carries_what_the_build_needs() -> None:
    """El paso `prebuild` vive en web/site/scripts/. Si esa carpeta no viaja, el build del
    servidor se rompe justo ahí — y eso es lo que pasó."""
    deploy = (RAIZ / "ops" / "deploy.sh").read_text(encoding="utf-8")
    assert "web/site/scripts" in deploy
    paquete = json.loads((RAIZ / "web" / "site" / "package.json").read_text(encoding="utf-8"))
    guion = paquete["scripts"].get("prebuild", "")
    assert guion, "si se quita el prebuild, esta prueba sobra; mientras exista, tiene que viajar"
    assert (RAIZ / "web" / "site" / "scripts").is_dir()
