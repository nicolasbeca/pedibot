"""Lo que se comparte se puede retirar (23-sep-2026).

El botón «copiar enlace» crea una página pública con la pregunta del padre y la respuesta. Lleva
`noindex` y un identificador aleatorio, así que no sale en buscadores ni se adivina — pero una
vez creada **no había forma de deshacerla**. Un padre que comparte y se arrepiente, o que se da
cuenta de que escribió el nombre de su hija en la pregunta, no tenía a quién acudir.

Quien creó el enlace es el único que puede retirarlo, y se comprueba con la misma sesión que se
exige para crearlo. Retirado, la página deja de existir para todo el mundo.
"""

from __future__ import annotations

from test_api_dose import client  # noqa: F401 — el fixture vive allí


def test_the_one_who_shared_can_take_it_back(client) -> None:  # noqa: ANN001, F811
    j = client.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre"}).json()
    s = client.post(
        "/api/share", json={"answer_id": j["answer_id"], "session": j["session"]}
    ).json()
    assert client.get(s["path"]).status_code == 200

    fuera = client.request(
        "DELETE", f"/api/share/{s['token']}", json={"session": "alguien que pasaba"}
    )
    assert fuera.status_code == 404, "un extraño no puede retirar el enlace de otro"
    assert client.get(s["path"]).status_code == 200

    quitar = client.request("DELETE", f"/api/share/{s['token']}", json={"session": j["session"]})
    assert quitar.status_code == 200, quitar.text
    assert client.get(s["path"]).status_code == 404, "la página sigue viva después de retirarla"


def test_taking_back_something_that_is_not_there(client) -> None:  # noqa: ANN001, F811
    r = client.request("DELETE", "/api/share/nope", json={"session": "x"})
    assert r.status_code == 404


def test_the_answer_itself_survives(client) -> None:  # noqa: ANN001, F811
    """Retirar el enlace quita la página, no la respuesta: el registro de calidad sigue igual."""
    j = client.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre"}).json()
    s = client.post(
        "/api/share", json={"answer_id": j["answer_id"], "session": j["session"]}
    ).json()
    client.request("DELETE", f"/api/share/{s['token']}", json={"session": j["session"]})
    otra = client.post(
        "/api/share", json={"answer_id": j["answer_id"], "session": j["session"]}
    ).json()
    assert otra["token"] != s["token"]
    assert client.get(otra["path"]).status_code == 200


def test_the_button_reads_the_key_the_site_actually_writes(client) -> None:  # noqa: ANN001, F811
    """El botón lee la sesión de `localStorage`, y la web la escribe desde otro fichero.

    Si alguien renombra la clave en el chat, este botón deja de funcionar para todo el mundo y
    nada más se entera: la página seguiría cargando igual, con un botón que siempre dice «esto
    no lo compartiste tú». Las dos puntas se comprueban aquí.
    """
    import pathlib

    j = client.post("/api/ask", json={"question": "mi hijo de 4 años tiene fiebre"}).json()
    s = client.post(
        "/api/share", json={"answer_id": j["answer_id"], "session": j["session"]}
    ).json()
    pagina = client.get(s["path"]).text
    assert "pedibot_session" in pagina

    raiz = pathlib.Path(__file__).resolve().parents[1]
    chat = (raiz / "web" / "site" / "src" / "components" / "Chat.astro").read_text(encoding="utf-8")
    assert "localStorage.setItem('pedibot_session'" in chat, (
        "el chat ya no guarda la sesión con ese nombre: el botón de retirar no encontrará nada"
    )
