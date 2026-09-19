"""La pantalla de la cuenta no puede empezar en blanco (19-sep-2026).

`/family` se construye con los dos bloques dentro —el de «entra o crea cuenta» y el de «estos
son tus hijos»— y JavaScript decide cuál se ve. La primera versión los dejaba **ocultos a los
dos** hasta que contestara `/api/family/me`, y eso es una pantalla en blanco: un parpadeo con
fibra, varios segundos en 2G y para siempre sin JavaScript.

Y como es un sitio que apunta a India, África y el mundo árabe, «varios segundos en 2G» no es un
caso raro: es el caso.

También se comprueba aquí que un hijo se pueda **corregir** sin borrarlo. Una fecha de nacimiento
mal tecleada corre la curva entera y todas las vacunas; si la única salida fuera borrar al hijo,
se irían con él todas sus medidas.
"""

from __future__ import annotations

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DIST = RAIZ / "web" / "site" / "dist"
COMPONENTE = (RAIZ / "web" / "site" / "src" / "components" / "Family.astro").read_text(
    encoding="utf-8"
)

pytestmark = pytest.mark.skipif(not DIST.exists(), reason="no hay build en web/site/dist")


@pytest.mark.parametrize("rel", ["family", "es/family", "ar/family", "hi/family"])
def test_the_form_is_there_before_any_javascript_runs(rel: str) -> None:
    html = (DIST / rel / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<div id="fam-out"([^>]*)>', html)
    assert m, f"{rel}: no está el bloque de «sin cuenta»"
    assert "hidden" not in m.group(1), (
        f"{rel}: la pantalla empieza oculta, o sea en blanco hasta que conteste la API"
    )
    # y el de dentro sí empieza oculto: enseñar «tus hijos» a quien no ha entrado sería peor
    dentro = re.search(r'<div id="fam-in"([^>]*)>', html)
    assert dentro and "hidden" in dentro.group(1)


@pytest.mark.parametrize("rel", ["family", "es/family"])
def test_it_asks_for_an_email_and_a_password(rel: str) -> None:
    html = (DIST / rel / "index.html").read_text(encoding="utf-8")
    assert 'type="email"' in html and 'type="password"' in html
    assert 'minlength="8"' in html, "la contraseña mínima que pide la API son ocho"


def test_a_child_can_be_corrected_without_deleting_them() -> None:
    assert "method: 'PATCH'" in COMPONENTE, (
        "la API sabe corregir un hijo desde el principio y la pantalla no lo usaba: "
        "la única salida era borrarlo, y con él sus medidas"
    )
    assert "form.ficha" in COMPONENTE
    assert "T.edit_child" in COMPONENTE


def test_the_word_for_correcting_exists_in_every_language() -> None:
    i18n = (RAIZ / "web" / "site" / "src" / "i18n.ts").read_text(encoding="utf-8")
    assert i18n.count('"edit_child"') == 8, "falta «corregir» en alguna lengua"
