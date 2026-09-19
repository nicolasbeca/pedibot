"""La cartilla de vacunación, que es la que no se moja (20-sep-2026).

El sitio ya sabía decir «el 12 de julio le tocaba la segunda de hexavalente». Lo que no sabía es
si se puso, y esa es la pregunta de la casa a la que este proyecto va: donde la cartilla es un
papel que se pierde, la madre no necesita saber qué tocaba, necesita saber qué falta.

Lo que se prueba aquí, en orden de lo que rompería más si fallara:

1. que marcar una visita la saca de «pendiente», porque si no, la lista de lo que falta no
   adelgaza nunca y el padre deja de mirarla;
2. que se identifica por la EDAD y no por el nombre de la vacuna, porque el ministerio cambia de
   producto y el nombre cambia con él;
3. que «marcada sin acordarme del día» no es lo mismo que «sin marcar», que son dos `None` que
   se parecen mucho;
4. que la cartilla de un niño no se ve desde otra cuenta.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from pedibot.family.store import FamilyStore
from pedibot.family.vaccines import pending, schedule_for_child

NACIMIENTO = "2024-03-12"
HOY = dt.date(2026, 9, 20)


@pytest.fixture
def tienda(tmp_path: Path) -> FamilyStore:
    return FamilyStore(tmp_path / "familias.db")


@pytest.fixture
def hija(tienda: FamilyStore) -> tuple[int, int]:
    uid = tienda.register("madre@example.com", "una contraseña larga")
    assert uid
    cid = tienda.add_child(uid, name="Laura", birth_date=NACIMIENTO, country="ES")
    assert cid
    return uid, cid


def _citas(tienda: FamilyStore, uid: int, cid: int) -> list[dict]:
    hijo = tienda.child(uid, cid)
    assert hijo
    return schedule_for_child(hijo, lang="es", today=HOY, given=tienda.doses(uid, cid))


def test_marcar_una_visita_la_saca_de_lo_pendiente(tienda: FamilyStore, hija) -> None:
    uid, cid = hija
    antes = pending(_citas(tienda, uid, cid))
    assert antes, "una niña de dos años y medio sin cartilla tiene visitas sin constar"

    primera = antes[0]
    assert tienda.mark_dose(uid, cid, primera["age_months"], "2024-03-13")

    despues = _citas(tienda, uid, cid)
    marcada = next(c for c in despues if c["age_months"] == primera["age_months"])
    assert marcada["state"] == "done"
    assert marcada["given_on"] == "2024-03-13"
    assert len(pending(despues)) == len(antes) - 1


def test_lo_marcado_gana_incluso_a_lo_que_toca_ahora(tienda: FamilyStore, hija) -> None:
    """Si el padre dice que ya se puso, el sitio no está para discutírselo.

    La fecha está elegida —cuatro meses justos— para que caiga una visita dentro de la
    tolerancia. Con un `skip` cuando no la había, esta prueba se saltaba siempre sin que nadie
    se enterara, que es la forma más silenciosa de no probar nada.
    """
    uid, cid = hija
    hijo = tienda.child(uid, cid)
    assert hijo
    a_los_cuatro_meses = dt.date(2024, 7, 12)
    citas = schedule_for_child(hijo, lang="es", today=a_los_cuatro_meses)
    tocan = [c for c in citas if c["state"] == "due"]
    assert tocan, "a los cuatro meses el calendario español tiene visita"

    tienda.mark_dose(uid, cid, tocan[0]["age_months"])
    despues = schedule_for_child(
        hijo, lang="es", today=a_los_cuatro_meses, given=tienda.doses(uid, cid)
    )
    ahora = next(c for c in despues if c["age_months"] == tocan[0]["age_months"])
    assert ahora["state"] == "done"


def test_marcada_sin_fecha_no_es_lo_mismo_que_sin_marcar(tienda: FamilyStore, hija) -> None:
    """Los dos son `None` y significan cosas opuestas. Confundirlos borra la cartilla entera."""
    uid, cid = hija
    edad = pending(_citas(tienda, uid, cid))[0]["age_months"]
    tienda.mark_dose(uid, cid, edad)  # sin acordarse del día

    cita = next(c for c in _citas(tienda, uid, cid) if c["age_months"] == edad)
    assert cita["state"] == "done"
    assert cita["given_on"] is None
    assert tienda.doses(uid, cid)[edad] is None


def test_desmarcar_devuelve_la_visita_a_pendiente(tienda: FamilyStore, hija) -> None:
    uid, cid = hija
    edad = pending(_citas(tienda, uid, cid))[0]["age_months"]
    tienda.mark_dose(uid, cid, edad)
    assert tienda.unmark_dose(uid, cid, edad)
    cita = next(c for c in _citas(tienda, uid, cid) if c["age_months"] == edad)
    assert cita["state"] == "pending"


def test_marcar_dos_veces_solo_cambia_la_fecha(tienda: FamilyStore, hija) -> None:
    uid, cid = hija
    edad = pending(_citas(tienda, uid, cid))[0]["age_months"]
    tienda.mark_dose(uid, cid, edad, "2024-04-01")
    tienda.mark_dose(uid, cid, edad, "2024-04-08")
    assert tienda.doses(uid, cid) == {edad: "2024-04-08"}


def test_la_cartilla_no_se_ve_desde_otra_cuenta(tienda: FamilyStore, hija) -> None:
    uid, cid = hija
    tienda.mark_dose(uid, cid, pending(_citas(tienda, uid, cid))[0]["age_months"])

    otro = tienda.register("otra@example.com", "otra contraseña larga")
    assert otro
    assert tienda.doses(otro, cid) == {}
    assert tienda.mark_dose(otro, cid, 2) is False
    assert tienda.unmark_dose(otro, cid, 2) is False


def test_lo_pendiente_sale_de_lo_mas_viejo_a_lo_mas_nuevo(tienda: FamilyStore, hija) -> None:
    """Un niño que se saltó cuatro visitas empieza por la primera, no por la última."""
    uid, cid = hija
    edades = [c["age_months"] for c in pending(_citas(tienda, uid, cid))]
    assert edades == sorted(edades)


def test_borrar_el_hijo_se_lleva_su_cartilla(tienda: FamilyStore, hija) -> None:
    """La cascada del `PRAGMA foreign_keys`: si no, quedan filas huérfanas de un niño borrado."""
    uid, cid = hija
    tienda.mark_dose(uid, cid, 2)
    assert tienda.delete_child(uid, cid)
    with tienda._con() as con:
        assert (
            con.execute("SELECT COUNT(*) FROM doses WHERE child_id = ?", (cid,)).fetchone()[0] == 0
        )
