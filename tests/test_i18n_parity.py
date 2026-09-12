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
    assert not any(missing.values()), (
        f"claves que faltan por idioma: { {k: v for k, v in missing.items() if v} }"
    )
    assert len(common) > 100


def test_lang_names_covers_every_language() -> None:
    m = re.search(
        r"LANG_NAMES: Record<Lang, string> = \{(.*?)\};", I18N.read_text(encoding="utf-8")
    )
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

    ru = [
        slug("Вши у детей: что действительно помогает"),
        slug("Что делать при простуде у ребёнка"),
    ]
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
    block = text[text.index("const FORM_WORD") :]
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
NAV_PILLS = [
    "nav_dose",
    "nav_guides",
    "nav_kit",
    "nav_sources",
    "nav_vaccines",
    "nav_emergency_short",
]
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
    named = (
        "Spanish and French",
        "español y francés",
        "espagnol et en français",
        "Spanisch, Französisch",
        "испанском, французском",
        "والإسبانية والفرنسية",
    )
    guilty = {}
    for lang in langs():
        body = block(lang)
        hits = [n for n in named if n in body]
        if hits:
            guilty[lang] = hits
    assert not guilty, f"idiomas enumerados a mano en vez de contados: {guilty}"
    for lang in langs():
        assert "{langs}" in block(lang), f"[{lang}] no usa el marcador {{langs}}"


def test_every_language_table_in_the_engine_holds_the_same_shape() -> None:
    """A positional patch across seven similar tables drifted by one and put the clarify buttons
    into ASK_AGE, the age question into the emergency header, and nothing into the mental-health
    one. mypy caught it, which is what mypy is for — but a table of strings with one list in it is
    worth refusing here too, where the message says which table.
    """
    from pedibot.bot.answer import (
        AGE_REFINES,
        ASK_AGE,
        CLARIFY,
        CLARIFY_OPTIONS,
        DISCLAIMER,
        NO_SOURCE,
        SUPPORTED_LANGS,
    )

    for name, table, kind in (
        ("DISCLAIMER", DISCLAIMER, str),
        ("NO_SOURCE", NO_SOURCE, str),
        ("CLARIFY", CLARIFY, str),
        ("ASK_AGE", ASK_AGE, str),
        ("AGE_REFINES", AGE_REFINES, str),
        ("CLARIFY_OPTIONS", CLARIFY_OPTIONS, list),
    ):
        assert set(table) >= set(SUPPORTED_LANGS), (
            f"{name}: faltan {set(SUPPORTED_LANGS) - set(table)}"
        )
        for lang, value in table.items():
            assert isinstance(value, kind), (
                f"{name}[{lang}] es {type(value).__name__}, no {kind.__name__}"
            )
        if kind is list:
            sizes = {len(v) for v in table.values()}
            assert len(sizes) == 1, f"{name}: listas de distinta longitud {sizes}"


def test_the_three_emergency_headers_are_three_different_sentences() -> None:
    """They are built in three separate dicts a few lines apart, which is exactly how one ended up
    carrying another's text — twice — without anything failing."""
    import re

    src = (ROOT / "src" / "pedibot" / "bot" / "answer.py").read_text(encoding="utf-8")
    blocks = re.findall(r"heads = \{(.*?)\n        \}", src, re.S)
    assert len(blocks) == 3, f"esperaba tres cabeceras, hay {len(blocks)}"
    per_lang: dict[str, list[str]] = {}
    for block in blocks:
        for lang, text in re.findall(r'"(\w\w)": f?"([^"]+)"', block):
            per_lang.setdefault(lang, []).append(text)
    for lang, texts in per_lang.items():
        assert len(texts) == 3, f"[{lang}] sólo aparece en {len(texts)} de las tres cabeceras"
        assert len(set(texts)) == 3, f"[{lang}] repite texto entre cabeceras: {texts}"


