r"""A title has to survive becoming a filename, in every script (5-sep-2026).

`slug()` folds accents and transliterates Cyrillic and Arabic; anything it does not know is
stripped, and a title left with nothing falls back to the literal string "s". The comment above
that table has said since it was written what the consequence is — "two guides in the same
language end up sharing one filename, the second overwriting the first" — and Devanagari was
never added to it.

So every Hindi guide was written to web/content/hi/s.md. Fifty-five generations, each one paid
for, each one deleting the last, and the run was still going when it was stopped. Nothing failed:
the file was written, the log said ✓, and only counting the files showed it.

The test is per script rather than per language: what breaks is the writing system, and the next
one to arrive (Bengali, Thai, Chinese) will break the same way.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.ingest.pipeline import slug

# Real guide titles, one pair per script — two DIFFERENT guides that must not collide.
TITLES: dict[str, tuple[str, str]] = {
    "latin": ("Fever in children: what to do at home", "Head lice: what to do"),
    "cyrillic": ("Температура у ребёнка: что делать дома", "Вши у ребёнка: что делать"),
    "arabic": ("الحمى عند الأطفال: ماذا تفعل في البيت", "قمل الرأس: ماذا تفعل"),
    "devanagari": ("बच्चों में बुखार: घर पर क्या करें", "सिर की जूँ: क्या करें"),
}


@pytest.mark.parametrize("script", sorted(TITLES))
def test_a_title_keeps_something_of_itself(script: str) -> None:
    for title in TITLES[script]:
        s = slug(title, max_len=70)
        assert s != "s", f"[{script}] «{title}» se queda sin slug"
        assert len(s) > 8, f"[{script}] «{title}» → «{s}», demasiado poco"
        assert s == s.lower() and all(c.isalnum() or c == "_" for c in s), s


@pytest.mark.parametrize("script", sorted(TITLES))
def test_two_guides_never_share_a_filename(script: str) -> None:
    a, b = (slug(t, max_len=70) for t in TITLES[script])
    assert a != b, f"[{script}] dos guías distintas comparten «{a}»"


def test_hindi_reads_the_way_it_sounds() -> None:
    """A consonant carries an inherent "a" that a vowel sign or a virama removes, and Hindi drops
    it at the end of a word. Character by character बुखार would come out "bakhaara"."""
    assert slug("बुखार", max_len=70) == "bukhaar"
    assert slug("सिर की जूँ", max_len=70) == "sir_kee_joon"
    assert slug("क्या करें", max_len=70) == "kyaa_karen"


def test_the_writer_refuses_to_overwrite_another_topic(tmp_path: pathlib.Path) -> None:
    """The guard that turns a slug bug into a stopped run instead of a quiet loss."""
    from pedibot.publish.articles import write_article

    class Fake:
        lang = "hi"
        slug = "s"
        topic = "fever"

        def markdown(self) -> str:
            return f"---\nlang: hi\ntopic: {self.topic}\n---\n\ncuerpo\n"

        def social_text(self, site_url: str) -> str:
            return "texto"

    a = Fake()
    write_article(a, tmp_path / "content", tmp_path / "queue", "https://pedibot.xyz")
    write_article(a, tmp_path / "content", tmp_path / "queue", "https://pedibot.xyz")  # mismo tema

    a.topic = "head_lice"
    with pytest.raises(ValueError, match="colisión de slug"):
        write_article(a, tmp_path / "content", tmp_path / "queue", "https://pedibot.xyz")
