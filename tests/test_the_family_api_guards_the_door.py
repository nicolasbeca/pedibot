"""La puerta de la cuenta: quién entra, qué ve y qué se lleva (19-sep-2026).

La tienda ya sabe que cada consulta pide de quién es (`test_a_family_keeps_its_own_data`). Esto
es la otra mitad, la que un navegador toca de verdad: la cookie, el 401 cuando no hay cuenta, y
que la cuenta de una familia **no puede ver ni tocar** la de otra aunque adivine el número del
hijo, que es la clase de fallo que no deja ningún rastro.

Y una que no es de seguridad y es la razón de todo esto: preguntar **«¿qué vacunas le tocan a
Laura?»** teniendo a Laura dada de alta tiene que contestar por su edad, sin que el padre la
escriba. Eso se comprueba en `test_the_chat_knows_who_laura_is`.
"""

from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient

from pedibot.family.store import FamilyStore


@pytest.fixture
def cliente(tmp_path: pathlib.Path) -> TestClient:
    from fastapi import FastAPI

    from pedibot.family.api import family_router

    app = FastAPI()
    app.include_router(family_router(FamilyStore(tmp_path / "familias.db")))
    return TestClient(app)


def _alta(c: TestClient, email: str = "madre@ejemplo.com") -> None:
    r = c.post(
        "/api/family/register",
        json={"email": email, "password": "contraseña de prueba", "lang": "es"},
    )
    assert r.status_code == 200, r.text


def test_without_an_account_there_is_nothing_to_see(cliente: TestClient) -> None:
    assert cliente.get("/api/family/me").status_code == 401
    assert cliente.get("/api/family/children").status_code == 401
    assert (
        cliente.post(
            "/api/family/children", json={"name": "Laura", "birth_date": "2024-03-12"}
        ).status_code
        == 401
    )


def test_registering_leaves_you_inside(cliente: TestClient) -> None:
    _alta(cliente)
    yo = cliente.get("/api/family/me")
    assert yo.status_code == 200
    assert yo.json()["email"] == "madre@ejemplo.com"
    assert yo.json()["children"] == []


def test_the_same_email_twice_is_refused_without_saying_more(cliente: TestClient) -> None:
    _alta(cliente)
    r = cliente.post(
        "/api/family/register", json={"email": "madre@ejemplo.com", "password": "otra contraseña"}
    )
    assert r.status_code == 409


def test_logging_out_closes_the_door(cliente: TestClient) -> None:
    _alta(cliente)
    assert cliente.post("/api/family/logout").status_code == 200
    assert cliente.get("/api/family/me").status_code == 401


def test_a_child_gets_an_age_without_anyone_typing_it(cliente: TestClient) -> None:
    """La fecha de nacimiento no envejece mal; «tiene 14 meses», sí."""
    _alta(cliente)
    r = cliente.post(
        "/api/family/children",
        json={"name": "Laura", "birth_date": "2024-03-12", "sex": "f", "country": "ES"},
    )
    assert r.status_code == 200, r.text
    hijo = r.json()
    assert hijo["name"] == "Laura"
    assert hijo["age_months"] > 0, "la edad se calcula hoy, no se guarda"


def test_another_family_cannot_touch_your_child(
    cliente: TestClient, tmp_path: pathlib.Path
) -> None:
    _alta(cliente, "una@ejemplo.com")
    hijo = cliente.post(
        "/api/family/children", json={"name": "Laura", "birth_date": "2024-03-12"}
    ).json()
    cliente.post("/api/family/logout")
    _alta(cliente, "otra@ejemplo.com")
    assert cliente.get(f"/api/family/children/{hijo['id']}/measurements").status_code == 404
    assert cliente.delete(f"/api/family/children/{hijo['id']}").status_code == 404
    r = cliente.post(
        f"/api/family/children/{hijo['id']}/measurements",
        json={"date": "2025-01-10", "weight_kg": 9.2},
    )
    assert r.status_code == 404, "ni existe ni es suyo: la misma respuesta para las dos cosas"


def test_the_measurements_draw_a_line(cliente: TestClient) -> None:
    _alta(cliente)
    hijo = cliente.post(
        "/api/family/children", json={"name": "Laura", "birth_date": "2024-03-12", "sex": "f"}
    ).json()
    for fecha, kg, cm in (("2024-09-01", 7.4, 67.0), ("2024-06-01", 6.0, 61.5)):
        r = cliente.post(
            f"/api/family/children/{hijo['id']}/measurements",
            json={"date": fecha, "weight_kg": kg, "height_cm": cm},
        )
        assert r.status_code == 200, r.text
    medidas = cliente.get(f"/api/family/children/{hijo['id']}/measurements").json()
    assert [m["date"] for m in medidas] == ["2024-06-01", "2024-09-01"]
    # cada punto trae su edad en meses, que es el eje de la curva, y su percentil
    assert medidas[0]["age_months"] == pytest.approx(2.7, abs=0.2)
    assert 0 < medidas[0]["weight_percentile"] < 100


def test_you_can_take_everything_and_then_leave(cliente: TestClient) -> None:
    _alta(cliente)
    cliente.post("/api/family/children", json={"name": "Laura", "birth_date": "2024-03-12"})
    fuera = cliente.get("/api/family/export")
    assert fuera.status_code == 200
    assert fuera.json()["children"][0]["name"] == "Laura"
    assert "attachment" in fuera.headers.get("content-disposition", "")
    assert cliente.delete("/api/family/account").status_code == 200
    assert cliente.get("/api/family/me").status_code == 401
    # y la contraseña de antes ya no entra en ninguna parte
    assert (
        cliente.post(
            "/api/family/login",
            json={"email": "madre@ejemplo.com", "password": "contraseña de prueba"},
        ).status_code
        == 401
    )


