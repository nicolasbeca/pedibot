"""La cuenta de familia: qué guarda, de quién es y cómo se borra (19-sep-2026).

Pedido por el operador: «quiero que puedas darte de alta tanto en web como en app para guardar
datos de tus hijos… y que cuando preguntes cuáles son las vacunas que le tocan a Laura, te diga
cuáles le tocan sabiendo su fecha de nacimiento». Decidido por él también el cómo: **correo y
contraseña**, y la cuenta **opcional** — quien no la quiera sigue usando el sitio entero.

Tres decisiones de diseño que se comprueban aquí porque son las que no se pueden romper después:

1. **Base de datos aparte.** `pedibot_ops.db` abre su fichero diciendo «no personal data», y es
   verdad: sesiones aleatorias e IP con sal. Esto es lo contrario —el nombre de un niño, su fecha
   de nacimiento y su peso— y vive en `pedibot_familias.db`, con su propio respaldo, su propia
   retención y su propio borrado. Mezclarlas sería perder la frase que hace honesta a la otra.
2. **La contraseña no se guarda.** Se guarda un `scrypt` con sal propia, de la biblioteca estándar
   (nada de dependencias nuevas para algo así), y dos cuentas con la misma contraseña tienen
   hashes distintos.
3. **Cada familia ve la suya.** Todas las consultas piden el `user_id`; no hay ninguna que
   devuelva un hijo sin decir de quién es. Es la clase de fallo que no da ningún error.
"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest

from pedibot.family.store import FamilyStore


@pytest.fixture
def tienda(tmp_path: pathlib.Path) -> FamilyStore:
    return FamilyStore(tmp_path / "familias.db")


def test_the_password_is_never_stored(tienda: FamilyStore) -> None:
    tienda.register("Madre@Ejemplo.com ", "una contraseña larga", lang="es")
    fila = sqlite3.connect(tienda.path).execute("SELECT email, password_hash FROM users").fetchone()
    assert fila[0] == "madre@ejemplo.com", "el correo se guarda en minúsculas y sin espacios"
    assert "una contraseña larga" not in fila[1]
    assert fila[1].startswith("scrypt$")


def test_two_accounts_with_the_same_password_do_not_look_alike(tienda: FamilyStore) -> None:
    """Sin sal propia, una filtración de la base enseñaría quién comparte contraseña con quién."""
    tienda.register("a@ejemplo.com", "la misma de siempre")
    tienda.register("b@ejemplo.com", "la misma de siempre")
    hashes = [f[0] for f in sqlite3.connect(tienda.path).execute("SELECT password_hash FROM users")]
    assert hashes[0] != hashes[1]


def test_the_same_email_cannot_register_twice(tienda: FamilyStore) -> None:
    assert tienda.register("madre@ejemplo.com", "contraseña de prueba")
    assert tienda.register("MADRE@ejemplo.com", "otra contraseña") is None


def test_a_short_password_is_refused(tienda: FamilyStore) -> None:
    with pytest.raises(ValueError):
        tienda.register("madre@ejemplo.com", "corta")


def test_logging_in_needs_the_right_password(tienda: FamilyStore) -> None:
    tienda.register("madre@ejemplo.com", "contraseña de prueba")
    assert tienda.login("madre@ejemplo.com", "contraseña de prueba")
    assert tienda.login("madre@ejemplo.com", "contraseña equivocada") is None
    assert tienda.login("nadie@ejemplo.com", "contraseña de prueba") is None


def test_the_session_token_is_not_stored_as_it_travels(tienda: FamilyStore) -> None:
    """Lo que viaja en la cookie no está en la base: está su huella. Quien lea la base no puede
    hacerse pasar por nadie."""
    tienda.register("madre@ejemplo.com", "contraseña de prueba")
    token = tienda.login("madre@ejemplo.com", "contraseña de prueba")
    assert token
    guardado = sqlite3.connect(tienda.path).execute("SELECT token_hash FROM sessions").fetchone()[0]
    assert token not in guardado
    assert tienda.user_for(token)
    tienda.logout(token)
    assert tienda.user_for(token) is None


def test_a_child_belongs_to_one_family_only(tienda: FamilyStore) -> None:
    """El fallo que no da ningún error: una consulta que devuelve un hijo sin mirar de quién es."""
    una = tienda.register("una@ejemplo.com", "contraseña de prueba")
    otra = tienda.register("otra@ejemplo.com", "contraseña de prueba")
    assert una and otra
    laura = tienda.add_child(una, name="Laura", birth_date="2024-03-12", sex="f", country="ES")
    assert tienda.children(una) and not tienda.children(otra)
    assert tienda.child(otra, laura) is None, "una familia no puede leer al hijo de otra"
    assert tienda.delete_child(otra, laura) is False
    assert tienda.child(una, laura)


def test_a_child_is_found_by_name_as_it_is_typed(tienda: FamilyStore) -> None:
    """«las vacunas que le tocan a laura» se escribe en minúscula y sin tilde, y es la pregunta
    que motivó todo esto."""
    u = tienda.register("madre@ejemplo.com", "contraseña de prueba")
    assert u
    tienda.add_child(u, name="Laura", birth_date="2024-03-12")
    tienda.add_child(u, name="Martín", birth_date="2019-11-02")
    assert tienda.child_by_name(u, "laura")
    assert tienda.child_by_name(u, "LAURA")
    assert tienda.child_by_name(u, "martin"), "sin tilde, que es como se teclea deprisa"
    assert tienda.child_by_name(u, "pedro") is None


def test_the_measurements_come_back_in_order(tienda: FamilyStore) -> None:
    u = tienda.register("madre@ejemplo.com", "contraseña de prueba")
    assert u
    c = tienda.add_child(u, name="Laura", birth_date="2024-03-12")
    tienda.add_measurement(u, c, date="2025-01-10", weight_kg=9.2, height_cm=74.0)
    tienda.add_measurement(u, c, date="2024-06-01", weight_kg=6.8, height_cm=64.5)
    fechas = [m["date"] for m in tienda.measurements(u, c)]
    assert fechas == ["2024-06-01", "2025-01-10"], "una curva se lee de izquierda a derecha"


def test_a_measurement_of_someone_elses_child_is_refused(tienda: FamilyStore) -> None:
    una = tienda.register("una@ejemplo.com", "contraseña de prueba")
    otra = tienda.register("otra@ejemplo.com", "contraseña de prueba")
    assert una and otra
    c = tienda.add_child(una, name="Laura", birth_date="2024-03-12")
    assert tienda.add_measurement(otra, c, date="2025-01-10", weight_kg=9.2) is None
    assert tienda.measurements(otra, c) == []


def test_deleting_the_account_leaves_nothing_behind(tienda: FamilyStore) -> None:
    """Borrar tiene que borrar. Es lo que la ley pide y es lo que uno espera."""
    u = tienda.register("madre@ejemplo.com", "contraseña de prueba")
    assert u
    c = tienda.add_child(u, name="Laura", birth_date="2024-03-12")
    tienda.add_measurement(u, c, date="2025-01-10", weight_kg=9.2)
    token = tienda.login("madre@ejemplo.com", "contraseña de prueba")
    tienda.delete_account(u)
    con = sqlite3.connect(tienda.path)
    for tabla in ("users", "children", "measurements", "sessions"):
        assert con.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0] == 0, tabla
    assert tienda.user_for(token or "") is None


def test_everything_can_be_taken_away(tienda: FamilyStore) -> None:
    """Y antes de borrar, poder llevárselo: el mismo derecho, la otra mitad."""
    u = tienda.register("madre@ejemplo.com", "contraseña de prueba", lang="es")
    assert u
    c = tienda.add_child(u, name="Laura", birth_date="2024-03-12", sex="f", country="ES")
    tienda.add_measurement(u, c, date="2025-01-10", weight_kg=9.2, height_cm=74.0)
    fuera = tienda.export(u)
    assert fuera["email"] == "madre@ejemplo.com"
    assert "password_hash" not in str(fuera), "lo exportado es suyo, no nuestro"
    assert fuera["children"][0]["name"] == "Laura"
    assert fuera["children"][0]["measurements"][0]["weight_kg"] == 9.2


def test_the_newsletter_is_off_unless_it_is_asked_for(tienda: FamilyStore) -> None:
    """Un boletín no se regala con el alta: se pide aparte y se puede dejar de un clic."""
    u = tienda.register("madre@ejemplo.com", "contraseña de prueba")
    assert u
    assert tienda.export(u)["newsletter"] is False
    assert tienda.newsletter_audience() == []
    tienda.set_newsletter(u, True)
    assert [d["email"] for d in tienda.newsletter_audience()] == ["madre@ejemplo.com"]
    baja = tienda.export(u)["unsubscribe"]
    assert tienda.unsubscribe(baja) is True
    assert tienda.newsletter_audience() == []
    assert tienda.unsubscribe("un-token-inventado") is False


def test_the_family_database_is_not_the_ops_database() -> None:
    """La otra base abre su fichero prometiendo que no guarda datos personales, y lo cumple.
    Esto es lo contrario, así que vive aparte: otro fichero, otro respaldo, otro borrado."""
    from pedibot import settings

    familia = pathlib.Path(settings.get_settings().family_db_path)
    ops = pathlib.Path(settings.get_settings().ops_db_path)
    assert familia != ops
    ops_src = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "pedibot" / "ops" / "store.py"
    ).read_text(encoding="utf-8")
    assert "No personal data" in ops_src, (
        "si la de operación deja de prometerlo, esta separación pierde su motivo y hay que "
        "volver a pensarla"
    )
