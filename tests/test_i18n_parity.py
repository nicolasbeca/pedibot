"""The web layer must know about exactly one list of languages (3-sep-2026).

French shipped with six places still written for two languages, and none of them failed: a
missing translation renders as an empty string, and `lang === 'es' ? a : b` quietly hands the
English branch to every other language. These tests are the guard, so the fourth language is a
block of data instead of another hunt.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "web" / "site" / "src"
I18N = SITE / "i18n.ts"


def langs() -> list[str]:
    m = re.search(r"export const LANGS: Lang\[\] = \[(.*?)\];", I18N.read_text(encoding="utf-8"))
    assert m, "no encuentro LANGS en i18n.ts"
    return re.findall(r"'(\w+)'", m.group(1))


def block(lang: str) -> str:
    """The body of one language table, matched by brace depth rather than by indentation."""
    text = I18N.read_text(encoding="utf-8")
    start = text.index(f"\n  {lang}: {{") + len(f"\n  {lang}: {{")
    depth, i = 1, start
    while depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[start : i - 1]


def keys(body: str) -> set[str]:
    """Every key of the table, including the keys inside its nested objects.

    Strings are removed first so that a colon inside a sentence is not read as a key.
    """
    stripped = re.sub(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", "''", body)
    return set(re.findall(r"(?:^|[{,\s])([a-z_][a-z_0-9]*)\s*:", stripped))


def test_the_three_tables_carry_the_same_keys() -> None:
    per_lang = {lang: keys(block(lang)) for lang in langs()}
    common = set.intersection(*per_lang.values())
    missing = {lang: sorted(set.union(*per_lang.values()) - ks) for lang, ks in per_lang.items()}
    assert not any(missing.values()), f"claves que faltan por idioma: { {k: v for k, v in missing.items() if v} }"
    assert len(common) > 100


def test_lang_names_covers_every_language() -> None:
    m = re.search(r"LANG_NAMES: Record<Lang, string> = \{(.*?)\};", I18N.read_text(encoding="utf-8"))
    assert m
    assert set(re.findall(r"(\w+):", m.group(1))) == set(langs())


def test_the_content_schema_accepts_every_language() -> None:
    """A guide whose language is missing here fails the whole build, not just its own page."""
    text = (SITE / "content.config.ts").read_text(encoding="utf-8")
    m = re.search(r"lang: z\.enum\(\[(.*?)\]\)", text)
    assert m
    assert set(re.findall(r"'(\w+)'", m.group(1))) == set(langs())


@pytest.mark.parametrize("name", ["checklist.json", "vaccines.json"])
def test_data_files_carry_every_language(name: str) -> None:
    """The warning-signs list rendered 34 empty bullets in French because of exactly this."""
    data = json.loads((SITE / "data" / name).read_text(encoding="utf-8"))
    want = set(langs())

    def walk(node: object, path: str = "") -> list[str]:
        gaps = []
        if isinstance(node, dict):
            if want & set(node):  # a node that translates itself must translate itself fully
                if not want <= set(node):
                    gaps.append(f"{path}: faltan {sorted(want - set(node))}")
            for k, v in node.items():
                gaps += walk(v, f"{path}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                gaps += walk(v, f"{path}[{i}]")
        return gaps

    assert not walk(data), walk(data)[:6]


def test_no_component_decides_the_language_with_a_ternary() -> None:
    """`lang === 'es' ? a : b` is the shape of the bug: every other language gets `b`.

    Filtering a collection by `data.lang` is a different thing and stays allowed.
    """
    offenders = []
    for f in sorted(SITE.rglob("*.astro")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\blang\s*===\s*'\w+'\s*\?", line) or re.search(r"\bconst \w+ = lang === '\w+';", line):
                offenders.append(f"{f.relative_to(SITE)}:{i}")
    assert not offenders, offenders


def test_the_tool_strings_carry_the_same_keys() -> None:
    """Same guard on the engine side: dose, rehydration, vaccines and the photo check."""
    from pedibot.bot.strings import STRINGS

    shapes = {lang: set(table) for lang, table in STRINGS.items()}
    assert len(set(map(frozenset, shapes.values()))) == 1, shapes
    assert set(STRINGS) == set(langs()), f"idiomas del motor {set(STRINGS)} vs web {set(langs())}"
    warn = {lang: set(table["dose_warn"]) for lang, table in STRINGS.items()}
    assert len(set(map(frozenset, warn.values()))) == 1, warn


def test_the_model_is_told_the_right_language() -> None:
    """The mapping the model is given used to be written inline in two places, and both times a
    new language fell back to English: French guides were requested as "Spanish", and a German
    question was answered in English."""
    from pedibot.bot.strings import LANGUAGE_NAME, STRINGS

    assert set(LANGUAGE_NAME) == set(STRINGS)
    src = (ROOT / "src" / "pedibot").rglob("*.py")
    inline = [
        f"{f.relative_to(ROOT)}"
        for f in src
        if f.name != "strings.py" and '"es": "Spanish"' in f.read_text(encoding="utf-8")
    ]
    assert not inline, f"la tabla de idiomas vuelve a estar escrita a mano en {inline}"


def test_slugs_survive_a_non_latin_script() -> None:
    """A Cyrillic title used to collapse to the fallback "s", so the second Russian guide
    overwrote the first — same filename, no error, one guide gone."""
    from pedibot.ingest.pipeline import slug

    ru = [slug("Вши у детей: что действительно помогает"), slug("Что делать при простуде у ребёнка")]
    assert all(len(s) > 10 for s in ru), ru
    assert len(set(ru)) == 2, ru
    ar = slug("ما يجب فعله عند ارتفاع حرارة الطفل")
    assert len(ar) > 10, ar
    # and the Latin languages are unchanged
    assert slug("¿Qué hago si mi hijo tiene fiebre?") == "que_hago_si_mi_hijo_tiene_fiebre"


def test_every_language_names_the_dosage_forms() -> None:
    """The dose table headers are the strength printed on the bottle, and the first word of each
    is the form. A language missing from that map showed "gotas 100 mg/ml" on the Russian page."""
    text = (SITE / "dosepages.ts").read_text(encoding="utf-8")
    block = text[text.index("const FORM_WORD"):]
    block = block[: block.index("};")]
    have = set(re.findall(r"^  (\w+):\s*\{", block, re.M))
    # Spanish needs no entry: the keys of the map are the Spanish words themselves, because the
    # drug catalogue is written in Spanish and those strings are what a presentation is called.
    want = set(langs()) - {"es"}
    assert want <= have, f"faltan formas farmacéuticas en {want - have}"


def test_the_api_accepts_every_language_the_engine_speaks() -> None:
    """It was typed as "^(es|en|fr)$", so the live German and Russian pages — which send their
    language explicitly — got a 422 for every question asked. The sites were up; the chat was not."""
    import re as _re

    from pedibot.api import _LANG_PATTERN
    from pedibot.bot.answer import SUPPORTED_LANGS

    for lang in SUPPORTED_LANGS:
        assert _re.fullmatch(_LANG_PATTERN, lang), f"la API rechazaría lang={lang}"
    assert not _re.fullmatch(_LANG_PATTERN, "xx")