def paths(body: str) -> set[str]:
    """Every key with the object it lives in — `donate.on_network`, not `on_network`.

    `keys()` flattens, which is what let a value exist and still render as nothing: Russian and
    Arabic had `on_network` one level up, outside `donate`, so `t(lang).donate.on_network` was
    undefined and the donation cards drew two empty lines. The names all matched.
    """
    stripped = re.sub(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", "''", body)
    out: set[str] = set()
    stack: list[str] = []
    i = 0
    while i < len(stripped):
        m = re.compile(r"([a-z_][a-z_0-9]*)\s*:\s*").match(stripped, i)
        if m and (i == 0 or stripped[i - 1] in "{,\n \t"):
            name = m.group(1)
            j = m.end()
            if j < len(stripped) and stripped[j] == "{":
                stack.append(name)
                i = j + 1
                continue
            out.add(".".join([*stack, name]))
            i = j
            continue
        if stripped[i] == "{":
            stack.append("[]")  # an object inside an array: its keys are positional, not named
        elif stripped[i] == "}" and stack:
            stack.pop()
        i += 1
    return out


def test_every_key_lives_in_the_same_object_in_every_language() -> None:
    per_lang = {lang: paths(block(lang)) for lang in langs()}
    everything = set.union(*per_lang.values())
    misplaced = {lang: sorted(everything - p) for lang, p in per_lang.items()}
    assert not any(misplaced.values()), (
        "claves que faltan o están anidadas en otro sitio: "
        f"{ {k: v for k, v in misplaced.items() if v} }"
    )


def test_the_path_check_catches_a_key_moved_out_of_its_object() -> None:
    """A checker nobody has seen fire is not a checker, and this one exists because the flat
    version passed while two pages rendered blank."""
    good = "donate: {\n  h: 'x',\n  on_network: 'y',\n},\n"
    bad = "donate: {\n  h: 'x',\n},\non_network: 'y',\n"
    assert "donate.on_network" in paths(good)
    assert "donate.on_network" not in paths(bad)
    assert "on_network" in paths(bad)


# --- y los YAML de config, que hasta el 7-sep-2026 no miraba nadie ------------------------------
#
# Las comprobaciones de arriba cubren el i18n de la web y dos ficheros exportados. Los YAML de
# `config/` —de donde sale todo lo demás— no los miraba ninguna. En un solo día aparecieron dos
# huecos ahí: el catálogo de fármacos hablaba seis idiomas de ocho (a portugués e hindi les
# llegaba en inglés el aviso «no en menores de 3 meses ni de 5 kg») y la frase por defecto del
# número de emergencias en hindi era la única sin ninguna cifra.
#
# Esto los busca todos a la vez, con la misma regla que la de arriba: **un nodo que se traduce a
# sí mismo tiene que traducirse entero**.


def _huecos(nodo: object, quiere: set[str], ruta: str = "") -> list[str]:
    fuera: list[str] = []
    if isinstance(nodo, dict):
        claves = set(nodo)
        if quiere & claves and not quiere <= claves:
            fuera.append(f"{ruta}: faltan {sorted(quiere - claves)}")
        for k, v in nodo.items():
            fuera += _huecos(v, quiere, f"{ruta}/{k}")
    elif isinstance(nodo, list):
        for i, v in enumerate(nodo):
            fuera += _huecos(v, quiere, f"{ruta}[{i}]")
    return fuera


#: `synonyms.yaml` queda fuera del barrido, y no por comodidad: su nivel superior no es una cosa
#: traducida a ocho idiomas, es un REGISTRO de tablas. `es`, `en`, `fr` y `de` son tablas
#: coloquial→prospecto del propio idioma, y `ru_es`, `ar_en`, `pt_es`, `hi_en`… son las CRUZADAS,
#: que es como se resuelven los cuatro idiomas cuyo corpus está en español e inglés. Lo que hay
#: que comprobar ahí es otra cosa, y está justo debajo.
FUERA_DEL_BARRIDO = {"synonyms.yaml"}


def _configs() -> list[pathlib.Path]:
    return sorted(f for f in (ROOT / "config").glob("*.yaml") if f.name not in FUERA_DEL_BARRIDO)


def test_every_language_has_somewhere_to_expand_a_query_from() -> None:
    """Lo que de verdad importa de synonyms.yaml.

    El buscador expande la consulta con la tabla del idioma o con una cruzada hacia el español y
    el inglés, que es donde está el corpus. Un idioma sin ninguna de las dos busca con las
    palabras crudas del padre contra un corpus escrito en otra lengua — y no falla, simplemente
    encuentra menos.
    """
    from pedibot.bot.retrieval import Synonyms

    syn = Synonyms(ROOT / "config" / "synonyms.yaml", ROOT / "config" / "drugs.yaml")
    sin_tabla = [lang for lang in langs() if not syn.knows(lang)]
    assert not sin_tabla, f"idiomas sin ninguna tabla de sinónimos: {sin_tabla}"


def test_there_are_configs_to_check() -> None:
    """El candado del candado."""
    assert len(_configs()) >= 5


@pytest.mark.parametrize("fichero", _configs(), ids=lambda f: f.name)
def test_every_config_translates_itself_completely(fichero: pathlib.Path) -> None:
    import yaml

    datos = yaml.safe_load(fichero.read_text(encoding="utf-8"))
    faltan = _huecos(datos, set(langs()))
    assert not faltan, f"{fichero.name} tiene traducciones a medias:\n  " + "\n  ".join(faltan[:8])


def test_the_shared_answer_page_is_written_in_every_language() -> None:
    """La página de `/a/{token}` es HTML escrito a mano dentro de `api.py`, fuera de Astro y
    fuera del alcance de los candados de arriba.

    Estaba en dos idiomas —`"…" if lang != "es" else "…"`, la forma exacta que este fichero
    prohíbe en la web— así que seis de los ocho recibían la rama inglesa: un padre alemán
    compartía su respuesta en alemán envuelta en un título y una nota legal en inglés. Y el
    árabe salía maquetado de izquierda a derecha, que la web sí sabe hacer desde el primer día.
    """
    import re as _re

    from pedibot.bot.answer import SUPPORTED_LANGS

    fuente = (ROOT / "src" / "pedibot" / "api.py").read_text(encoding="utf-8")
    bloque = _re.search(r"SHARED = \{(.*?)\n    \}", fuente, _re.S)
    assert bloque, "no encuentro la tabla SHARED en api.py"
    escritos = set(_re.findall(r'"(\w{2})": \(', bloque.group(1)))
    faltan = sorted(set(SUPPORTED_LANGS) - escritos)
    assert not faltan, f"la página compartida no está escrita en: {faltan}"
    assert 'dir="{direction}"' in fuente, "la página compartida no declara dirección de escritura"


def test_the_chat_tells_the_three_failures_apart() -> None:
    """«Espera un poco», «ahora no puedo» y «se nos ha roto algo» piden cosas distintas del
    padre, y las tres se contestaban con la tercera (9-sep-2026).

    Un 429 es un límite que ponemos nosotros, no una avería: decirle «hemos fallado» lo deja
    reintentando, que es justo lo que alarga el bloqueo. Y en la rama de la foto había un
    ternario con las DOS ramas iguales —`r.status === 503 ? S.err_server : S.err_server`—,
    señal de que alguien quiso distinguir el 503 y no terminó.
    """
    chat = (ROOT / "web" / "site" / "src" / "components" / "Chat.astro").read_text(
        encoding="utf-8"
    )
    assert "S.err_server : S.err_server" not in chat, "vuelve a haber un ternario con dos ramas iguales"
    assert chat.count("S.err_busy") >= 2, "el límite de peticiones no se distingue"
    assert chat.count("S.err_unavailable") >= 2, "el «ahora no puedo» no se distingue"


def test_every_error_message_is_written_in_every_language() -> None:
    """Los cuatro estados de fallo, en los ocho. Son los textos que menos se releen y los que
    más falta hacen: los tres llevan al lado el «si es urgente, llama a urgencias»."""
    import re as _re

    texto = I18N.read_text(encoding="utf-8")
    n = len(langs())
    for clave in ("err_server", "err_net", "err_busy", "err_unavailable"):
        encontrados = _re.findall(rf"^\s*{clave}: ", texto, _re.M)
        assert len(encontrados) == n, f"{clave} está en {len(encontrados)} idiomas de {n}"
