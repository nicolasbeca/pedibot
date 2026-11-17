"""Una pregunta de seguimiento larga sigue buscando el tema de antes (17-nov-2026).

Consulta real desde España el 13-nov (1284-1285):

    «Mi hijo se ha caido y se ha dado en la cabeza»
    «Al poco tiempo estaba como si nada jugandose y riendose. Debo mantenerlo despierto?»

La primera salió bien, con la hoja del traumatismo craneal de la SEUP. La segunda citó la hoja de
la CONVULSIÓN FEBRIL: la hoja del golpe, que dice justo eso («puede dormir, pero en traumatismos
más importantes, es recomendable despertarlo cada 4 horas»), no llegó.

La búsqueda sólo sumaba el mensaje anterior si el de ahora tenía ocho palabras o menos, y éste
tenía trece. Y aunque lo hubiera sumado, en las lenguas del corpus la búsqueda se rehacía con la
lectura de la IA, que por diseño describe sólo el mensaje actual («should I keep my child
awake?»): el golpe se perdía también en las cortas. Si la lectura dice que sigue siendo el mismo
problema, lo de antes entra en la búsqueda, sea cual sea el largo.
"""

from __future__ import annotations

from test_the_ai_reads_the_question_first import _json, _motor

GOLPE = [
    {"role": "user", "text": "Mi hijo se ha caido y se ha dado en la cabeza"},
    {"role": "assistant", "text": "Vigila las primeras 24 horas."},
]
SIGUE = (
    "Al poco tiempo estaba como si nada jugandose y riendose. Debo mantenerlo despierto?"
)
LEIDA = dict(
    lang="es",
    lang_name="Spanish",
    query_en="Should I keep my child awake?",
    query_es="¿Debo mantener a mi hijo despierto?",
    keywords=["sleep", "dormir", "keep awake", "despierto"],
)


def _busquedas(visto: dict) -> str:
    return " || ".join(str(b) for b in visto["busquedas"])


def test_a_long_followup_searches_the_head_injury_too() -> None:
    motor, visto = _motor(_json(new_topic=False, **LEIDA))
    motor.ask(SIGUE, lang="es", history=GOLPE)
    assert "cabeza" in _busquedas(visto), _busquedas(visto)


def test_a_short_followup_keeps_it_after_the_ai_reading() -> None:
    motor, visto = _motor(_json(new_topic=False, **LEIDA))
    motor.ask("¿Debo mantenerlo despierto?", lang="es", history=GOLPE)
    assert "cabeza" in _busquedas(visto), _busquedas(visto)


def test_a_new_topic_does_not_carry_the_old_one() -> None:
    motor, visto = _motor(
        _json(
            new_topic=True,
            lang="es",
            lang_name="Spanish",
            query_en="My baby has red eyes",
            query_es="Mi bebé tiene los ojos rojos",
        )
    )
    motor.ask("Ahora otra cosa: mi bebé tiene los ojos muy rojos desde esta mañana", lang="es",
              history=GOLPE)
    assert "cabeza" not in _busquedas(visto), _busquedas(visto)


def test_with_the_real_index_the_seup_sleep_passage_comes_first() -> None:
    """Con las dos frases juntas, el pasaje de la SEUP que dice «puede dormir… despertarlo»."""
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.index.store import Index
    from pedibot.ingest.classify import Taxonomy
    from pedibot.settings import get_settings

    s = get_settings()
    r = Retriever(
        Index(s.index_db_path),
        Synonyms(s.config_dir / "synonyms.yaml", s.config_dir / "drugs.yaml"),
        llm=None,
        top_k=s.retrieval_top_k,
        taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
    )
    hits, _ = r.search(f"{GOLPE[0]['text']} {SIGUE}", "es")
    ids = [h.chunk.chunk_id for h in hits]
    assert "seup_tce#que_podemos_hacer_en_casa#1" in ids[:3], ids
    assert not any("convulsion" in i for i in ids), ids