def test_the_newsletter_is_asked_for_apart(cliente: TestClient) -> None:
    _alta(cliente)
    assert cliente.get("/api/family/me").json()["newsletter"] is False
    assert cliente.post("/api/family/newsletter", json={"on": True}).status_code == 200
    assert cliente.get("/api/family/me").json()["newsletter"] is True
    token = cliente.get("/api/family/export").json()["unsubscribe"]
    assert cliente.get(f"/api/family/unsubscribe?t={token}").status_code == 200
    assert cliente.get("/api/family/me").json()["newsletter"] is False


def test_a_wrong_password_does_not_say_whether_the_email_exists(cliente: TestClient) -> None:
    """Contestar «ese correo no existe» es publicar quién está dado de alta."""
    _alta(cliente)
    mala = cliente.post(
        "/api/family/login", json={"email": "madre@ejemplo.com", "password": "la que no es"}
    )
    ninguna = cliente.post(
        "/api/family/login", json={"email": "nadie@ejemplo.com", "password": "la que no es"}
    )
    assert mala.status_code == ninguna.status_code == 401
    assert mala.json() == ninguna.json()


def test_guessing_the_password_gets_slower(tmp_path: pathlib.Path) -> None:
    """Una contraseña se adivina probando, y probar es gratis si nadie lleva la cuenta.

    Diez intentos por cuarto de hora desde la misma conexión no le estorban a quien se equivocó
    dos veces, y le quitan la gracia a quien prueba una lista.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from pedibot.family.api import family_router

    app = FastAPI()
    app.include_router(family_router(FamilyStore(tmp_path / "f.db"), max_attempts=3))
    c = TestClient(app)
    c.post(
        "/api/family/register",
        json={"email": "madre@ejemplo.com", "password": "contraseña de prueba"},
    )
    c.post("/api/family/logout")
    for _ in range(3):
        assert (
            c.post(
                "/api/family/login", json={"email": "madre@ejemplo.com", "password": "no"}
            ).status_code
            == 401
        )
    # el cuarto ya no se comprueba siquiera: se frena antes de mirar la contraseña
    frenado = c.post(
        "/api/family/login",
        json={"email": "madre@ejemplo.com", "password": "contraseña de prueba"},
    )
    assert frenado.status_code == 429


def test_marking_a_dose_takes_it_off_the_pending_list(cliente: TestClient) -> None:
    """La cartilla, por la puerta que toca un navegador (20-sep-2026).

    El caso de uso entero en cinco líneas: un niño de dos años y medio sin nada marcado tiene
    visitas que no constan; se marca una; deja de constar como pendiente y pasa a puesta.
    """
    _alta(cliente)
    hijo = cliente.post(
        "/api/family/children",
        json={"name": "Laura", "birth_date": "2024-03-12", "country": "ES"},
    ).json()

    antes = cliente.get(f"/api/family/children/{hijo['id']}/vaccines?lang=es").json()
    assert antes["pending"], "sin cartilla, a esta edad hay visitas que no constan"
    edad = antes["pending"][0]["age_months"]

    r = cliente.post(
        f"/api/family/children/{hijo['id']}/doses",
        json={"age_months": edad, "given_on": "2024-04-01"},
    )
    assert r.status_code == 204, r.text

    despues = cliente.get(f"/api/family/children/{hijo['id']}/vaccines?lang=es").json()
    assert len(despues["pending"]) == len(antes["pending"]) - 1
    marcada = next(c for c in despues["appointments"] if c["age_months"] == edad)
    assert marcada["state"] == "done"
    assert marcada["given_on"] == "2024-04-01"

    assert cliente.delete(f"/api/family/children/{hijo['id']}/doses/{edad}").status_code == 204
    otra_vez = cliente.get(f"/api/family/children/{hijo['id']}/vaccines?lang=es").json()
    assert len(otra_vez["pending"]) == len(antes["pending"])


def test_another_family_cannot_touch_your_card(cliente: TestClient) -> None:
    """Una cartilla ajena no se lee ni se escribe, ni siquiera adivinando el número del hijo."""
    _alta(cliente, "una@ejemplo.com")
    hijo = cliente.post(
        "/api/family/children",
        json={"name": "Laura", "birth_date": "2024-03-12", "country": "ES"},
    ).json()
    cliente.post(f"/api/family/children/{hijo['id']}/doses", json={"age_months": 2})
    cliente.post("/api/family/logout")

    _alta(cliente, "otra@ejemplo.com")
    assert cliente.get(f"/api/family/children/{hijo['id']}/vaccines").status_code == 404
    assert (
        cliente.post(f"/api/family/children/{hijo['id']}/doses", json={"age_months": 2}).status_code
        == 404
    )
    assert cliente.delete(f"/api/family/children/{hijo['id']}/doses/2").status_code == 404


def test_a_dose_without_an_account_is_refused(cliente: TestClient) -> None:
    """Sin cuenta no hay cartilla que valga: es dato de un niño."""
    assert cliente.post("/api/family/children/1/doses", json={"age_months": 2}).status_code == 401
