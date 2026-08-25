from __future__ import annotations

from pathlib import Path

import pytest

from pedibot.bot.llm import FakeProvider
from pedibot.index.store import Index, build_index
from pedibot.ingest.schema import Chunk
from pedibot.publish.articles import (
    TOPIC_PLAN,
    generate_article,
    parse_output,
    pending_topics,
    write_article,
)


def _chunk(cid, text, red=False, url=None):
    return Chunk(
        chunk_id=cid,
        doc_id=cid.split("#")[0],
        org="SEUP",
        doc_title="Fiebre. Información para padres",
        year=None,
        lang="es",
        section="Sección",
        pages=[1],
        text=text,
        topic="fiebre",
        doc_type="hoja_padres",
        evidence="sociedad_cientifica",
        usage="publico",
        is_red_flag=red,
        source_url=url,
        source_hash="h",
        n_words=len(text.split()),
    )


GOOD = """TITLE: When should I worry about my child's fever?
SUMMARY: Fever is a symptom, not a disease; comfort matters more than the number.
BODY:
## What it is
Fever is a rise in body temperature above 38 °C [1].
## What you can do at home
- Offer fluids and do not over-dress your child [1].
## When to see a doctor or go to the emergency department
- Spots that do not fade when pressed [2].
## Common questions
Fever itself is not dangerous [1].
"""


@pytest.fixture
def index(tmp_path: Path):
    db = tmp_path / "i.db"
    build_index(
        [
            _chunk(
                "seup_fiebre#a#1",
                "La fiebre es una elevación de la temperatura por encima de 38ºC. Ofrezca líquidos, no abrigue.",
                url="https://seup.org/f.pdf",
            ),
            _chunk(
                "seup_fiebre#b#1",
                "Consulte en urgencias si aparecen manchas en la piel que no desaparecen al presionar. fiebre",
                red=True,
            ),
            _chunk(
                "seup_acudir_urgencias#c#1",
                "Fiebre: acuda a urgencias si el niño tiene menos de 3 meses.",
            ),
        ],
        db,
    )
    return Index(db)


def test_parse_output_requires_all_parts():
    t, s, b = parse_output(GOOD)
    assert (
        t.startswith("When should") and s.startswith("Fever is") and b.startswith("## What it is")
    )
    with pytest.raises(ValueError):
        parse_output("just text")


def test_generate_and_write(index, tmp_path: Path):
    llm = FakeProvider(GOOD)
    a = generate_article(index, llm, "fiebre", "en")
    assert a.verification == "ok" and a.title.startswith("When should")
    assert len(a.sources) == 2 and a.sources[0].startswith("[1] SEUP")
    md_path, q_path = write_article(
        a, tmp_path / "content", tmp_path / "queue", "https://pedibot.xyz"
    )
    md = md_path.read_text(encoding="utf-8")
    assert (
        md.startswith("---\ntitle:")
        and "topic: fiebre" in md
        and "## Sources" in md
        and "not medical advice" in md
    )
    social = q_path.read_text(encoding="utf-8")
    assert "https://pedibot.xyz/en/guides/" in social and "SEUP" in social
    assert "fiebre" not in pending_topics(tmp_path / "content", "en")
    assert "laringitis" in pending_topics(tmp_path / "content", "en")


def test_uncited_article_is_regenerated_then_rejected(index):
    bad = GOOD.replace(" [1]", "").replace(" [2]", "")
    llm = FakeProvider(bad)
    with pytest.raises(ValueError, match="verification"):
        generate_article(index, llm, "fiebre", "en")
    assert len(llm.calls) == 2


def test_dose_numbers_without_table_rejected(index):
    llm = FakeProvider(GOOD.replace("Offer fluids", "Give 150 mg of paracetamol"))
    with pytest.raises(ValueError):
        generate_article(index, llm, "fiebre", "en")


def test_topic_plan_docs_exist_in_catalog(config_dir):
    from pedibot.ingest.catalog import load_catalog

    ids = {d.doc_id for d in load_catalog(config_dir / "fuentes.yaml")}
    for topic, plan in TOPIC_PLAN.items():
        for d in plan["docs"]:
            assert d in ids, (topic, d)


def test_frontmatter_is_valid_yaml_with_quotes(index, tmp_path: Path):
    import yaml

    llm = FakeProvider(GOOD.replace("When should I worry", 'When should I "worry"'))
    a = generate_article(index, llm, "fiebre", "en")
    md_path, _ = write_article(a, tmp_path / "content", tmp_path / "queue", "https://x")
    fm = md_path.read_text(encoding="utf-8").split("---")[1]
    data = yaml.safe_load(fm)
    assert '"worry"' in data["title"] and data["sources"][0].startswith("[1] SEUP")
