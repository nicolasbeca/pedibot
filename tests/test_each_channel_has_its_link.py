"""Cada canal de difusión lleva su enlace, y el panel dice cuánta gente trae cada uno (11-oct-2026).

El operador: «por ahora sólo ha sido bueno CHIFA, lo demás son permisos». Lo sabíamos cruzando
fechas a mano, porque casi todo entra como «directo»: un correo no manda cabecera Referer. Ahora
cada correo, boletín o foro enlaza `https://pedibot.xyz/?r=<canal>` y el registro del servidor,
que ya guarda la dirección entera, dice de qué canal llegó cada persona. Sin cookies, igual que
el resto del panel. Cada persona cuenta una vez, en el primer canal con el que llegó.
"""

from __future__ import annotations

from pedibot.admin import _web_card
from pedibot.ops import report
from tests.test_the_panel_knows_the_web import _persona


def _visitas():
    lineas = []
    lineas += _persona("1.1.1.1", ["/?r=chifa", "/emergency"])
    lineas += _persona("2.2.2.2", ["/es/?r=sevilla-acoge"])
    lineas += _persona("6.6.6.6", ["/?r=chifa"])
    # vuelve otro día por otro enlace: sigue siendo de CHIFA, que es quien la trajo
    lineas += _persona("1.1.1.1", ["/?r=immunize"], ts=1_789_100_000.0)
    lineas += _persona("4.4.4.4", ["/es/dose"])
    # utm_source también vale: algunos boletines lo añaden solos
    lineas += _persona("5.5.5.5", ["/?utm_source=IZ-Express&utm_medium=email"])
    return report.count_visits(lineas)


def test_each_channel_counts_the_people_it_brought() -> None:
    assert _visitas()["web"]["channels"] == {"chifa": 2, "iz-express": 1, "sevilla-acoge": 1}


def test_the_channel_does_not_split_the_page_counts() -> None:
    w = _visitas()
    assert ("/", 4) in w["top"]
    assert all("?" not in uri for uri, _ in w["web"]["entries"])


def test_junk_in_the_link_is_not_a_channel() -> None:
    lineas = _persona("6.6.6.6", ["/?r=<script>alert(1)</script>"])
    lineas += _persona("7.7.7.7", ["/?r=" + "x" * 200])
    assert report.count_visits(lineas)["web"]["channels"] == {}


def test_the_panel_shows_the_channels() -> None:
    html = _web_card(_visitas()["web"])
    assert "Por qué enlace" in html
    assert "chifa" in html
