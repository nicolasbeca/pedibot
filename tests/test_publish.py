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
    # English is served from the root: /en/guides/<slug> is a 404 (fixed 26-ago)
    assert "https://pedibot.xyz/guides/" in social and "SEUP" in social
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


_ES_DRAFT = (
    "TITLE: ¿Qué vacunas necesita mi hijo y cuándo?\n"
    "SUMMARY: Guía clara sobre el calendario de vacunación infantil en España.\n"
    "BODY:\n## Qué es\nLas vacunas protegen a tu hijo de enfermedades graves antes de que se "
    "exponga a ellas [1]. En España el calendario recomendado incluye varias dosis durante la "
    "infancia y es importante que se administren en tiempo [1].\n"
    "## Qué puedes hacer en casa\nLleva la cartilla al día [1].\n"
    "## Cuándo acudir al médico o a urgencias\nSi hay fiebre alta tras la vacuna [1].\n"
    "## Preguntas frecuentes\n¿Se pueden juntar dosis? Sí [1].\n"
)


def test_an_article_in_the_wrong_language_is_rejected(tmp_path: Path, monkeypatch):
    """26-ago: a Spanish topic generated with --lang en wrote a Spanish guide into web/content/en
    with `lang: en` in the frontmatter, which also breaks canonical/hreflang."""
    db = tmp_path / "i.db"
    build_index(
        [_chunk("seup_vacunas#1", "calendario de vacunación infantil dosis a los 2 meses")], db
    )
    monkeypatch.setitem(
        TOPIC_PLAN, "_vacunas", {"docs": ["seup_vacunas"], "query": "calendario vacunación"}
    )
    with pytest.raises(ValueError, match="wrong_language"):
        generate_article(Index(db), FakeProvider(_ES_DRAFT), "_vacunas", lang="en")


def test_an_article_in_the_requested_language_passes(tmp_path: Path, monkeypatch):
    db = tmp_path / "i.db"
    build_index(
        [_chunk("seup_vacunas#1", "calendario de vacunación infantil dosis a los 2 meses")], db
    )
    monkeypatch.setitem(
        TOPIC_PLAN, "_vacunas", {"docs": ["seup_vacunas"], "query": "calendario vacunación"}
    )
    draft = (
        "TITLE: What vaccines does my child need?\n"
        "SUMMARY: A clear guide to the childhood immunisation schedule.\n"
        "BODY:\n## What it is\nVaccines protect your child from serious illness before they are "
        # «Spanish» no es decoración: las fuentes de este borrador son de la SEUP, y desde
        # el 23-sep-2026 una guía que describe el calendario de un país sin nombrarlo no se
        # publica
        "exposed to it [1]. The Spanish schedule gives several doses during the first year [1].\n"
        "## What you can do at home\nKeep the record up to date [1].\n"
        "## When to see a doctor or go to the emergency department\nHigh fever after a dose [1].\n"
        "## Common questions\nCan doses be combined? Yes [1].\n"
    )
    a = generate_article(Index(db), FakeProvider(draft), "_vacunas", lang="en")
    assert a.lang == "en"


def test_english_only_topics_are_not_offered_in_spanish(tmp_path: Path):
    """A topic key ending in `_en` is anchored on English-speaking material (NHS/CDC schedules).
    Generated in Spanish it produced a second, near-duplicate vaccines guide about the UK and US
    calendars — duplicate content that also confuses the reader."""
    es = pending_topics(tmp_path, "es")
    assert [t for t in es if t.endswith("_en")] == []
    assert "vacunas" in es, "the Spanish calendar topic must still be offered"
    assert "vaccines_en" in pending_topics(tmp_path, "en")


def test_the_social_link_points_at_a_page_that_exists(tmp_path: Path, monkeypatch):
    """English lives at the root of the site, not under /en: every English social post was
    linking to /en/guides/<slug>, which is a 404 (26-ago)."""
    db = tmp_path / "i.db"
    build_index([_chunk("seup_fiebre#1", "la fiebre no es peligrosa por si misma")], db)
    monkeypatch.setitem(TOPIC_PLAN, "_f", {"docs": ["seup_fiebre"], "query": "fiebre"})
    draft = (
        "TITLE: Fever in children\nSUMMARY: What to do.\n"
        "BODY:\n## What it is\nFever is common [1].\n"
        "## What you can do at home\nFluids and rest [1].\n"
        "## When to see a doctor or go to the emergency department\nIf the baby is under three months [1].\n"
        "## Common questions\nHow long does it last? A few days [1].\n"
    )
    en = generate_article(Index(db), FakeProvider(draft), "_f", lang="en")
    assert "https://pedibot.xyz/guides/" in en.social_text("https://pedibot.xyz")
    assert "/en/guides/" not in en.social_text("https://pedibot.xyz")

    draft_es = (
        "TITLE: La fiebre\nSUMMARY: Qué hacer.\nBODY:\n## Qué es\nLa fiebre es frecuente [1].\n"
        "## Qué puedes hacer en casa\nLíquidos y descanso [1].\n"
        "## Cuándo acudir al médico o a urgencias\nSi el bebé tiene menos de tres meses [1].\n"
        "## Preguntas frecuentes\n¿Cuánto dura? Unos días [1].\n"
    )
    es = generate_article(Index(db), FakeProvider(draft_es), "_f", lang="es")
    assert "https://pedibot.xyz/es/guides/" in es.social_text("https://pedibot.xyz")


