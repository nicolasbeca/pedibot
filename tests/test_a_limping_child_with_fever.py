"""Cojear con fiebre no es rutina, y «cojera» tiene que llegar a «claudicación» (17-sep-2026).

Lo probó el operador en la web: *«he buscado qué pasa si mi hijo cojea y tiene fiebre, que es un
síntoma grave, y me dice que no sabe nada de cojeras cuando en alguna de mis guías sí que venía
que era para ir a urgencias»*. Reproducido contra lo vivo, era peor de lo que contaba:

    nivel: routine · «La cojera no aparece en estas fuentes, así que no tengo información
    fiable sobre ella: coméntela con su pediatra.»

Dos fallos distintos, y los dos se arreglan aquí:

1. **El triaje no tenía ninguna regla.** Los `limp` que aparecían en `red_flags.yaml` eran falsos
   amigos: «limp» de flojo y «limpieza» de producto de limpieza.

2. **La palabra del padre no llegaba al material.** El corpus tiene el capítulo «Claudicación en
   niños» y los de artritis séptica y osteomielitis del Manual de Pediatría de la Universidad
   Católica de Chile, y el de claudicación de Pediatría. Diagnóstico y tratamiento. Pero un padre
   no escribe «claudicación», escribe «cojea», y sin puente esos capítulos no se abren nunca.

Por qué urgente y no rutina, con lo que dice el propio corpus: la sinovitis transitoria —la causa
más frecuente de cojera en un niño pequeño— cursa con **temperatura menor de 38 ºC**, y su
diagnóstico diferencial principal es la artritis séptica. El manual lo dice sin rodeos: «en la
primera aproximación, siempre descartar infecciones o fracturas ocultas, que son los cuadros más
urgentes de diagnosticar». Cojera más fiebre es exactamente la combinación que hay que descartar
el mismo día.

Y por qué NO emergencia: una cojera sola, sin fiebre, es casi siempre una tontería —una piedra en
el zapato, un golpe sin contar—. Un aviso que salta siempre deja de leerse, que es la lección que
ya nos costó el golpe en la cabeza en árabe.
"""

from __future__ import annotations

import pytest

from pedibot.bot.retrieval import Index, Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.ingest.classify import Taxonomy
from pedibot.settings import ROOT, get_settings


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


@pytest.fixture(scope="module")
def buscador() -> Retriever:
    s = get_settings()
    return Retriever(
        Index(s.index_db_path),
        Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
        top_k=40,
        taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
    )


#: La frase del operador y su equivalente en los otros siete idiomas del sitio.
COJEA_CON_FIEBRE = [
    ("es", "mi hijo cojea y tiene fiebre"),
    ("es", "tiene fiebre y no quiere apoyar la pierna"),
    ("es", "mi niña de 4 años cojea desde ayer y está con 38.5"),
    ("en", "my child is limping and has a fever"),
    ("en", "he has a temperature and refuses to walk on his leg"),
    ("fr", "mon enfant boite et a de la fièvre"),
    ("de", "mein kind hinkt und hat fieber"),
    ("ru", "ребёнок хромает и у него температура"),
    ("ar", "ابني يعرج وعنده حرارة"),
    ("pt", "o meu filho coxeia e está com febre"),
    ("hi", "मेरा बच्चा लंगड़ा कर चल रहा है और बुखार है"),
]

#: Lo que NO puede convertirse en un aviso: cojear sin fiebre, y la fiebre sola.
NO_ES_ESTA_REGLA = [
    ("es", "cojea desde que se cayó jugando al fútbol"),
    ("es", "mi hijo tiene fiebre y está muy cansado"),
    ("en", "he limps a bit after falling off his bike"),
    ("en", "my daughter has a fever and a sore throat"),
    ("fr", "il boite depuis qu'il est tombé"),
    ("de", "er hinkt, seit er gestürzt ist"),
]


@pytest.mark.parametrize("lang,texto", COJEA_CON_FIEBRE)
def test_limping_with_fever_is_seen_today_not_next_week(triaje: Triage, lang: str, texto: str):
    r = triaje.assess(texto)
    assert r.level == "urgent", f"[{lang}] «{texto}» sale como {r.level}"
    assert any(m.id == "limp_with_fever" for m in r.matched), f"[{lang}] salta otra regla"


@pytest.mark.parametrize("lang,texto", NO_ES_ESTA_REGLA)
def test_a_limp_without_fever_is_not_an_alarm(triaje: Triage, lang: str, texto: str):
    r = triaje.assess(texto)
    ids = [m.id for m in r.matched]
    assert "limp_with_fever" not in ids, f"[{lang}] «{texto}» dispara la regla de cojera: {ids}"


def test_the_rule_says_why_in_every_language(triaje: Triage):
    """El motivo se le enseña al padre; si falta en su idioma, se le enseña en otro."""
    regla = next(r for r in triaje.rules if r.id == "limp_with_fever")
    assert regla.reason_es and regla.reason_en
    for lg in ("fr", "de", "ru", "ar", "pt", "hi"):
        assert regla.reasons_by_lang.get(lg), f"la regla no explica el porqué en {lg}"


# ── la segunda mitad: que la palabra del padre llegue al capítulo ────────────────────────────
@pytest.mark.parametrize(
    "lang,pregunta",
    [
        ("es", "mi hijo cojea"),
        ("es", "mi hijo cojea y tiene fiebre"),
        ("en", "my child is limping"),
    ],
)
def test_the_word_a_parent_uses_reaches_the_chapter(buscador: Retriever, lang: str, pregunta: str):
    """«Cojea» tiene que abrir «claudicación»: son la misma cosa escritas por dos personas."""
    hits, _ = buscador.search(pregunta, lang=lang)
    textos = " ".join(h.chunk.text.lower() for h in hits)
    assert any(
        p in textos for p in ("claudicación", "claudicacion", "cojera", "cojea", "artritis séptica")
    ), f"[{lang}] «{pregunta}» no trae ni un pasaje sobre la cojera"
