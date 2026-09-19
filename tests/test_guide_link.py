"""An answer offers the guide written from the sources it used (5-sep-2026).

An answer is four sentences; the guide on the same subject is eight hundred words with the same
documents at the bottom. Nothing joined them, so a parent could ask about fever, get an answer,
and never learn the site has a whole page about fever.

The match is on DOCUMENTS, not on words in the question. That is the part worth locking: keyword
matching would put the vaccines guide under a question about a rash after a vaccine, or the rash
guide, depending on which word won — and a wrong guide under a right answer makes the whole page
look like it is guessing.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.guides import GuideIndex, GuideLink

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "web" / "content"


def write(dir_: pathlib.Path, lang: str, slug: str, topic: str, title: str) -> None:
    d = dir_ / lang
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.md").write_text(
        f'---\ntitle: "{title}"\ndescription: "x"\nlang: {lang}\ntopic: {topic}\n'
        f"date: 2026-09-05\nsources: []\ndraft: false\n---\n\ncuerpo\n",
        encoding="utf-8",
    )


def test_the_url_follows_where_each_language_is_served() -> None:
    assert GuideLink("fiebre", "fever", "Fever", "en").url == "/guides/fever"
    assert GuideLink("fiebre", "fiebre", "Fiebre", "es").url == "/es/guides/fiebre"


def test_it_picks_the_guide_built_from_the_cited_documents(tmp_path: pathlib.Path) -> None:
    write(tmp_path, "es", "fiebre", "fiebre", "¿Qué hago si mi hijo tiene fiebre?")
    write(tmp_path, "es", "laringitis", "laringitis", "Tos perruna: qué hacer")
    gi = GuideIndex(tmp_path)

    g = gi.best_for(["seup_laringitis#2"], "es", "tos de perro por la noche")
    assert g is not None and g.topic == "laringitis"

    g = gi.best_for(["seup_fiebre#1", "seup_acudir_urgencias#4"], "es", "tiene 39 de fiebre")
    assert g is not None and g.topic == "fiebre"


def test_a_passing_mention_does_not_win(tmp_path: pathlib.Path) -> None:
    """A Russian answer about fever quoted the fever sheet twice and the heat-stroke sheet once,
    for its one "when to consult" line — and the first version of this offered the reader the
    guide to heat stroke, because both had "a document in common". What the answer is ABOUT is
    the document it drew most from."""
    write(tmp_path, "ru", "fiebre", "fiebre", "Что делать, если у ребёнка температура?")
    write(tmp_path, "ru", "calor", "golpe_calor", "Тепловой удар у ребёнка: что делать?")
    gi = GuideIndex(tmp_path)

    g = gi.best_for(["seup_fiebre#1", "seup_fiebre#2", "seup_golpe_calor#3"], "ru", "температура")
    assert g is not None and g.topic == "fiebre"

    # and the reverse still works: an answer that is really about heat stroke
    g = gi.best_for(["seup_golpe_calor#1", "seup_golpe_calor#2"], "ru", "весь день на солнце")
    assert g is not None and g.topic == "golpe_calor"


def test_no_overlap_means_no_link(tmp_path: pathlib.Path) -> None:
    """A guide on a merely related subject is not worth the click on a health site."""
    write(tmp_path, "es", "fiebre", "fiebre", "Fiebre")
    gi = GuideIndex(tmp_path)
    assert gi.best_for(["un_documento_que_nadie_usa#1"], "es", "hola") is None
    assert gi.best_for([], "es", "hola") is None
    assert gi.best_for(["seup_fiebre#1"], "de", "fieber") is None  # sin guía en ese idioma


def test_a_draft_is_never_offered(tmp_path: pathlib.Path) -> None:
    write(tmp_path, "es", "fiebre", "fiebre", "Fiebre")
    f = tmp_path / "es" / "fiebre.md"
    f.write_text(
        f.read_text(encoding="utf-8").replace("draft: false", "draft: true"), encoding="utf-8"
    )
    assert GuideIndex(tmp_path).best_for(["seup_fiebre#1"], "es") is None


def test_a_missing_content_folder_is_not_an_error(tmp_path: pathlib.Path) -> None:
    """The engine must start on a machine that has never generated a guide."""
    gi = GuideIndex(tmp_path / "no-existe")
    assert len(gi) == 0
    assert gi.best_for(["seup_fiebre#1"], "es") is None


@pytest.mark.skipif(not CONTENT.is_dir(), reason="no hay guías publicadas")
@pytest.mark.parametrize(
    "lang,chunk,expect_topic",
    [
        ("es", "seup_fiebre#1", "fiebre"),
        ("en", "seup_bronquiolitis#1", "bronquiolitis"),
        ("pt", "seup_tce#1", "traumatismo_craneal"),
    ],
)
def test_the_published_corpus_answers_the_obvious_cases(
    lang: str, chunk: str, expect_topic: str
) -> None:
    g = GuideIndex(CONTENT).best_for([chunk], lang)
    assert g is not None, f"[{lang}] {chunk} no encuentra guía"
    assert g.topic == expect_topic, f"[{lang}] devuelve «{g.topic}»"
    assert g.url.startswith("/guides/" if lang == "en" else f"/{lang}/guides/")
