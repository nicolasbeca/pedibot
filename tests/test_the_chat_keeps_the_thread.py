"""Después de una respuesta el padre casi siempre tiene otra pregunta, y el chat le dejaba solo
(12-sep-2026).

Segunda lectura de `Chat.astro`, esta vez de lo que pasa DESPUÉS de una respuesta:

1. **Las preguntas siguientes.** Tras «tiene fiebre» viene «¿cuánto paracetamol?» o «¿cuándo voy
   a urgencias?». El chat no ofrecía nada: el padre tenía que saber qué preguntar y teclearlo.
   Ahora la API manda hasta tres preguntas siguientes según el asunto de la respuesta, en la lengua
   del padre, y **cada una de ellas tiene fuente en el corpus**: una pregunta sugerida que acaba
   en «no tengo fuente» es peor que ninguna. Esa es la prueba que manda aquí.
2. **Los botones de edad no ajustaban el chip.** El padre tocaba «2 años», el servidor contestaba
   con la edad, y la pregunta siguiente salía otra vez sin edad: se la volvía a pedir.
3. **La edad escrita sólo se reconocía en castellano e inglés.** Un padre francés que escribe
   «mon fils de 3 ans» con el chip en «2 ans» mandaba las dos edades en la misma frase.
4. **«Leer en alto» leía también los botones**: «📄 Guía: …», «💊 Abrir la calculadora»,
   «📞 Llamar al 112». Ahora lee la respuesta, y un segundo toque la calla.
5. **Sin red, sin salida.** «No he podido conectar» y nada que tocar: había que volver a teclear
   la pregunta. Ahora hay «Reintentar», que manda la misma pregunta y quita el error.
"""

from __future__ import annotations

import re

import pytest
import yaml

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import ROOT

CHAT = ROOT / "web" / "site" / "src" / "components" / "Chat.astro"
I18N = ROOT / "web" / "site" / "src" / "i18n.ts"
FOLLOWUPS = ROOT / "config" / "followups.yaml"
LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


