"""Lo que la página legal promete es lo que el código hace (19-sep-2026).

La cuenta de familia rompió, tal como estaba escrita, la frase con la que este proyecto se
presenta: «Sin cuenta, sin nombre, sin correo. Nunca pedimos datos personales». El operador lo
resolvió él mismo —«será que no hace falta cuenta OBLIGATORIA»— y la página se reescribió en las
ocho lenguas.

Esta prueba existe porque **esa clase de frase se queda vieja sin que nadie lo note**: el código
cambia en un commit y la promesa sigue diciendo lo de antes durante meses, que es exactamente lo
que pasó con este proyecto y su calculadora de dosis. Aquí se atan las dos cosas: cada promesa
concreta de la página legal tiene al lado la línea de código que la cumple, y si una se va, la
otra falla.
"""

from __future__ import annotations

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[1]
I18N = (RAIZ / "web" / "site" / "src" / "i18n.ts").read_text(encoding="utf-8")
TIENDA = (RAIZ / "src" / "pedibot" / "family" / "store.py").read_text(encoding="utf-8")
API = (RAIZ / "src" / "pedibot" / "family" / "api.py").read_text(encoding="utf-8")


def test_the_page_no_longer_says_there_is_no_account() -> None:
    """La frase vieja, tal cual, ya no puede estar en ninguna lengua: hoy hay cuenta y sería
    mentira."""
    viejas = [
        "No account, no name, no e-mail",
        "Sin cuenta, sin nombre, sin correo",
        "Pas de compte, pas de nom",
        "Kein Konto, kein Name",
        "Без аккаунта, без имени",
        "بدون حساب وبدون اسم",
        "Sem conta, sem nome",
        "न खाता, न नाम",
    ]
    quedan = [v for v in viejas if v in I18N]
    assert not quedan, f"la promesa vieja sigue escrita en {len(quedan)} lenguas: {quedan}"


def test_the_page_says_the_account_is_optional_in_every_language() -> None:
    nuevas = [
        "You do not need an account",
        "No hace falta cuenta",
        "Aucun compte n'est nécessaire",
        "Ein Konto ist nicht nötig",
        "Аккаунт не нужен",
        "لا حاجة إلى حساب",
        "Não é preciso conta",
        "खाता ज़रूरी नहीं है",
    ]
    faltan = [n for n in nuevas if n not in I18N]
    assert not faltan, f"sin la frase nueva en {len(faltan)} lenguas: {faltan}"


def test_the_password_promise_is_kept() -> None:
    """La página dice «un hash de tu contraseña (nunca la contraseña)». El código tiene que
    hacer justamente eso."""
    assert "hash de tu contraseña" in I18N or "hash of your password" in I18N
    assert "hashlib.scrypt" in TIENDA, "la promesa dice hash y el código tiene que hacerlo"
    assert not re.search(
        r"INSERT INTO users[^\"']*password[^\"']*\)\s*VALUES[^)]*password\b", TIENDA
    )


def test_the_delete_promise_is_kept() -> None:
    """«Borrar borra: se van con ella los hijos, las medidas y las sesiones.» Eso son las
    claves foráneas en cascada, y el PRAGMA sin el cual SQLite las ignora."""
    assert "borrar la cuenta" in I18N or "delete the account" in I18N
    assert TIENDA.count("ON DELETE CASCADE") >= 3
    assert "PRAGMA foreign_keys = ON" in TIENDA, (
        "sin este PRAGMA la cascada es un comentario y borrar la cuenta dejaría a los hijos"
    )
    assert "/api/family/account" in API


def test_the_download_promise_is_kept() -> None:
    assert "descargarlo todo" in I18N or "download everything" in I18N
    assert "/api/family/export" in API


def test_the_newsletter_promise_is_kept() -> None:
    """«Casilla aparte, apagada salvo que la enciendas, y un enlace para dejarlo en un clic.»"""
    assert "casilla aparte" in I18N or "separate tick box" in I18N
    assert "newsletter INTEGER NOT NULL DEFAULT 0" in TIENDA, "tiene que nacer apagada"
    assert "unsub_token" in TIENDA and "/api/family/unsubscribe" in API


def test_the_separate_database_promise_is_kept() -> None:
    """«Vive en una base de datos separada de la anónima.» Si algún día alguien la junta con la
    de operación, esta prueba es la que lo dice."""
    assert "base de datos separada" in I18N or "database separate" in I18N
    ajustes = (RAIZ / "src" / "pedibot" / "settings.py").read_text(encoding="utf-8")
    assert "family_db_path" in ajustes and "ops_db_path" in ajustes
    assert "pedibot_familias.db" in ajustes and "pedibot_ops.db" in ajustes


def test_the_family_database_is_backed_up_on_the_server() -> None:
    """Perder el historial de peso de un niño porque el respaldo sólo miraba la otra base sería
    de las pocas cosas de este proyecto que no se pueden deshacer."""
    unidad = (RAIZ / "ops" / "systemd" / "pedibot-backup.service").read_text(encoding="utf-8")
    assert "pedibot_familias.db" in unidad
    assert "pedibot_ops.db" in unidad


def test_the_family_database_never_comes_down_to_the_pc() -> None:
    """Y la otra mitad, que es una decisión y no un olvido (19-sep-2026).

    El despliegue se trae una copia de la base de OPERACIÓN al PC del operador, y está bien:
    es anónima —sesiones al azar, IP con sal— y tenerla dos veces la protege de un error. La de
    familias no baja. Tiene el nombre y la fecha de nacimiento de niños de verdad, y cada copia
    en otra máquina es otro sitio del que puede salirse. Vive en el servidor, se respalda ahí y
    quien quiera la suya se la descarga desde su propia página.
    """
    deploy = (RAIZ / "ops" / "deploy.sh").read_text(encoding="utf-8")
    assert "pedibot_ops.db" in deploy, "la de operación sí baja, y esta prueba lo supone"
    assert "pedibot_familias.db" not in deploy, (
        "la base de familias no se copia al PC: son datos de niños de verdad"
    )
