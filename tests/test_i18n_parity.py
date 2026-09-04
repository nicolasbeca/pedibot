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


def ternary(line: str) -> str | None:
    """The offending shape in one line of code, ignoring anything after a `//` comment.

    `lang === 'es' ? a : b` hands `b` to every language after the second, which is the bug
    this whole file exists for. Filtering a collection by `data.lang` is a different thing
    and stays allowed.
    """
    code = line.split("//")[0]
    m = re.search(r"(?<!\.)\blang\s*===\s*'\w+'\s*\?", code) or re.search(
        r"\bconst \w+ = lang === '\w+';", code
    )
    return m.group(0) if m else None


def test_no_component_decides_the_language_with_a_ternary() -> None:
    """`lang === 'es' ? a : b` is the shape of the bug: every other language gets `b`.

    Filtering a collection by `data.lang` is a different thing and stays allowed.
    """
    offenders = []
    for f in sorted(SITE.rglob("*.astro")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if ternary(line):
                offenders.append(f"{f.relative_to(SITE)}:{i}")
    assert not offenders, offenders


def test_the_ternary_guard_reads_code_and_not_prose() -> None:
    """A checker nobody has seen fire is not a checker — and this one used to fire at its own
    documentation. It matched the whole line, so a comment warning about the pattern tripped
    it, and the only way to document the rule was to avoid naming it.
    """
    assert ternary("const p = lang === 'en' ? '' : `/${lang}`;")
    assert ternary("  const isSpanish = lang === 'es';")
    assert not ternary("// never write lang === 'en' ? a : b — use langPrefix instead")
    assert not ternary("const p = langPrefix(lang); // and not lang === 'en' ? a : b")
    assert not ternary("const mine = all.filter((g) => g.data.lang === lang);")


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


def test_the_telegram_bot_speaks_every_language_the_engine_does() -> None:
    """`/lang` listed ("en","es","fr") by hand, and HELP was indexed with [...] rather than .get —
    so a user who set French and typed /help crashed the handler."""
    from pedibot.bot.answer import SUPPORTED_LANGS
    from pedibot.telegram_bot import HELP, LANG_SET

    assert set(SUPPORTED_LANGS) <= set(HELP), f"/help falta en {set(SUPPORTED_LANGS) - set(HELP)}"
    assert set(SUPPORTED_LANGS) <= set(LANG_SET)


def test_each_rss_feed_declares_its_own_language() -> None:
    """Cloning a language folder copied the German feed title onto Russian and Arabic: the
    strings are not the language code, so the clone's find-and-replace never touched them."""
    pages = SITE / "pages"
    for lang in langs():
        feed = (pages if lang == "en" else pages / lang) / "rss.xml.ts"
        text = feed.read_text(encoding="utf-8")
        # A regional tag is allowed and often better: a Brazilian feed should say pt-BR, not pt.
        # What must never happen is a feed declaring a DIFFERENT language, which is what the
        # cloned German feeds did to Russian and Arabic.
        declared = re.search(r"<language>([\w-]+)</language>", text)
        assert declared, f"{lang}: el feed no declara idioma"
        assert declared.group(1).split("-")[0] == lang, (
            f"{lang}: el feed declara {declared.group(1)}"
        )
        assert f"g.data.lang === '{lang}'" in text, f"{lang}: el feed lista otras guías"


# --- the home-kit page (4-sep-2026) -------------------------------------------------------------
# Key parity cannot see this one: an array with three items instead of five has exactly the same
# keys as one with five. A language quietly carrying two fewer items is the same failure as a
# missing translation, only harder to notice.


def kit_list(body: str, name: str) -> list[tuple[str, str, str]]:
    m = re.search(rf"\n      {name}: \[(.*?)\n      \]", body, re.S)
    assert m, f"no encuentro la lista {name}"
    return re.findall(r'\{ name: "(.*?)", what: "(.*?)", cite: "(.*?)" \}', m.group(1))


@pytest.mark.parametrize("name", ["have", "avoid"])
def test_the_home_kit_lists_the_same_number_of_things_in_every_language(name: str) -> None:
    counts = {lang: len(kit_list(block(lang), name)) for lang in langs()}
    assert len(set(counts.values())) == 1, f"la lista {name} no coincide por idioma: {counts}"
    assert next(iter(counts.values())) >= 4


def test_every_line_of_the_home_kit_names_its_source() -> None:
    """The page only exists because each item can be traced back to a published document. An item
    with no citation is a claim the site cannot back, which is the one thing it must not publish.
    """
    for lang in langs():
        body = block(lang)
        for name in ("have", "avoid"):
            for item, what, cite in kit_list(body, name):
                assert what.strip(), f"[{lang}] {item}: sin texto"
                assert "—" in cite and len(cite) > 12, f"[{lang}] {item}: sin fuente citada"


#: The pills that live inside <nav> in Base.astro. The bar is capped at the 1040px `.wrap`
#: column, and it shares that column with the logo, the support pill, the language menu and the
#: theme toggle — so the labels have perhaps sixty characters between them before the last one
#: gets cut in half.
NAV_PILLS = ["nav_dose", "nav_guides", "nav_kit", "nav_sources", "nav_vaccines",
             "nav_emergency_short"]
NAV_BUDGET = 66


def test_the_menu_labels_still_fit_in_the_bar() -> None:
    """German cut "Soll ich in die Notaufna…" off the end of the bar, and French was worse.

    The cause was not the number of pills but their wording: the emergency label was a whole
    question — 28 characters in German and French — where a nav label should be a noun. Nothing
    failed; the pill was simply sliced, and only in some languages, which is why it survived a
    redesign and two reviews. A budget makes the next long translation fail here instead of on
    someone's screen.
    """
    text = I18N.read_text(encoding="utf-8")
    over = {}
    for lang in langs():
        body = block(lang)
        total = 0
        for key in NAV_PILLS:
            m = re.search(rf"{key}: ['\"](.*?)['\"],", body)
            assert m, f"[{lang}] falta la etiqueta {key}"
            total += len(m.group(1))
        if total > NAV_BUDGET:
            over[lang] = total
    assert not over, (
        f"etiquetas del menú demasiado largas (presupuesto {NAV_BUDGET}): {over}. "
        "Acorta una: una pastilla de menú es un sustantivo, no una frase."
    )
    # exactamente una vez por idioma en el catálogo; el uso vive en Base.astro, otro fichero
    assert text.count("nav_emergency_short") == len(langs())


def test_the_full_question_survives_where_it_fits() -> None:
    """Shortening the pill must not lose the question: it still introduces the page in the footer
    and under the chat box, which is where a parent reads it as a question rather than a label."""
    base = (SITE / "layouts" / "Base.astro").read_text(encoding="utf-8")
    chat = (SITE / "components" / "Chat.astro").read_text(encoding="utf-8")
    assert "s.nav_emergency_short" in base, "la barra debe usar la etiqueta corta"
    assert "s.nav_emergency}" in base, "el pie debe conservar la pregunta completa"
    assert "s.nav_emergency}" in chat, "el aviso bajo el chat debe conservar la pregunta"


def test_no_edition_counts_the_languages_by_hand() -> None:
    """Every edition used to name the languages the site had when THAT edition was written.

    English, Spanish and French said "in English, Spanish and French" long after German, Russian
    and Arabic had shipped; German said four; Russian said five. Only Arabic was right, and only
    because it happened to be last. On a page whose entire argument is that this project does not
    state what it has not checked, that sentence was the worst thing on it.

    It is `{langs}` now, counted at build time from the guides that exist. This refuses the
    hand-written version coming back.
    """
    named = ("Spanish and French", "español y francés", "espagnol et en français",
             "Spanisch, Französisch", "испанском, французском", "والإسبانية والفرنسية")
    guilty = {}
    for lang in langs():
        body = block(lang)
        hits = [n for n in named if n in body]
        if hits:
            guilty[lang] = hits
    assert not guilty, f"idiomas enumerados a mano en vez de contados: {guilty}"
    for lang in langs():
        assert "{langs}" in block(lang), f"[{lang}] no usa el marcador {{langs}}"