@pytest.fixture(scope="module")
def chat() -> str:
    return CHAT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    return Retriever(
        Index(ROOT / "index" / "pedibot.db"),
        Synonyms(ROOT / "config" / "synonyms.yaml", ROOT / "config" / "drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(ROOT / "config" / "taxonomia.yaml"),
    )


def _tabla() -> dict[str, dict[str, list[str]]]:
    if not FOLLOWUPS.exists():
        return {}
    return yaml.safe_load(FOLLOWUPS.read_text(encoding="utf-8"))["followups"]


CASOS = [
    (asunto, lang, q)
    for asunto, por_lengua in _tabla().items()
    for lang in LANGS
    for q in por_lengua.get(lang, [])
]


# ── la tabla ──────────────────────────────────────────────────────────────────────────────
def test_hay_tabla_y_cubre_lo_que_mas_se_pregunta():
    tabla = _tabla()
    assert tabla, "no hay config/followups.yaml: el chat no ofrece preguntas siguientes"
    for asunto in ("fiebre", "respiratorio", "digestivo", "piel", "medicamentos", "vacunas"):
        assert asunto in tabla, (
            f"sin preguntas siguientes para «{asunto}», que es de lo más preguntado"
        )


def test_cada_asunto_en_las_ocho_lenguas_y_traducido():
    for asunto, por_lengua in _tabla().items():
        assert set(por_lengua) == set(LANGS), f"«{asunto}» no está en las ocho lenguas"
        for lang in LANGS:
            qs = por_lengua[lang]
            assert 2 <= len(qs) <= 3, (
                f"«{asunto}»/{lang}: {len(qs)} preguntas; entre 2 y 3, que caben en un móvil"
            )
            assert all(q.strip() for q in qs)
            assert len(set(qs)) == len(qs), f"«{asunto}»/{lang}: pregunta repetida"
            if lang != "en":
                assert not set(qs) & set(por_lengua["en"]), (
                    f"«{asunto}»/{lang} lleva la inglesa: es respaldo, no traducción"
                )


def test_los_asuntos_son_de_la_taxonomia():
    temas = set(
        yaml.safe_load((ROOT / "config" / "taxonomia.yaml").read_text(encoding="utf-8"))["topics"]
    )
    raros = set(_tabla()) - temas
    assert not raros, (
        f"asuntos que la taxonomía no conoce, así que nunca se ofrecerían: {sorted(raros)}"
    )


@pytest.mark.parametrize(
    ("asunto", "lang", "q"), CASOS, ids=[f"{a}-{lg}-{n}" for n, (a, lg, _) in enumerate(CASOS)]
)
def test_cada_pregunta_sugerida_tiene_fuente(buscador: Retriever, asunto: str, lang: str, q: str):
    """Una pregunta que ofrecemos nosotros y acaba en «no tengo fuente» es peor que ninguna."""
    hits, _ = buscador.search(q, lang)
    assert hits, f"«{q}» ({lang}, {asunto}) no encuentra fuente: no se puede ofrecer"


# ── el módulo y la API ────────────────────────────────────────────────────────────────────
def test_el_modulo_sirve_las_preguntas_y_no_repite_la_que_acaban_de_hacer():
    from pedibot.bot.followups import Followups

    f = Followups(FOLLOWUPS)
    primera = f.for_topic("fiebre", "es")[0]
    assert f.for_topic("fiebre", "es")
    assert f.for_topic(None, "es") == []
    assert f.for_topic("fiebre", "xx") == []
    assert f.for_topic("no_existe", "es") == []
    assert primera not in f.for_topic("fiebre", "es", asked=primera.upper() + " ")


def test_la_api_declara_el_campo():
    from pedibot.api import AskOut

    assert "followups" in AskOut.model_fields, (
        "AskOut no tiene `followups`: el cliente no puede pintarlas"
    )
    assert AskOut.model_fields["followups"].default == []


# ── el cliente ────────────────────────────────────────────────────────────────────────────
def _manejador(chat: str) -> str:
    return chat[chat.index("thread.addEventListener('click'") :]


def test_el_cliente_pinta_las_preguntas_siguientes_como_preguntas(chat: str):
    assert "j.followups" in chat, "el cliente no lee `followups`"
    trozo = chat[chat.index("j.followups") :][:400]
    assert 'class="fb opt"' in trozo, (
        "las preguntas siguientes no van por `.opt`, que es lo que llama a ask()"
    )


def test_el_boton_de_edad_ajusta_el_chip(chat: str):
    assert "data-age=" in chat, "los botones de edad no llevan el valor del chip"
    m = _manejador(chat)
    assert re.search(r"dataset\.age[^;]*;?\s*[^;]*ageSel\.value\s*=", m) or (
        "dataset.age" in m and "ageSel.value = " in m
    ), "tocar una edad no ajusta el chip: la pregunta siguiente sale sin edad y se vuelve a pedir"


@pytest.mark.parametrize(
    "forma",
    [
        "ans",
        "mois",
        "jahr",
        "monat",
        "лет",
        "год",
        "мес",
        "anos",
        "साल",
        "महीन",
        "سنوات",
        "شهر",
        "أسبوعان",
        "سنتان",
    ],
)
def test_la_edad_escrita_se_reconoce_en_cada_lengua(chat: str, forma: str):
    linea = next(ln for ln in chat.splitlines() if "chat_age_note.replace" in ln)
    assert forma in linea, (
        f"«{forma}» escrito en la pregunta no se reconoce: se añade el chip encima"
    )


def test_el_boton_de_escuchar_ya_no_esta(chat: str):
    """21-sep-2026, el operador: «el botón escuchar elimínalo, es irrelevante ahora»."""
    assert 'class="txt"' in chat, "la respuesta no está separada de los botones"
    assert "fb listen" not in chat
    assert "speechSynthesis" not in chat


def test_hay_reintento_cuando_falla_la_red(chat: str):
    assert "S.chat_retry" in chat, "no hay botón de reintento"
    m = _manejador(chat)
    pos_retry, pos_voto = m.find("classList.contains('retry')"), m.find("/api/feedback")
    assert pos_retry != -1 and pos_retry < pos_voto, "`.retry` cae al voto"
    pide = chat[chat.index("async function ask(") : chat.index("thread.addEventListener")]
    assert pide.count("retry") >= 2, (
        "el reintento no está en las dos ramas de error (servidor y red)"
    )


@pytest.mark.parametrize("lang", LANGS)
def test_reintentar_esta_en_cada_lengua(lang: str):
    src = I18N.read_text(encoding="utf-8")
    bloque = src[src.index(f"  {lang}: {{") :]
    m = re.search(r'chat_retry:\s*"([^"]+)"', bloque)
    assert m and m.group(1).strip(), f"falta chat_retry en {lang}"
    if lang != "en":
        en = re.search(r'chat_retry:\s*"([^"]+)"', src[src.index("  en: {") :]).group(1)
        assert m.group(1) != en, f"chat_retry en {lang} es la inglesa"
