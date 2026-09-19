"""Las vacunas que vienen, en el calendario del móvil (19-sep-2026).

La app avisará con una notificación local (D-A3). La web no puede: un navegador no programa un
aviso para dentro de cuatro meses. Lo que sí puede, hoy y en cualquier teléfono, es dar el mismo
dato en el formato que todos los calendarios entienden — un `.ics` — y que sea el calendario del
propio móvil el que avise.

Es la respuesta honesta a la diferencia entre las dos: no se promete en la web algo que la web no
hace, se da lo equivalente que sí.

Lo que se comprueba, que es donde esto se rompe:
  - que el fichero sea un calendario de verdad y no un texto con pinta de calendario;
  - que sólo lleve lo que viene (una cita pasada en el calendario de alguien es ruido);
  - que cada cita tenga un identificador estable, o volver a descargarlo duplica todo;
  - que no lleve dentro más de lo que hace falta: el nombre del niño y la vacuna, y ya.
"""

from __future__ import annotations

import re


def _alta(c) -> dict:  # noqa: ANN001
    c.post(
        "/api/family/register",
        json={"email": "madre@ejemplo.com", "password": "contraseña de prueba", "lang": "es"},
    )
    return c.post(
        "/api/family/children",
        json={"name": "Laura", "birth_date": "2024-03-12", "sex": "f", "country": "ES"},
    ).json()


def test_it_is_a_real_calendar(app_con_familia) -> None:  # noqa: ANN001
    c = app_con_familia
    hijo = _alta(c)
    r = c.get(f"/api/family/children/{hijo['id']}/vaccines.ics", params={"lang": "es"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/calendar")
    assert "attachment" in r.headers.get("content-disposition", "")
    ics = r.text
    assert ics.startswith("BEGIN:VCALENDAR")
    assert ics.rstrip().endswith("END:VCALENDAR")
    assert "VERSION:2.0" in ics
    # las líneas de un ics terminan en CRLF; sin eso, la mitad de los calendarios lo rechazan
    assert "\r\n" in ics


def test_only_what_is_ahead_goes_in(app_con_familia) -> None:  # noqa: ANN001
    """Una cita de hace dos años en el calendario de alguien no es un recordatorio, es basura."""
    c = app_con_familia
    hijo = _alta(c)
    ics = c.get(f"/api/family/children/{hijo['id']}/vaccines.ics").text
    fechas = re.findall(r"DTSTART;VALUE=DATE:(\d{8})", ics)
    assert fechas, "no hay ni una cita: para una niña de dos años quedan varias"
    import datetime as dt

    hoy = dt.date.today().strftime("%Y%m%d")
    assert all(f >= hoy for f in fechas), (
        f"hay citas pasadas dentro: {[f for f in fechas if f < hoy]}"
    )


def test_downloading_it_twice_does_not_duplicate_anything(app_con_familia) -> None:  # noqa: ANN001
    """El identificador tiene que salir del hijo y de la fecha, no de un número al azar."""
    c = app_con_familia
    hijo = _alta(c)
    uno = c.get(f"/api/family/children/{hijo['id']}/vaccines.ics").text
    otro = c.get(f"/api/family/children/{hijo['id']}/vaccines.ics").text
    uids = re.findall(r"UID:(\S+)", uno)
    assert uids and uids == re.findall(r"UID:(\S+)", otro)
    assert len(uids) == len(set(uids)), "dos citas con el mismo identificador se pisan"


def test_it_says_who_it_is_for_and_nothing_else(app_con_familia) -> None:  # noqa: ANN001
    c = app_con_familia
    hijo = _alta(c)
    ics = c.get(f"/api/family/children/{hijo['id']}/vaccines.ics", params={"lang": "es"}).text
    assert "Laura" in ics, "sin el nombre, con dos hijos no se sabe de quién es la cita"
    assert "madre@ejemplo.com" not in ics, "el correo no pinta nada en un calendario compartido"
    assert "2024-03-12" not in ics and "20240312" not in ics, (
        "la fecha de nacimiento tampoco: de ella salen las citas, pero no hace falta enseñarla"
    )


def test_another_family_gets_nothing(app_con_familia) -> None:  # noqa: ANN001
    c = app_con_familia
    hijo = _alta(c)
    c.post("/api/family/logout")
    c.post(
        "/api/family/register",
        json={"email": "otra@ejemplo.com", "password": "contraseña de prueba"},
    )
    assert c.get(f"/api/family/children/{hijo['id']}/vaccines.ics").status_code == 404
