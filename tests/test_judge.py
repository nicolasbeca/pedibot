from __future__ import annotations

from pedibot.bot.judge import judge
from pedibot.bot.llm import FakeProvider
from pedibot.index.store import Hit
from pedibot.ingest.schema import Chunk


def _hit(text: str) -> Hit:
    c = Chunk(
        chunk_id="seup_fiebre#s#1",
        doc_id="seup_fiebre",
        org="SEUP",
        doc_title="Fiebre",
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
        n_words=3,
    )
    return Hit(c, 1.0, 1)


def test_judge_parses_verdict_and_passes_passages():
    llm = FakeProvider(
        '{"verdict": "unfaithful", "unsupported": ["give 150 mg"], "contradicted": [], "notes": "dose not in source"}'
    )
    v = judge(llm, "Give 150 mg [1].", [_hit("La fiebre no es peligrosa.")], [1])
    assert v.verdict == "unfaithful" and not v.ok and v.unsupported == ["give 150 mg"]
    assert "La fiebre no es peligrosa" in llm.calls[0][1] and "SOURCE PASSAGES" in llm.calls[0][1]


def test_judge_unparseable():
    v = judge(FakeProvider("no json here"), "x [1]", [_hit("y")], [1])
    assert v.verdict == "unparseable" and not v.ok


def test_judge_faithful():
    v = judge(
        FakeProvider(
            '{"verdict": "faithful", "unsupported": [], "contradicted": [], "notes": "ok"}'
        ),
        "x [1]",
        [_hit("y")],
        [1],
    )
    assert v.ok
