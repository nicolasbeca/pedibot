r"""Each guide template must serve its own language (4-sep-2026).

There is one `[...slug].astro` per language and they are made by copying. The pieces that name a
language are spelled four different ways, and a copy only rewrites what whoever made it happened
to recognise:

    g.data.lang === 'es'          which guides exist at all
    g.id.replace(/^es\//, '')     the slug strip, with an escaped slash
    const family = ... 'es'       the pool "related guides" is drawn from
    others['xx']                  one block per sibling language

Every one of those failing is silent — the page builds, renders, and is simply somebody else's.
The Portuguese clone shipped sixty `/pt/guides/<spanish-slug>` pages full of Spanish before this
existed, and the German, Russian and Arabic pages carried a French heading for weeks.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGES = ROOT / "web" / "site" / "src" / "pages"


def _langs() -> tuple[str, ...]:
    """Read from i18n.ts, never typed here: a hand-written list silently exempts the language
    that was just added, which is the one most likely to be a broken copy of another."""
    m = re.search(
        r"export const LANGS: Lang\[\] = \[(.*?)\];",
        (ROOT / "web" / "site" / "src" / "i18n.ts").read_text(encoding="utf-8"),
    )
    assert m, "no encuentro LANGS en i18n.ts"
    return tuple(re.findall(r"'(\w+)'", m.group(1)))


LANGS = _langs()


def template(lang: str) -> str:
    rel = "guides/[...slug].astro" if lang == "en" else f"{lang}/guides/[...slug].astro"
    p = PAGES / rel
    assert p.exists(), f"falta {rel}"
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("lang", LANGS)
def test_the_template_lists_guides_of_its_own_language(lang: str) -> None:
    m = re.search(r"getCollection\('guides', g => g\.data\.lang === '(\w+)'", template(lang))
    assert m, f"[{lang}] no encuentro el filtro de getStaticPaths"
    assert m.group(1) == lang, f"[{lang}] sirve guías de '{m.group(1)}'"


@pytest.mark.parametrize("lang", LANGS)
def test_the_template_strips_its_own_slug_prefix(lang: str) -> None:
    r"""`g.id` and `r.id` are guides of THIS page; only `twins[0].id` belongs to another language.
    Portuguese stripped `/^es\//` from all four of its own links and still passed the old check,
    which only asked whether `pt` appeared somewhere — so sixty guides linked to /pt/guides/pt/…
    """
    mine = re.findall(r"\b[gr]\.id\.replace\(/\^(\w+)\\/", template(lang))
    assert mine, f"[{lang}] no encuentro ningún recorte de prefijo propio"
    assert set(mine) == {lang}, f"[{lang}] recorta {sorted(set(mine) - {lang})} en sus propios enlaces"


@pytest.mark.parametrize("lang", LANGS)
def test_the_ask_button_goes_to_its_own_edition(lang: str) -> None:
    r"""It read `/es?q=…` in every language but English: a German reader who finished a German
    guide and pressed the button landed on the Spanish site with a German question typed in."""
    m = re.search(r"href=\{`(/\w*)\?q=\$\{encodeURIComponent\(g\.data\.title\)\}`\}", template(lang))
    assert m, f"[{lang}] no encuentro el botón de preguntar"
    assert m.group(1) == ("/" if lang == "en" else f"/{lang}"), (
        f"[{lang}] el botón lleva a '{m.group(1)}'"
    )


@pytest.mark.parametrize("lang", LANGS)
def test_related_guides_come_from_the_same_language(lang: str) -> None:
    m = re.search(
        r"const family = await getCollection\('guides', x => x\.data\.lang === '(\w+)'",
        template(lang),
    )
    assert m, f"[{lang}] no encuentro `family`"
    assert m.group(1) == lang, f"[{lang}] las relacionadas salen de '{m.group(1)}'"


@pytest.mark.parametrize("lang", LANGS)
def test_the_template_knows_every_sibling_language(lang: str) -> None:
    """A language that nobody lists gets no alternate link from anywhere: it exists and cannot be
    reached from its own translations."""
    others = set(re.findall(r"others\['(\w+)'\]", template(lang)))
    assert others == set(LANGS) - {lang}, (
        f"[{lang}] hermanos: faltan {sorted(set(LANGS) - {lang} - others)}, "
        f"sobran {sorted(others - set(LANGS))}"
    )


@pytest.mark.parametrize("lang", LANGS)
def test_no_heading_is_typed_into_the_template(lang: str) -> None:
    """`<h2>Guides associés</h2>` was hardcoded, so German, Russian and Arabic guide pages all
    said it in French. Headings belong in the catalogue, where the parity test can see them."""
    typed = re.findall(r"<h2>([^<{][^<]*)</h2>", template(lang))
    assert not typed, f"[{lang}] encabezado escrito a mano: {typed}"


@pytest.mark.parametrize("lang", LANGS)
def test_the_guide_never_claims_a_medical_review(lang: str) -> None:
    """Google's health guidelines reward `reviewedBy` and `lastReviewed`, and no clinician has
    read these guides. Claiming either would be the one kind of statement this site exists to not
    make — worse than the SEO is worth, and worse coming from a page whose whole argument is that
    it says only what it can show.
    """
    # code only: the comment above the block explains why those fields are absent, and a check
    # that fires at its own documentation teaches people to stop documenting. Same trap as the
    # ternary guard, twice in one day.
    code = "\n".join(
        line.split("//")[0] for line in template(lang).splitlines()
        if not line.lstrip().startswith(("//", "/*", "*"))
    )
    for claim in ("reviewedBy", "lastReviewed"):
        assert claim not in code, f"[{lang}] declara {claim} sin que nadie haya revisado nada"


@pytest.mark.parametrize("lang", LANGS)
def test_the_guide_declares_what_is_true_about_it(lang: str) -> None:
    """The honest half: who publishes it, who it is for, what field, when, and its citations."""
    t = template(lang)
    for field in ("publisher", "audience", "specialty", "dateModified", "citation", "inLanguage"):
        assert field in t, f"[{lang}] los datos estructurados no declaran {field}"
