"""Cada promesa de /legal, atada a lo que hace el código (6/7-sep-2026).

La página de privacidad hace seis promesas concretas sobre lo que la web guarda y lo que no.
Nadie las había comparado nunca con lo que ejecuta el servidor. Al hacerlo, **tres no se
cumplían**:

  · «hash con sal» — la sal era la constante «pedibot», escrita en un repositorio público, porque
    el parámetro no se pasaba desde ninguno de los tres sitios que construyen el almacén.
  · «la memoria dura 24 horas» — `history()` solo LEÍA 24 horas; las filas no se borraban nunca.
  · «sin rastreadores de terceros» — cada carga pedía el CSS a fonts.googleapis.com.

Este fichero existe para que no vuelva a pasar, y sobre todo para lo contrario de lo que parece:
**si alguien cambia el texto de la promesa, el test falla y le obliga a mirar el código.** Una
promesa y su comprobación tienen que moverse juntas o no sirven de nada.

Las que ya tienen candado en otro sitio se citan aquí para que se vea el mapa completo:
  · la sal y las 24 horas → tests/test_who_asked.py
  · ningún recurso de terceros → tests/test_internal_links.py
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
I18N = (ROOT / "web" / "site" / "src" / "i18n.ts").read_text(encoding="utf-8")

#: Trozo de la promesa, en español, tal y como está publicada. Si cambia, este fichero falla.
PROMESAS = {
    "sin_datos": "Nunca pedimos datos personales",
    "anonimo": "un identificador de sesión aleatorio, sin dirección IP",
    "memoria_24h": "La memoria de conversación dura 24 horas",
    "hash_con_sal": "hash con sal",
    "navegador": "el identificador de sesión, el país elegido y el modo noche",
    "sin_rastreadores": "Sin rastreadores publicitarios",
    "compartidas": "solo contienen la pregunta y la respuesta",
    "telegram_stop": "para no recibir ninguno; puedes seguir preguntando",
}


def test_the_promises_still_say_what_these_tests_check() -> None:
    """El eslabón que mantiene honesto a todo lo demás. Si alguien reescribe una promesa, esta
    prueba cae y le obliga a comprobar que el código sigue haciendo lo que ahora dice."""
    m = re.search(r"\n  es: \{.*?legal_priv: \[(.*?)\],\n", I18N, re.S)
    assert m, "no encuentro la lista de privacidad en español"
    texto = m.group(1)
    faltan = [k for k, frase in PROMESAS.items() if frase not in texto and frase not in I18N]
    assert not faltan, (
        "la página legal ya no dice esto, así que su comprobación puede estar midiendo otra cosa: "
        + ", ".join(faltan)
    )


def test_the_answers_table_has_no_column_for_an_ip() -> None:
    """«un identificador de sesión aleatorio, sin dirección IP». La forma más segura de no
    guardar una IP es no tener dónde ponerla."""
    store = (ROOT / "src" / "pedibot" / "ops" / "store.py").read_text(encoding="utf-8")
    crear = store[store.index("CREATE TABLE IF NOT EXISTS answers") :]
    crear = crear[: crear.index(");")]
    sospechosas = [
        ln.strip() for ln in crear.splitlines() if re.search(r"\bip\b|address|remote", ln, re.I)
    ]
    assert not sospechosas, f"la tabla de respuestas tiene columnas de dirección: {sospechosas}"


def test_the_browser_keeps_only_the_three_things_the_page_names() -> None:
    """«el identificador de sesión, el país elegido y el modo noche». Ni una clave más: cada una
    que se añada sin tocar el texto convierte la frase en mentira."""
    escritas: set[str] = set()
    leidas: set[str] = set()
    for f in (ROOT / "web" / "site" / "src").rglob("*.astro"):
        texto = f.read_text(encoding="utf-8")
        escritas.update(re.findall(r"localStorage\.setItem\(\s*['\"]([^'\"]+)", texto))
        leidas.update(re.findall(r"localStorage\.getItem\(\s*['\"]([^'\"]+)", texto))
    assert escritas == {"pedibot_session", "pedibot_country", "pedibot_theme"}, (
        f"el sitio guarda {sorted(escritas)} en el navegador, y la página nombra tres cosas"
    )
    # 13-sep-2026: el sitio LEE además una marca que sólo escribe el panel con contraseña, para
    # que el operador no salga como lector. En el navegador de un lector no existe nunca, así que
    # la frase sigue siendo verdad para él; lo que no puede pasar es que la escriba el sitio.
    panel = (ROOT / "src" / "pedibot" / "admin.py").read_text(encoding="utf-8")
    for clave in leidas - escritas:
        assert f"localStorage.setItem('{clave}'" in panel, (
            f"el sitio lee «{clave}» y no la escribe el panel: ¿quién la guarda en el navegador?"
        )


def test_a_shared_answer_carries_nothing_but_the_question_and_the_answer() -> None:
    """«páginas públicas que solo contienen la pregunta y la respuesta». Comprobado también contra
    la web real el 7-sep: ni sesión, ni IP, ni país, ni identificadores, y con noindex."""
    api = (ROOT / "src" / "pedibot" / "api.py").read_text(encoding="utf-8")
    i = api.index("def shared_answer(")
    cuerpo = api[i : api.index("\n    @app.", i + 10)]
    assert "noindex" in cuerpo, "una respuesta compartida debería pedir que no se indexe"
    for prohibido in ("session", "ip_hash", "country", "answer_id"):
        assert f'd["{prohibido}"]' not in cuerpo and f"d['{prohibido}']" not in cuerpo, (
            f"la página compartida usa {prohibido}, y la promesa dice que solo lleva dos cosas"
        )


def test_stop_really_stops_the_notices_and_nothing_else() -> None:
    """«Escribe /stop para no recibir ninguno; puedes seguir preguntando». Las dos mitades: que
    la baja se guarde y la respete quien envía, y que no bloquee las preguntas."""
    bot = (ROOT / "src" / "pedibot" / "telegram_bot.py").read_text(encoding="utf-8")
    store = (ROOT / "src" / "pedibot" / "ops" / "store.py").read_text(encoding="utf-8")

    assert 'cmd == "/stop"' in bot, "el bot no atiende /stop"
    i = bot.index('cmd == "/stop"')
    assert "set_tg_opt_out(chat_id, True)" in bot[i : i + 300], "/stop no da de baja"
    assert '"stop"' in bot, "/stop no está registrado como comando"

    # quien envía avisos tiene que filtrar por la baja
    assert "opted_out=0" in store, "la lista de destinatarios no filtra a quien se dio de baja"

    # y las preguntas siguen: nada consulta opted_out para decidir si responder
    responder = bot[bot.index("def handle_message(") :]
    assert "opted_out" not in responder, "la baja de avisos está bloqueando también las respuestas"