def _publish_stub(dir_: Path, lang: str, slug: str, topic: str) -> None:
    d = dir_ / lang
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.md").write_text(
        f"---\ntitle: t\ntopic: {topic}\nlang: {lang}\n---\nx\n", encoding="utf-8"
    )


def test_a_subject_is_not_published_twice_under_two_topic_names(tmp_path: Path):
    """TOPIC_PLAN carries a Spanish-named and an English-named key for the same subject
    (golpe_calor/heat, urticaria/hives, cefalea/headache_en…). In English both were offered and we
    ended up with two guides about heatstroke — duplicate content that splits the SEO signal."""
    _publish_stub(tmp_path, "en", "what_should_i_do_if_my_child_has_heat_stroke", "golpe_calor")
    pending = pending_topics(tmp_path, "en")
    assert "golpe_calor" not in pending  # already published
    assert "heat" not in pending, "same sources as the guide already published"


def test_comparison_articles_are_still_offered(tmp_path: Path):
    """The `compare_*` topics reuse the same sources on purpose (a comparison table is a different
    article from the guide), so the deduplication must not swallow them."""
    _publish_stub(tmp_path, "en", "fever", "fiebre")
    pending = pending_topics(tmp_path, "en")
    assert "compare_fever_medicine" in pending
    assert "compare_fever_threshold" in pending


def test_a_batch_does_not_publish_two_guides_on_the_same_subject(tmp_path: Path):
    """`pending_topics` was read once at the start of the run, so within a single batch the
    deduplication never saw what the batch itself had just written: a run of 90 topics produced
    both hives and urticaria, and both screen_sleep and sueno_pantallas (2-sep-2026). The list
    has to be re-read before each article, and the pairs are declared in SAME_SUBJECT."""
    content = tmp_path / "content"
    first = pending_topics(content, "en")
    assert "hives" in first and "urticaria" in first  # both offered while nothing is published

    _publish_stub(content, "en", "one", "hives")
    assert "urticaria" not in pending_topics(content, "en"), (
        "same subject as the one just published"
    )
    assert "breastfeeding" in pending_topics(content, "en"), "a different subject must survive"


def test_a_french_guide_is_asked_for_and_checked_in_french(tmp_path: Path, monkeypatch):
    """The generator said "English if en else Spanish": French would have been requested in
    Spanish, and the language verifier would have demanded Spanish back (3-sep-2026)."""
    db = tmp_path / "i.db"
    build_index([_chunk("who_fr_measles#1", "la rougeole est une maladie très contagieuse")], db)
    monkeypatch.setitem(TOPIC_PLAN, "_fr", {"docs": ["who_fr_measles"], "query": "rougeole"})
    draft = (
        "TITLE: La rougeole chez l'enfant\n"
        "SUMMARY: Ce qu'il faut savoir et quand consulter.\n"
        "BODY:\n## Ce que c'est\nLa rougeole est une maladie très contagieuse [1].\n"
        "## Ce que vous pouvez faire à la maison\nDu repos et des liquides [1].\n"
        "## Quand consulter un médecin ou aller aux urgences\nEn cas de gêne respiratoire [1].\n"
        "## Questions fréquentes\nCombien de temps ? Quelques jours [1].\n"
    )
    a = generate_article(Index(db), FakeProvider(draft), "_fr", lang="fr")
    assert a.lang == "fr"
    assert "/fr/guides/" in a.public_url("https://pedibot.xyz")
    assert "## Sources" in a.markdown()  # French keeps the English word for this heading

    # a Spanish draft asked for in French must be refused, exactly as English/Spanish are
    spanish = (
        "TITLE: El sarampión\nSUMMARY: Qué es.\nBODY:\n## Qué es\nEl sarampión es contagioso [1].\n"
        "## Qué puedes hacer en casa\nReposo [1].\n"
        "## Cuándo acudir al médico o a urgencias\nSi cuesta respirar [1].\n"
        "## Preguntas frecuentes\n¿Cuánto dura? Unos días [1].\n"
    )
    with pytest.raises(ValueError, match="wrong_language"):
        generate_article(Index(db), FakeProvider(spanish), "_fr", lang="fr")


def test_a_draft_without_the_body_marker_is_still_usable():
    """The model sometimes goes straight from SUMMARY to the first heading and never writes the
    literal "BODY:". Throwing away a perfectly good article over a missing marker wasted a whole
    French batch (3-sep-2026); the first heading is an unambiguous start of the body."""
    text = (
        "TITLE: Mon bébé a le VRS, que faire ?\n\n"
        "SUMMARY: Le VRS est un virus courant qui peut devenir grave chez les bébés.\n\n"
        "## Ce que c'est\n\nLe VRS est un virus respiratoire [1].\n"
    )
    title, summary, body = parse_output(text)
    assert title.startswith("Mon bébé")
    assert summary.startswith("Le VRS")
    assert body.startswith("## Ce que c'est")


def test_a_draft_with_neither_marker_nor_heading_is_still_refused():
    with pytest.raises(ValueError, match="missing"):
        parse_output("I cannot help with that.")
