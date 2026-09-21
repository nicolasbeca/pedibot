"""El panel avisa cuando toca montar el proveedor de correo (21-sep-2026).

El operador: el correo (recuperar la contraseña, el boletín) espera «a tener 20 altas por lo
menos». Y el mismo día: «elimina los informes a Telegram, tengo el panel para entrar cuando
quiera». Así que el aviso vive en la casilla de cuentas del panel, y en ningún otro sitio.
"""

from __future__ import annotations

from pedibot.admin import ACCOUNTS_FOR_EMAIL, family_kpis


def _c(n: int) -> dict[str, int]:
    return {"accounts": n, "children": 0, "measurements": 0, "newsletter": 0}


def test_the_threshold_is_the_operators_twenty() -> None:
    assert ACCOUNTS_FOR_EMAIL == 20


def test_below_twenty_the_box_is_quiet() -> None:
    h = family_kpis(_c(19))
    assert 'class="k warn"' not in h
    assert "correo" not in h


def test_at_twenty_the_box_turns_and_says_why() -> None:
    h = family_kpis(_c(20))
    assert '<div class="k warn"><b>20</b>' in h
    assert "toca montar el correo" in h
