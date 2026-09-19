"""El panel dice cuántas cuentas hay, y nada más de ellas (19-sep-2026).

Pedido por el operador el mismo día que se abrió el registro: «en el panel debe aparecer cuántas
cuentas se han creado». Es la cifra que dice si esto le sirve a alguien.

Y con ella, la línea que no se cruza: **el panel enseña números, nunca personas**. Ni un correo,
ni el nombre de un niño, ni una fecha de nacimiento. El panel se abre desde un navegador con una
contraseña básica y se mira en sitios donde alguien puede estar mirando por encima del hombro;
las cuentas viven en otra base de datos precisamente para que su contenido no ande suelto por
ahí. Contar no es enseñar.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from pedibot.family.store import FamilyStore


@pytest.fixture
def tienda(tmp_path: pathlib.Path) -> FamilyStore:
    t = FamilyStore(tmp_path / "familias.db")
    uno = t.register("madre@ejemplo.com", "contraseña de prueba", lang="es")
    otro = t.register("padre@ejemplo.com", "contraseña de prueba", lang="en")
    assert uno and otro
    laura = t.add_child(uno, name="Laura", birth_date="2024-03-12", sex="f", country="ES")
    t.add_child(otro, name="Martín", birth_date="2019-11-02", sex="m", country="ES")
    t.add_measurement(uno, laura, date="2025-01-10", weight_kg=9.2, height_cm=74.0)
    t.set_newsletter(uno, True)
    return t


def test_the_store_can_count_itself(tienda: FamilyStore) -> None:
    c = tienda.counts()
    assert c["accounts"] == 2
    assert c["children"] == 2
    assert c["measurements"] == 1
    assert c["newsletter"] == 1


def test_counting_an_empty_or_missing_database_is_zero(tmp_path: pathlib.Path) -> None:
    """El panel se abre el primer día, cuando todavía no hay ni base: eso son ceros, no un error."""
    from pedibot.admin import family_counts

    assert family_counts(tmp_path / "no-existe.db") == {
        "accounts": 0,
        "children": 0,
        "measurements": 0,
        "newsletter": 0,
    }
    vacia = FamilyStore(tmp_path / "vacia.db")
    assert family_counts(vacia.path)["accounts"] == 0


def test_the_panel_shows_the_numbers(tienda: FamilyStore) -> None:
    from pedibot.admin import family_counts, family_kpis

    html = family_kpis(family_counts(tienda.path))
    assert "cuentas" in html
    assert ">2<" in html, "no aparece el número de cuentas"
    assert "hijos" in html


def test_the_panel_never_shows_who(tienda: FamilyStore) -> None:
    """La línea que no se cruza: números sí, personas no."""
    from pedibot.admin import family_counts, family_kpis

    html = family_kpis(family_counts(tienda.path))
    for prohibido in ("madre@ejemplo.com", "padre@ejemplo.com", "Laura", "Martín", "2024-03-12"):
        assert prohibido not in html, f"el panel está enseñando «{prohibido}»"


def test_the_counter_does_not_read_more_than_it_needs() -> None:
    """Una lectura de más hoy es una filtración mañana: lo que consulta el panel son COUNT(*),
    y eso se comprueba leyendo el código, que es donde se cambia sin querer."""
    fuente = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "pedibot" / "admin.py"
    ).read_text(encoding="utf-8")
    trozo = fuente[fuente.index("def family_counts") : fuente.index("def family_kpis")]
    consultas = re.findall(r"SELECT[^\"']*", trozo)
    assert consultas, "family_counts no consulta nada"
    for c in consultas:
        assert "count(*)" in c.lower(), f"el panel lee más de lo que necesita: «{c.strip()}»"
