"""No guide sends a parent to a phone number they cannot dial (3-sep-2026).

The rule was already enforced on new guides by the article prompt: name the organisation as the
source, never forward the reader to its phone line. The guides written before that rule kept the
NHS's numbers, and every translation carried them across — so the Spanish meningitis guide told a
parent in Madrid to dial 999, the Russian fever guide said "call an ambulance (999)", and the
Arabic one gave 999 and 111 for meningitis-grade red flags. All of them are dead numbers outside
the UK, printed in the paragraph a frightened parent reads first.

A prompt rule only binds what is written after it. This binds what is already published.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "web" / "content"

# Numbers and national brands a reader in another country cannot use. 112 is deliberately absent:
# it is the shared European number, and where a guide names it, it names its own country too.
FORBIDDEN = re.compile(
    r"\b999\b|\b911\b|NHS\s*111|(?<![\d.,])111(?![\d.,])|\bA&E\b|GP surgery|"
    r"1-800-222-1222|91\s?562\s?04\s?20"
)


def _prose(path: pathlib.Path) -> list[tuple[int, str]]:
    """Body text only: the sources block quotes documents verbatim and the disclaimer is ours."""
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith('- "[') or stripped.startswith("*"):
            continue
        out.append((i, line))
    return out


def test_no_guide_prints_a_number_the_reader_cannot_dial() -> None:
    offenders = []
    for lang_dir in sorted(CONTENT.iterdir()):
        if not lang_dir.is_dir():
            continue
        for f in sorted(lang_dir.glob("*.md")):
            for i, line in _prose(f):
                m = FORBIDDEN.search(line)
                if m:
                    offenders.append(f"{lang_dir.name}/{f.name}:{i} — {m.group(0)}")
    assert not offenders, offenders[:12]


def test_every_guide_still_carries_its_disclaimer() -> None:
    """The numbers were removed from the prose because the disclaimer carries the instruction.
    If a guide lost its disclaimer, the removal would leave nothing in its place."""
    missing = []
    for lang_dir in sorted(CONTENT.iterdir()):
        if not lang_dir.is_dir():
            continue
        for f in sorted(lang_dir.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            if not any(line.strip().startswith("*") for line in text.splitlines()[-6:]):
                missing.append(f"{lang_dir.name}/{f.name}")
    assert not missing, missing[:10]


def test_the_faq_heading_is_known_in_every_language() -> None:
    """A heading missing from guides.ts costs that language its FAQ structured data, silently —
    it cost French that in July and German, Russian and Arabic until this was written."""
    site = ROOT / "web" / "site" / "src"
    headings = (site / "guides.ts").read_text(encoding="utf-8")
    block = headings[headings.index("FAQ_HEADINGS = [") : headings.index("];", headings.index("FAQ_HEADINGS = ["))]
    langs = re.findall(
        r"'(\w+)'",
        re.search(
            r"export const LANGS: Lang\[\] = \[(.*?)\]", (site / "i18n.ts").read_text(encoding="utf-8")
        ).group(1),
    )
    # one alternative per language, and each language's guides must actually match one of them
    assert len(re.findall(r"'", block)) // 2 >= len(langs), block
    pattern = re.compile(
        r"^##\s+(" + "|".join(re.findall(r"'([^']+)'", block)) + r")\s*$", re.M | re.I
    )
    for lang in langs:
        guides = sorted((CONTENT / lang).glob("*.md"))
        if not guides:
            continue
        hit = sum(1 for g in guides if pattern.search(g.read_text(encoding="utf-8")))
        assert hit > len(guides) // 2, f"{lang}: solo {hit}/{len(guides)} guías con bloque de preguntas"


def test_a_citation_never_names_a_section_the_document_lacks() -> None:
    """"Introducción" is the label the chunker gives the text before the first heading — our
    word, not the document's. It travelled into 119 citations of English and Russian documents,
    sending anyone who checked us to a section that is not there."""
    offenders = []
    for lang_dir in sorted(CONTENT.iterdir()):
        if not lang_dir.is_dir():
            continue
        for f in sorted(lang_dir.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            if re.search(r'(section|sección|Abschnitt|раздел|قسم) \\"Introducci[oó]n', text):
                offenders.append(f"{lang_dir.name}/{f.name}")
    assert not offenders, offenders[:10]


def test_the_citation_scaffolding_is_in_the_guide_s_own_language() -> None:
    """The quoted title and section stay in the document's language — that is what makes the
    citation checkable. The two words joining them are ours, and they were English everywhere."""
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from pedibot.bot.strings import CITATION_WORDS

    langs = {d.name for d in CONTENT.iterdir() if d.is_dir()}
    assert langs <= set(CITATION_WORDS), f"faltan palabras de cita para {langs - set(CITATION_WORDS)}"

    for lang in sorted(langs - {"en", "fr"}):  # fr uses the same two words as English
        word = CITATION_WORDS[lang][0]
        files = sorted((CONTENT / lang).glob("*.md"))
        english = [f.name for f in files if ', section \\"' in f.read_text(encoding="utf-8")]
        assert not english, f"{lang}: {len(english)} guías citan con «section» en inglés"
        localised = sum(1 for f in files if f', {word} \\"' in f.read_text(encoding="utf-8"))
        assert localised > 0, f"{lang}: ninguna guía usa «{word}»"
