"""«¿Qué vacunas le tocan a Laura?» (19-sep-2026).

Es la frase con la que el operador pidió todo esto: «poder ir apuntando por nombre de hijo… y
tener la edad de cada hijo, para que cuando te pregunten cuáles son las vacunas que le tocan a
Laura, pues que te diga cuáles le tocan sabiendo su edad con su fecha de nacimiento».

Cómo está resuelto, y por qué así: **no se toca nada de lo que ya funciona**. Si quien pregunta
tiene cuenta y en la frase aparece el nombre de uno de sus hijos, a la pregunta se le añade
delante la misma línea de contexto que hoy escribe el desplegable del chat —«Edad: 18 meses.
Peso: 11,2 kg.»—, y de ahí en adelante el triaje, la dosis, el calendario y el percentil hacen
lo de siempre. Una pieza nueva en el borde, no una rama nueva por dentro.

Lo que sí hace falta cuidar, y por eso hay pruebas de las dos cosas:

- **sin cuenta, todo sigue igual**: ni una consulta de más, ni un dato de nadie;
- **el nombre se reconoce como se teclea** (minúsculas, sin tilde) pero **no dentro de otra
  palabra**, que es la avería de «Catar» dentro de «catarro» y ya nos costó un día entero.
"""

from __future__ import annotations

import pytest

from pedibot.family.recognise import child_in_question, context_line, with_child_context

HIJOS = [
    {"id": 1, "name": "Laura", "birth_date": "2024-03-12", "sex": "f", "age_months": 18.0},
    {"id": 2, "name": "Martín", "birth_date": "2019-11-02", "sex": "m", "age_months": 70.0},
]


@pytest.mark.parametrize(
    "pregunta",
    [
        "¿qué vacunas le tocan a Laura?",
        "que vacunas le tocan a laura",
        "LAURA tiene fiebre desde anoche",
        "a Laura le duele el oído",
    ],
)
def test_the_child_is_recognised_as_it_is_typed(pregunta: str) -> None:
    hijo = child_in_question(pregunta, HIJOS)
    assert hijo is not None and hijo["name"] == "Laura"


def test_the_accent_is_not_needed(pregunta: str = "a martin le toca la vacuna?") -> None:
    hijo = child_in_question(pregunta, HIJOS)
    assert hijo is not None and hijo["name"] == "Martín"


@pytest.mark.parametrize(
    "pregunta",
    [
        "mi hijo tiene fiebre",
        "¿qué vacunas tocan a los 18 meses?",
        # el nombre DENTRO de otra palabra no es el nombre. Es la familia de averías de
        # «catar» dentro de «catarro» y de «inde» dentro de «Windeln».
        "le ha salido un sarpullido en la espalda por el laurel",
        "usamos jabón de laurel para el baño",
    ],
)
def test_a_name_inside_another_word_is_not_the_child(pregunta: str) -> None:
    assert child_in_question(pregunta, HIJOS) is None


def test_two_children_named_in_one_question_gives_up() -> None:
    """Si están los dos, no se elige: contestar por la edad equivocada es peor que preguntar."""
    assert child_in_question("Laura y Martín tienen fiebre", HIJOS) is None


def test_the_context_line_says_the_age_in_the_page_language() -> None:
    assert "18" in context_line(HIJOS[0], "es")
    assert context_line(HIJOS[0], "es").lower().startswith("edad")
    assert context_line(HIJOS[0], "en").lower().startswith("age")


def test_the_weight_travels_when_there_is_one() -> None:
    con_peso = {**HIJOS[0], "weight_kg": 11.2}
    linea = context_line(con_peso, "es")
    assert "11,2" in linea or "11.2" in linea


def test_the_question_keeps_its_own_words() -> None:
    """Lo que el padre escribió no se reescribe: se le pone una línea delante."""
    q = "¿qué vacunas le tocan a Laura?"
    salida = with_child_context(q, HIJOS[0], "es")
    assert salida.endswith(q)
    assert "18" in salida


def test_without_an_account_nothing_changes() -> None:
    assert child_in_question("¿qué vacunas le tocan a Laura?", []) is None


def test_the_api_answers_by_the_childs_age(app_con_familia) -> None:  # noqa: ANN001
    """La prueba de arriba abajo, con la API de verdad: se da de alta, se apunta a Laura y se
    pregunta por su nombre. La respuesta tiene que decir CON QUIÉN contestó, porque una edad que
    nadie ve es una edad que nadie puede corregir."""
    cliente = app_con_familia
    cliente.post(
        "/api/family/register",
        json={"email": "madre@ejemplo.com", "password": "contraseña de prueba", "lang": "es"},
    )
    cliente.post(
        "/api/family/children",
        json={"name": "Laura", "birth_date": "2024-03-12", "sex": "f", "country": "ES"},
    )
    r = cliente.post(
        "/api/ask",
        json={"question": "¿qué vacunas le tocan a Laura?", "lang": "es"},
        headers={"x-pedibot-client": "test"},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("child", {}).get("name") == "Laura"
    assert r.json()["child"]["age_months"] > 0


#: Un peso viejo no es un dato viejo inofensivo: es una dosis mal calculada. Un lactante de dos
#: meses gana casi dos kilos en noventa días.
def test_a_stale_weight_is_not_used() -> None:
    import datetime as dt

    from pedibot.family.recognise import fresh_weight

    hoy = dt.date(2025, 9, 19)
    bebe = {"age_months": 4.0}
    nino = {"age_months": 48.0}
    hace_dos_semanas = [{"date": "2025-09-05", "weight_kg": 6.9}]
    hace_dos_meses = [{"date": "2025-07-19", "weight_kg": 6.1}]

    assert fresh_weight(bebe, hace_dos_semanas, hoy) == 6.9
    assert fresh_weight(bebe, hace_dos_meses, hoy) is None, "en un lactante, dos meses es otro niño"
    assert fresh_weight(nino, hace_dos_meses, hoy) == 6.1, "a los cuatro años eso todavía vale"
    assert fresh_weight(bebe, [{"date": "2025-09-05", "height_cm": 62.0}], hoy) is None
    assert fresh_weight(bebe, [], hoy) is None
