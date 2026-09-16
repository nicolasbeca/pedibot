"""El árabe que escribe un padre no es el de las fichas (16-sep-2026).

Las fichas de la OMS están en árabe estándar y un padre escribe en su dialecto. Medido sobre
ocho frases corrientes del Golfo, de Egipto y del Levante: **seis no encontraban ninguna
fuente**, y una de ellas es de seguridad —«ابني وقع على راسه» (mi hijo se cayó de cabeza)—
que salía como RUTINA porque el triaje sólo conocía «سقط».

Lo que cambia entre el estándar y lo que se teclea:

    sacudida         سقط        →  وقع / طاح        (cayó)
    cabeza           رأسه       →  راسه            (sin hamza, en los tres dialectos)
    tiene fiebre     عنده حمى   →  سخن / حرارة      (Golfo / Levante)
    vomita           يتقيأ      →  يستفرغ / بيرجع   (Levante / Egipto)
    llora            يبكي       →  بيعيط            (Egipto)
    granos           طفح جلدي   →  حبوب             (Golfo)
    mis hijos        أطفالي     →  عيالي            (Golfo)
    no come          لا يأكل    →  ما ياكل / مش بياكل

No es un problema de traducción: es que la palabra con la que se pregunta no está escrita en
ningún sitio de este repositorio, ni en el triaje ni en los sinónimos.
"""

from __future__ import annotations

import re

import pytest

from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.index.store import Index
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    return Retriever(
        Index(ROOT / "index" / "pedibot.db"),
        Synonyms(ROOT / "config" / "synonyms.yaml", ROOT / "config" / "drugs.yaml"),
        top_k=6,
        taxonomy=Taxonomy(ROOT / "config" / "taxonomia.yaml"),
    )


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


#: (pregunta, variedad, expresión que debe aparecer entre las tres primeras fuentes)
DIALECTO = [
    ("ولدي سخن ومو راضي ياكل", "golfo", r"fever|fiebre|hma"),
    ("عيالي عندهم اسهال", "golfo", r"diarrh|gastro|is-hal|isal"),
    ("ابني بيكح كتير ومش عارف ينام", "egipcio", r"cough|croup|catarro|tos|respirat"),
    ("البيبي بيعيط كتير بالليل", "egipcio", r"colic|crying|soothing|colico"),
    ("ابني عم يستفرغ من امبارح", "levantino", r"vomit|gastro|norovirus"),
    ("بنتي عندها حرارة وما بتاكل", "levantino", r"fever|fiebre"),
    ("ولدي طلع عنده حبوب بجسمه", "golfo", r"rash|urticaria|piel|chickenpox"),
    ("ابني وقع على راسه", "todos", r"head|craneal|tce|concussion"),
]


@pytest.mark.parametrize(("pregunta", "variedad", "esperado"), DIALECTO)
def test_el_dialecto_encuentra_su_ficha(
    buscador: Retriever, pregunta: str, variedad: str, esperado: str
) -> None:
    hits, extra = buscador.search(pregunta, "ar")
    assert hits, f"[{variedad}] «{pregunta}» no encuentra nada (expansión: {extra})"
    ids = [h.chunk.chunk_id for h in hits[:3]]
    assert any(re.search(esperado, i, re.I) for i in ids), f"[{variedad}] «{pregunta}» → {ids}"


#: Lo que el triaje tiene que ver aunque esté dicho en dialecto. El golpe en la cabeza es el
#: que lo destapó: «وقع على راسه» salía rutina y sin fuentes.
ALARMAS = [
    ("ابني وقع على راسه وصار يستفرغ", ("urgent", "emergency")),
    ("ولدي طاح على راسه ومو صاحي", ("urgent", "emergency")),
    ("البيبي بيعيط وشفايفه زرقا", ("emergency",)),
    ("ابني عنده تشنج", ("emergency",)),
]


@pytest.mark.parametrize(("frase", "niveles"), ALARMAS)
def test_la_alarma_en_dialecto_se_ve(triaje: Triage, frase: str, niveles: tuple[str, ...]) -> None:
    r = triaje.assess(frase)
    assert r.level in niveles, f"«{frase}» → {r.level} ({[x.id for x in r.matched]})"


def test_y_lo_corriente_sigue_siendo_corriente(triaje: Triage) -> None:
    for frase in ("ولدي ياكل زين ويلعب", "ابني بخير الحمد لله", "طفلي نام كويس"):
        assert triaje.assess(frase).level == "routine", frase


def test_caerse_de_cabeza_no_es_una_emergencia_por_si_solo(triaje: Triage) -> None:
    """Como en la regla inglesa: hace falta además perder el conocimiento o vomitar. Un niño se
    cae de cabeza todas las semanas, y un aviso que salta siempre deja de leerse."""
    assert triaje.assess("ابني وقع على راسه").level == "routine"
    assert triaje.assess("ولدي طاح وهو يلعب").level == "routine"
    # pero con lo otro, sí
    assert triaje.assess("ولدي طاح على راسه ومو صاحي").level in ("urgent", "emergency")


# ── y el árabe tecleado en letras latinas ────────────────────────────────────
# El «franco-árabe» es lo normal en el Golfo y en Egipto: el móvil está en inglés y las letras
# que no existen se escriben con cifras — 3 es ع, 7 es ح, 5 es خ. Medido el 16-sep-2026:
# **las diez preguntas de prueba no encontraban NADA**, ni una ficha.
ARABIZI = [
    ("ibni 3ando sokhouna", r"fever|fiebre"),
    ("tifli 3ando harara shadida", r"fever|fiebre"),
    ("ibni 3ando is-hal", r"diarrh|gastro"),
    ("el walad 3ando ko7a", r"cough|croup|cold|catarro"),
    ("ibni waga3 batno", r"abdominal|stomach|constipation|gastro"),
    ("bnti 3andha tafh jildi", r"rash|urticaria|piel|chickenpox"),
    ("el beby byebki keteer", r"colic|crying|soothing"),
    ("ibni ma yzeed wazno", r"growth|weight|nutrition|feeding"),
]


@pytest.mark.parametrize(("pregunta", "esperado"), ARABIZI)
def test_el_arabe_en_letras_latinas_encuentra_su_ficha(
    buscador: Retriever, pregunta: str, esperado: str
) -> None:
    hits, extra = buscador.search(pregunta, "ar")
    assert hits, f"«{pregunta}» no encuentra nada (expansión: {extra})"
    ids = [h.chunk.chunk_id for h in hits[:3]]
    assert any(re.search(esperado, i, re.I) for i in ids), f"«{pregunta}» → {ids}"


def test_da_igual_como_se_escriba_la_cifra(buscador: Retriever) -> None:
    """«3ando» y «aando» son la misma palabra; «ko7a», «koha» y «kouha» también."""
    assert buscador.expand("ibni 3ando sokhouna", "ar")
    assert set(buscador.expand("ko7a", "ar")) == set(buscador.expand("koha", "ar"))
    assert set(buscador.expand("sokhouna", "ar")) == set(buscador.expand("sukhuna", "ar"))


def test_el_arabe_de_siempre_sigue_igual(buscador: Retriever) -> None:
    """La normalización es del árabe: no puede tocar lo que ya funcionaba."""
    assert buscador.expand("طفلي عنده حمى", "ar")
    hits, _ = buscador.search("طفلي عنده حمى منذ يومين", "ar")
    assert hits and any("fever" in h.chunk.chunk_id or "hma" in h.chunk.chunk_id for h in hits[:3])
