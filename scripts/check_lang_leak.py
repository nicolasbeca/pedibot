"""Catch a page that shipped in the wrong language (3-sep-2026).

Cloning /es into /fr and translating the i18n table left six pages with their Spanish titles and
bodies intact, and the warning-signs list rendered as 34 empty bullets because its data only had
en/es. None of that failed the build: a missing translation is a blank string, not an error.

So the build output is checked directly. For every page, the language is read from its path and
its headline text (title, h1, h2, the eyebrow and lede) must not contain a word that only
belongs to another language. Headlines only — the source catalogue legitimately lists Spanish
document titles on the English page, and quoting a source is not the same as shipping in the
wrong language.

    uv run python scripts/check_lang_leak.py            # after `npx astro build`
    uv run python scripts/check_lang_leak.py --dist X   # another build directory
"""

from __future__ import annotations

import argparse
import pathlib
import re
from html import unescape

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "site" / "dist"

# Words that belong to exactly one of the site's languages. Deliberately short and unambiguous:
# 'sources'/'guides'/'documents' are shared between English and French and are not markers.
MARKERS: dict[str, tuple[str, ...]] = {
    "es": ("¿", "años", "niño", "hijo", "qué ", "cómo", "vacunas", "urgencias", "guías",
           # "dosis" was a marker until German arrived and spells it the same way
           "síntomas", "medicación", "cuándo", "preguntas frecuentes"),
    "en": ("child", "should", "what ", "when ", "vaccination schedule", "symptom diary",
           "dose calculator", "guidelines", "warning signs", "how it works", "common questions",
           "where they agree", "where they differ"),
    # the last four were added on 4-sep: the German, Russian and Arabic home pages carried the
    # French title for weeks and none of the words above appear in it
    "fr": ("enfant", "urgences", "vaccinal", "posologie", "dois-je", "médicaments",
           "quels ", "âge", "santé", "questions fréquentes",
           "gratuit ", "réponses", "sourcé", "pour les parents", "toutes les"),
    "de": ("kind", "notaufnahme", "impfkalender", "dosisrechner", "warnzeichen", "soll ich",
           "ratgeber", "häufige fragen", "quellen", "symptomtagebuch"),
    # Russian is in its own script, so any Cyrillic at all on a non-Russian page is a leak
    "ru": ("ребён", "ребен", "температур", "прививк", "источник", "калькулятор доз",
           "тревожн", "статьи для родителей", "дневник симптомов"),
    "ar": ("طفل", "الطوارئ", "التطعيمات", "حاسبة الجرعات", "المصادر", "علامات التحذير",
           "أدلة للوالدين", "مفكرة الأعراض"),
    # Portuguese words that Spanish does not spell the same way, which is the only real risk here
    "pt": ("criança", "você", "vômitos", "diretrizes", "pronto-socorro", "não ",
           "guias para pais", "sinais de alarme"),
    # Devanagari is its own script, so any of it on a non-Hindi page is a leak by itself;
    # these are the words the Hindi pages actually print, for the reverse direction
    "hi": ("बच्चे", "बुखार", "टीक", "इमरजेंसी", "खुराक", "स्रोत", "गाइड",
           "चेतावनी के निशान", "आम सवाल"),
}


def proper_names() -> list[str]:
    """Organisations, brands and schedule names are quoted verbatim in every language.

    "Sociedad Espanola de Urgencias de Pediatria" on the English sources page is a citation, not a
    page that shipped in Spanish, and "Advil Children's" is what is printed on the box. Read from
    the data rather than listed here, so the allowance follows the catalogue.
    """
    import json

    names: set[str] = set()
    data = ROOT / "web" / "site" / "src" / "data"
    for d in json.loads((data / "sources.json").read_text(encoding="utf-8")):
        names.update(x for x in (d.get("org"), d.get("org_full")) if x)
    for c in json.loads((data / "vaccines.json").read_text(encoding="utf-8")).values():
        names.update((c.get("name") or {}).values())
    def every_name(node: object) -> None:
        """Brand names sit at several depths in drugs.json; collect every "name" there is."""
        if isinstance(node, dict):
            if isinstance(node.get("name"), str):
                names.add(node["name"])
            for v in node.values():
                every_name(v)
        elif isinstance(node, list):
            for v in node:
                every_name(v)

    every_name(json.loads((data / "drugs.json").read_text(encoding="utf-8")))
    # brand names also reach the dose pages through the site module, not through a data file
    ts = ROOT / "web" / "site" / "src" / "dosepages.ts"
    if ts.exists():
        names.update(re.findall(r"'([^']*Children[^']*)'", ts.read_text(encoding="utf-8")))
    return sorted((n for n in names if len(n) > 3), key=len, reverse=True)


NAMES = proper_names()

HEADLINE = re.compile(
    r"<title>(.*?)</title>"
    r"|<h1[^>]*>(.*?)</h1>"
    r"|<h2[^>]*>(.*?)</h2>"
    r'|<p class="eyebrow"[^>]*>(.*?)</p>'
    r'|<p class="lede"[^>]*>(.*?)</p>'
    # the meta description was not read at all, and it shipped in French on nine pages
    r'|<meta name="description" content="([^"]*)"',
    re.S | re.I,
)
TAG = re.compile(r"<[^>]*>")


def page_lang(rel: pathlib.PurePath) -> str:
    """English lives at the root, the others under their own prefix."""
    first = rel.parts[0] if rel.parts else ""
    return first if first in MARKERS else "en"


def headlines(html: str) -> list[str]:
    out = []
    for m in HEADLINE.finditer(html):
        text = unescape(TAG.sub(" ", next(g for g in m.groups() if g is not None)))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append(text)
    return out


def leaks(html: str, lang: str) -> list[tuple[str, str, str]]:
    """(foreign language, the word found, the headline it was found in)."""
    found = []
    for line in headlines(html):
        low = line.lower()
        for name in NAMES:  # a quoted organisation or brand is not the page's language
            low = low.replace(name.lower(), " ")
        for other, words in MARKERS.items():
            if other == lang:
                continue
            for w in words:
                if w in low:
                    found.append((other, w.strip(), line[:90]))
                    break
    return found


def scan(dist: pathlib.Path) -> dict[str, list[tuple[str, str, str]]]:
    bad: dict[str, list[tuple[str, str, str]]] = {}
    for f in sorted(dist.rglob("*.html")):
        rel = f.relative_to(dist)
        hits = leaks(f.read_text(encoding="utf-8", errors="replace"), page_lang(rel))
        if hits:
            bad[str(rel).replace("\\", "/")] = hits
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default=str(DIST))
    args = ap.parse_args()
    dist = pathlib.Path(args.dist)
    if not dist.exists():
        print(f"no hay build en {dist} — ejecuta `npx astro build` primero")
        return 2

    bad = scan(dist)
    total = len(list(dist.rglob("*.html")))
    if not bad:
        print(f"{total} páginas: ningún idioma mezclado en los titulares")
        return 0
    for page, hits in bad.items():
        print(f"\n{page}")
        for other, word, line in hits:
            print(f"    parece {other}: «{word}» en «{line}»")
    print(f"\n{len(bad)} de {total} páginas con idioma mezclado")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
