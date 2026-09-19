"""El calendario deja de ser edades y pasa a ser fechas (19-sep-2026).

Hasta hoy el sitio sabía decir «a los 4 meses toca la segunda de hexavalente». Con la fecha de
nacimiento de cada hijo eso se convierte en **«el 12 de julio de 2024»**, que es lo único que
sirve para apuntarlo en el calendario del teléfono y lo que van a leer los recordatorios de la
app (D-A3 en `APP.md`).

No hay cálculo nuevo ni fuente nueva: es el mismo calendario oficial del país, con la fecha de
nacimiento sumada. Lo que sí hay que cuidar, y es lo que se comprueba aquí:

1. **Lo que ya pasó se marca como pasado, pero no se borra.** Un padre que llega tarde a una
   vacuna necesita verla más que nadie: la lista dice qué queda atrás, no la esconde.
2. **La campaña estacional no tiene fecha.** «Cada otoño» no es un día del año, y ponerle uno
   sería inventárselo. Sale sin fecha y dicho con las palabras de la fuente.
3. **Lo que toca ahora se dice aparte**: en la ventana de tolerancia del propio calendario
   —mes y medio en lactantes, seis meses a partir de los dos años—, que es la que ya usa el
   chat y no otra inventada para esta pantalla.
"""

from __future__ import annotations

import datetime as dt

import pytest

from pedibot.family.vaccines import schedule_for_child


def _hija(nacimiento: str = "2024-03-12", pais: str = "ES") -> dict[str, object]:
    return {"id": 1, "name": "Laura", "birth_date": nacimiento, "sex": "f", "country": pais}


def test_every_slot_gets_a_real_date() -> None:
    hoy = dt.date(2026, 9, 19)
    citas = schedule_for_child(_hija(), lang="es", today=hoy)
    assert citas, "el calendario español tiene citas y esto no devolvió ninguna"
    primera = citas[0]
    assert primera["date"] == "2024-03-12", "la primera cita es el día que nació"
    doce = next(c for c in citas if c["age_months"] == 12)
    assert doce["date"] == "2025-03-12", "doce meses después de nacer, el mismo día"


def test_what_is_past_is_marked_and_not_hidden() -> None:
    """Quien llega tarde a una vacuna es justo quien necesita verla."""
    hoy = dt.date(2026, 9, 19)
    citas = schedule_for_child(_hija(), lang="es", today=hoy)
    pasadas = [c for c in citas if c["state"] == "past"]
    futuras = [c for c in citas if c["state"] == "future"]
    assert pasadas and futuras, "una niña de dos años y medio tiene de las dos"
    assert all(c["date"] <= "2026-09-19" for c in pasadas)
    assert all(c["date"] > "2026-09-19" for c in futuras if c["date"])


def test_the_seasonal_campaign_has_no_date() -> None:
    """«Cada otoño» no es un día del año. Ponerle uno sería inventárselo."""
    hoy = dt.date(2026, 9, 19)
    citas = schedule_for_child(_hija(), lang="es", today=hoy)
    estacionales = [c for c in citas if c["every_year"]]
    if not estacionales:
        pytest.skip("el calendario de este país no tiene campaña estacional")
    assert all(c["date"] is None for c in estacionales)
    assert all(c["state"] == "seasonal" for c in estacionales)


def test_the_one_that_is_due_now_is_said_apart() -> None:
    """Con la tolerancia del propio calendario, no con una inventada para esta pantalla."""
    # una niña de exactamente cuatro meses: le toca la cita de los 4 meses
    hoy = dt.date(2026, 9, 19)
    nacimiento = (hoy - dt.timedelta(days=122)).isoformat()
    citas = schedule_for_child(_hija(nacimiento), lang="es", today=hoy)
    ahora = [c for c in citas if c["state"] == "due"]
    assert ahora, "a los cuatro meses justos algo tiene que tocar"
    assert any(c["age_months"] == 4 for c in ahora)


def test_a_country_we_do_not_have_says_so_instead_of_guessing() -> None:
    assert schedule_for_child(_hija(pais="ZZ"), lang="es") == []
    assert schedule_for_child({**_hija(), "country": None}, lang="es") == []


def test_the_next_appointment_is_the_first_one_ahead() -> None:
    from pedibot.family.vaccines import next_appointment

    hoy = dt.date(2026, 9, 19)
    citas = schedule_for_child(_hija(), lang="es", today=hoy)
    siguiente = next_appointment(citas)
    assert siguiente is not None
    assert siguiente["state"] in ("due", "future")
    futuras = [c["date"] for c in citas if c["state"] == "future"]
    assert siguiente["date"] in (min(futuras), *[c["date"] for c in citas if c["state"] == "due"])


def test_the_dates_come_with_what_the_source_says() -> None:
    """Una fecha sin la fuente detrás no vale: es el calendario de un ministerio, no nuestro."""
    citas = schedule_for_child(_hija(), lang="es", today=dt.date(2026, 9, 19))
    assert all(c["vaccines"] for c in citas)
    assert all(c["label"] for c in citas)


def test_the_api_gives_a_child_their_own_calendar(app_con_familia) -> None:  # noqa: ANN001
    """Y de arriba abajo, que es como lo va a pedir la app para programar los avisos."""
    c = app_con_familia
    c.post(
        "/api/family/register",
        json={"email": "madre@ejemplo.com", "password": "contraseña de prueba", "lang": "es"},
    )
    hijo = c.post(
        "/api/family/children",
        json={"name": "Laura", "birth_date": "2024-03-12", "sex": "f", "country": "ES"},
    ).json()
    r = c.get(f"/api/family/children/{hijo['id']}/vaccines", params={"lang": "es"})
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["country"] == "ES"
    assert len(datos["appointments"]) > 5
    assert datos["appointments"][0]["date"] == "2024-03-12"
    assert datos["next"], "una niña de dos años todavía tiene citas por delante"
    # y de otra familia, nada
    c.post("/api/family/logout")
    c.post(
        "/api/family/register",
        json={"email": "otra@ejemplo.com", "password": "contraseña de prueba"},
    )
    assert c.get(f"/api/family/children/{hijo['id']}/vaccines").status_code == 404
