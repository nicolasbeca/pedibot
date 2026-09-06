"""El contraste de la paleta, calculado (6-sep-2026).

Esta web se lee con una mano, en un móvil, a las tres de la mañana y con miedo. Nunca se había
comprobado nada de accesibilidad hasta hoy, y al calcularlo salieron tres colores por debajo de
la norma WCAG en el tema claro — el que ve casi todo el mundo, porque el modo noche ya iba de
4.93 para arriba:

    --ink-3   #8A9992   2.93   el texto pequeño de medio sitio, incluida la línea legal del chat
    --coral   #E38C7E   2.48   marca los «esto NO» del botiquín
    --amber   #E7B85C   1.81   pero no se usa como texto en ninguna parte

Los dos primeros se oscurecieron lo justo para pasar de 4.5 conservando el tono: es el mismo
color, más oscuro. El ámbar se dejó igual — cambiar un color que solo se usa de fondo y de borde
habría sido tocar el diseño sin arreglar nada, y este fichero comprueba lo que se usa como texto,
no la paleta entera.

Se calcula aquí en vez de confiar en que alguien lo mire: un token se retoca en un momento de
prisa y nadie vuelve a hacer la cuenta.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSS = (ROOT / "web" / "site" / "src" / "styles" / "global.css").read_text(encoding="utf-8")

#: WCAG AA: 4.5 para texto normal. Todos estos son texto de 12-15 px, así que no vale el 3.0 de
#: «texto grande».
MINIMO = 4.5


def _tokens(bloque: str) -> dict[str, str]:
    return dict(re.findall(r"(--[\w-]+):\s*(#[0-9A-Fa-f]{3,6})", bloque))


def _luminancia(color: str) -> float:
    h = color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    canales = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255
        canales.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]


def contraste(a: str, b: str) -> float:
    la, lb = _luminancia(a), _luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


CLARO = _tokens(CSS[: CSS.index(":root.night")])
NOCHE = _tokens(CSS[CSS.index(":root.night") : CSS.index("}", CSS.index(":root.night"))])

#: (qué es, color del texto, color del fondo). Solo pares que existen de verdad en la web.
PARES = [
    ("texto principal sobre el fondo", "--ink", "--ground"),
    ("texto principal sobre una tarjeta", "--ink", "--paper"),
    ("texto secundario", "--ink-2", "--ground"),
    ("texto pequeño (línea legal del chat, pies)", "--ink-3", "--ground"),
    ("texto pequeño sobre una tarjeta", "--ink-3", "--paper"),
    ("enlaces y verde de marca", "--sage", "--ground"),
    ("verde sobre una tarjeta", "--sage", "--paper"),
    ("los «esto NO» del botiquín", "--coral", "--ground"),
    ("texto del botón principal", "--paper", "--sage"),
    ("texto sobre el fondo menta", "--ink", "--mint"),
    ("texto sobre el fondo coral", "--ink", "--coral-soft"),
]


@pytest.mark.parametrize(("que", "texto", "fondo"), PARES)
def test_light_theme_contrast(que: str, texto: str, fondo: str) -> None:
    assert texto in CLARO and fondo in CLARO, f"faltan tokens para «{que}»"
    r = contraste(CLARO[texto], CLARO[fondo])
    assert r >= MINIMO, (
        f"{que}: {r:.2f}, por debajo de {MINIMO} ({CLARO[texto]} sobre {CLARO[fondo]})"
    )


@pytest.mark.parametrize(("que", "texto", "fondo"), PARES)
def test_night_theme_contrast(que: str, texto: str, fondo: str) -> None:
    """El modo noche ya cumplía antes de tocarlo. Se comprueba para que siga cumpliendo."""
    if texto not in NOCHE or fondo not in NOCHE:
        pytest.skip(f"el modo noche no redefine {texto} o {fondo}")
    r = contraste(NOCHE[texto], NOCHE[fondo])
    assert r >= MINIMO, (
        f"{que} (noche): {r:.2f}, por debajo de {MINIMO} ({NOCHE[texto]} sobre {NOCHE[fondo]})"
    )


def test_the_alarm_announces_itself_to_a_screen_reader() -> None:
    """La alarma roja es lo único de esta página que no puede pasar desapercibido, y hasta hoy
    llegaba en silencio para quien usa un lector de pantalla: el texto aparecía en el DOM y nada
    lo anunciaba. `role="alert"` interrumpe la lectura, que es exactamente lo que debe hacer."""
    chat = (ROOT / "web" / "site" / "src" / "components" / "Chat.astro").read_text(encoding="utf-8")
    banners = re.findall(r'<div class="banner \$\{j\.level\}"([^>]*)>', chat)
    assert banners, "no encuentro ninguna alarma en el chat"
    sin_rol = [b for b in banners if 'role="alert"' not in b]
    assert not sin_rol, f"{len(sin_rol)} alarmas no se anuncian como alarma"


def test_the_answer_is_announced_when_it_arrives() -> None:
    chat = (ROOT / "web" / "site" / "src" / "components" / "Chat.astro").read_text(encoding="utf-8")
    m = re.search(r'<div class="chat" id="thread"([^>]*)>', chat)
    assert m, "no encuentro el hilo de la conversación"
    assert "aria-live" in m.group(1), "la respuesta llega sin anunciarse"
