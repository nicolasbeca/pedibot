from __future__ import annotations

from pathlib import Path

from pedibot.bot.answer import EmergencyNumbers, Engine
from pedibot.bot.llm import FakeProvider
from pedibot.bot.retrieval import Retriever, Synonyms
from pedibot.bot.triage import Triage
from pedibot.eval import load_golden, run_eval, run_llm_eval
from pedibot.index.store import Index, build_index
from pedibot.ingest.classify import Taxonomy
from pedibot.ingest.schema import Chunk


def _chunk(cid, text):
    return Chunk(
        chunk_id=cid,
        doc_id=cid.split("#")[0],
        org="SEUP",
        doc_title="Fiebre. Información para padres",
        year=None,
        lang="es",
        section="S",
        pages=[1],
        text=text,
        topic="fiebre",
        doc_type="hoja_padres",
        evidence="sociedad_cientifica",
        usage="publico",
        source_hash="h",
        n_words=len(text.split()),
    )


def _engine(tmp_path: Path, config_dir, responder, name: str = "i.db"):
    db = tmp_path / name  # one file per engine: Windows cannot unlink an open SQLite db
    build_index([_chunk("seup_fiebre#s#1", "La fiebre no es peligrosa. Ofrezca líquidos.")], db)
    llm = FakeProvider(responder)
    return Engine(
        Retriever(
            Index(db),
            Synonyms(config_dir / "synonyms.yaml"),
            taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
        ),
        Triage(config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(config_dir / "emergency_numbers.yaml"),
    )


GOLDEN = [
    {
        "id": "a",
        "q": "mi hijo de 4 años tiene fiebre",
        "lang": "es",
        "level": "routine",
        "docs": ["seup_fiebre"],
    },
    {
        "id": "b",
        "q": "mi hijo tiene fiebre",
        "lang": "es",
        "level": "routine",
        "expect": "asked_age",
    },
    {
        "id": "c",
        "q": "está teniendo una convulsión",
        "lang": "es",
        "level": "emergency",
        "rules": ["seizure"],
    },
]


def test_golden_file_is_well_formed():
    from pedibot.settings import ROOT

    g = load_golden(ROOT / "eval" / "golden.jsonl")
    assert len(g) >= 50
    ids = [x["id"] for x in g]
    assert len(ids) == len(set(ids))
    for x in g:
        assert x["level"] in ("routine", "urgent", "emergency", "mental_health")
        assert x.get("docs") or x.get("expect"), x["id"]


def test_run_eval_metrics(tmp_path, config_dir):
    rep = run_eval(_engine(tmp_path, config_dir, "Texto [1]."), GOLDEN)
    s = rep.summary()
    assert s["triage_exact"] == 1.0 and s["red_flag_recall"] == 1.0 and s["rules_hit"] == 1.0
    assert s["source_hit"] == 1.0 and s["routing"] == 1.0
    assert rep.failures() == []


def test_run_llm_eval_measures_verification(tmp_path, config_dir):
    # del largo de una respuesta: una frase corta sin cita es una negativa, no un borrador malo
    rep = run_llm_eval(_engine(tmp_path, config_dir, "La fiebre es un mecanismo de defensa del cuerpo frente a las infecciones y en la mayoría de los niños dura entre dos y cuatro días, conviene ofrecer líquidos, vigilar el estado general y consultar si aparece cualquier signo que preocupe a la familia o si no mejora."), GOLDEN)
    s = rep.summary()
    assert s["n"] == 2  # asked_age case skipped
    assert s["citation_validity"] == 0.0  # every draft fell back
    rep2 = run_llm_eval(_engine(tmp_path, config_dir, "Con cita [1].", "j.db"), GOLDEN)
    assert rep2.summary()["citation_validity"] == 1.0 and rep2.summary()["with_sources"] == 1.0
