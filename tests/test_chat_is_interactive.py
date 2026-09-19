"""Lo que el chat ofrece con un toque tiene que funcionar con un toque (12-sep-2026).

Leído `Chat.astro` línea a línea buscando dónde añadir interactividad, y antes de añadir nada
salieron tres cosas rotas:

1. **Las respuestas rápidas nunca han funcionado.** Se pintan con `class="fb opt"` y el
   manejador de clics del hilo sólo distingue share / child / listen; cualquier otro `.fb` cae
   al voto, que manda `answer_id=NaN` y desactiva los botones con un «✓». El padre toca «¿fiebre
   o tos?» y lo que pasa es que se le agradece un voto que no ha dado.
2. **En un 503 el padre ve la palabra «undefined».** El cliente pinta `S.err_unavailable`, la
   cadena existe en las ocho lenguas, y no viajaba en `data-strings`.
3. Ídem `S.err_busy` en el 429 de la segunda ruta (la foto).

Y dos mejoras que se miden: cuando el bot pide la edad —**6 % de las respuestas**— botones con
las edades en vez de teclear (el servidor recuerda la pregunta: comprobado en las ocho lenguas);
y con nivel emergencia y país conocido, **un botón `tel:`**, porque con el niño en brazos marcar
tiene que ser un toque. Sólo con país conocido: la frase de respaldo dice «112 en la UE, 911 en
América», y sacarle un número sería marcar el equivocado.
"""

from __future__ import annotations

import re

import pytest

from pedibot.api import dialable
from pedibot.settings import ROOT

CHAT = ROOT / "web" / "site" / "src" / "components" / "Chat.astro"
I18N = ROOT / "web" / "site" / "src" / "i18n.ts"
LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


@pytest.fixture(scope="module")
def chat() -> str:
    return CHAT.read_text(encoding="utf-8")


# ── el número que marcar ──────────────────────────────────────────────────────────────────
CONOCIDOS = {"ES", "SA", "IN", "LB"}


@pytest.mark.parametrize(
    ("numeros", "pais", "esperado"),
    [
        ({"emergency": "112"}, "ES", "112"),
        ({"emergency": "997 (الهلال الأحمر) / 911"}, "SA", "997"),
        ({"emergency": "140 (الصليب الأحمر اللبناني) / 112"}, "LB", "140"),
        ({"emergency": "112"}, "IN", "112"),
    ],
)
def test_el_primer_numero_marcable_del_pais(numeros: dict, pais: str, esperado: str):
    assert dialable(numeros, pais, CONOCIDOS) == esperado


def test_sin_pais_no_se_inventa_un_numero():
    """La frase de respaldo lleva dos números y ninguno es el del padre."""
    frase = {"emergency": "your local emergency number (112 in the EU, 911 in the Americas)"}
    assert dialable(frase, None, CONOCIDOS) is None
    assert dialable(frase, "ZZ", CONOCIDOS) is None


def test_la_api_declara_el_campo():
    from pedibot.api import AskOut

    assert "call" in AskOut.model_fields, (
        "AskOut no tiene `call`: el cliente no puede pintar el botón"
    )
    assert AskOut.model_fields["call"].default is None


# ── el cliente ────────────────────────────────────────────────────────────────────────────
def test_una_respuesta_rapida_pregunta_en_vez_de_votar(chat: str):
    """El manejador tiene que atender `.opt` ANTES de caer al voto."""
    manejador = chat[chat.index("thread.addEventListener('click'") :]
    pos_opt = manejador.find("classList.contains('opt')")
    pos_voto = manejador.find("/api/feedback")
    assert pos_opt != -1, "los botones `.opt` no se atienden: caen al voto con answer_id=NaN"
    assert pos_opt < pos_voto, "`.opt` se comprueba después del voto, así que nunca llega"
    assert re.search(r"contains\('opt'\)\)\s*\{[^}]*\bask\(", manejador), (
        "un `.opt` tiene que llamar a ask()"
    )


def test_las_cadenas_de_error_viajan_al_cliente(chat: str):
    """Lo que el cliente pinta con `S.x` tiene que estar en data-strings, o pinta «undefined»."""
    datos = re.search(r"data-strings=\{JSON\.stringify\(\{(.*?)\}\)\}", chat, re.S)
    assert datos, "no encuentro data-strings"
    claves = set(re.findall(r"\b([a-z_]+):", datos.group(1)))
    usadas = set(re.findall(r"\bS\.([a-z_]+)", chat))
    faltan = sorted(usadas - claves)
    assert not faltan, f"el cliente usa {faltan} y no viajan: el padre vería «undefined»"


def test_cuando_pide_la_edad_hay_botones(chat: str):
    assert "verification === 'asked_age'" in chat, "sin botones de edad: hay que teclearla"
    assert "S.ages" in chat, "los botones de edad no usan las edades traducidas del chip"


def test_el_numero_de_emergencia_es_un_boton_de_llamada(chat: str):
    assert 'href="tel:' in chat, "el número de emergencias sigue siendo texto plano"
    assert "j.call" in chat, "el cliente no lee el campo `call` de la API"


@pytest.mark.parametrize("lang", LANGS)
def test_la_palabra_llamar_esta_en_cada_lengua(lang: str):
    src = I18N.read_text(encoding="utf-8")
    bloque = src[src.index(f"  {lang}: {{") :]
    m = re.search(r'chat_call:\s*"([^"]+)"', bloque)
    assert m and m.group(1).strip(), f"falta chat_call en {lang}"
    if lang != "en":
        en = re.search(r'chat_call:\s*"([^"]+)"', src[src.index("  en: {") :]).group(1)
        assert m.group(1) != en, f"chat_call en {lang} es la inglesa: es respaldo, no traducción"


# ── que no se rompa lo que ya estaba ─────────────────────────────────────────────────────
def test_las_otras_respuestas_rapidas_siguen_ahi(chat: str):
    for clase in ("share", "child", "listen"):
        assert f"classList.contains('{clase}')" in chat, f"se ha perdido el botón «{clase}»"


def test_el_sitio_construido_lleva_el_boton():
    """Astro saca el script del chat a un `.js` con hash bajo `_astro/`, no lo deja en el HTML:
    la primera versión de esta prueba miraba `index.html` y fallaba con la mejora hecha."""
    dist = ROOT / "web" / "site" / "dist"
    if not dist.exists():
        pytest.skip("el sitio no está construido en esta copia")
    js = "".join(f.read_text(encoding="utf-8") for f in (dist / "_astro").glob("*.js"))
    assert "tel:" in js and "asked_age" in js, (
        "el chat construido no lleva el botón de llamada ni las edades"
    )
