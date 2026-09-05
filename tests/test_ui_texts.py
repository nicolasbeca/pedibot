r"""What a full read of the 3.236 interface strings turned up (5-sep-2026).

The parity test checks that the eight languages have the same KEYS. These check that they say the
same thing, and that what they say is true. Each one is a defect that was live:

  · The vaccination tool offered a different set of ages in every language, because each list was
    written by hand on the day that language was added and froze the countries that existed then.
    A Spanish speaker could not ask about a three-month-old — and Brazil, Portugal and the UK all
    have a dose at three months.

  · The Spanish emergency sheet said "Llame al 112". 112 is European; most Spanish speakers are
    not. This is the page that exists to tell a parent when to call.

  · The French "how it works" lost its {docs} placeholder, so the French homepage was the only
    one that did not say how many documents there are — the strongest fact in that section.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
I18N = ROOT / "web" / "site" / "src" / "i18n.ts"

#: Numbers and services that only work in one country. The catalogue is shown to everybody, so
#: none of them belongs in it: the reader's own number comes from config/emergency_numbers.yaml.
COUNTRY_SPECIFIC = re.compile(r"\b(112|911|999|998|000)\b|NHS\s*111|\bA&E\b")


def _strings() -> dict[str, dict[str, str]]:
    """i18n.ts as JSON, evaluated by Node: it is a TypeScript object with nested arrays, both
    quote styles and apostrophes inside strings, and a regex reader would miss exactly the
    strings worth checking."""
    script = """
    import fs from 'node:fs';
    const src = fs.readFileSync(process.argv[2], 'utf8');
    const open = src.indexOf('{', src.indexOf('export const strings'));
    let depth = 0, end = -1, inStr = null, esc = false;
    for (let i = open; i < src.length; i++) {
      const c = src[i];
      if (inStr) { if (esc) { esc = false; continue; }
        if (c === '\\\\') { esc = true; continue; }
        if (c === inStr) inStr = null; continue; }
      if (c === '"' || c === "'" || c === '`') { inStr = c; continue; }
      if (c === '{') depth++; else if (c === '}') { depth--; if (!depth) { end = i; break; } }
    }
    process.stdout.write(JSON.stringify(eval('(' + src.slice(open, end + 1) + ')')));
    """
    tmp = ROOT / "eval" / "_dump_i18n.mjs"
    tmp.write_text(script, encoding="utf-8")
    try:
        # encoding spelled out: on Windows the default is cp1252 and the catalogue is Arabic,
        # Cyrillic and Devanagari
        out = subprocess.run(
            ["node", str(tmp), str(I18N)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
    finally:
        tmp.unlink(missing_ok=True)
    assert out.returncode == 0, out.stderr[:400]
    return json.loads(out.stdout)


def _flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _flat(v, f"{p}.{k}" if p else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _flat(v, f"{p}[{i}]")
    else:
        yield p, str(o)


@pytest.fixture(scope="module")
def strings() -> dict[str, dict[str, str]]:
    return {lang: dict(_flat(block)) for lang, block in _strings().items()}


def test_every_language_offers_the_same_vaccination_ages(strings) -> None:
    per_lang = {
        lang: [v for k, v in s.items() if re.fullmatch(r"vax_ages\[\d+\]\[0\]", k) and v]
        for lang, s in strings.items()
    }
    unique = {tuple(v) for v in per_lang.values()}
    assert len(unique) == 1, "\n".join(f"{k}: {v}" for k, v in per_lang.items())


def test_no_published_dose_is_out_of_reach_of_the_dropdown(strings) -> None:
    """The tool matches an age to a slot within its own tolerance. An age in a calendar that no
    option comes near is a dose a parent cannot ask about."""
    options = [
        float(v) for k, v in strings["es"].items()
        if re.fullmatch(r"vax_ages\[\d+\]\[0\]", k) and v
    ]
    cal = yaml.safe_load((ROOT / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    ages = {float(s["age"]) for c in cal["countries"].values() for s in c["schedule"]}
    unreachable = [
        a for a in sorted(ages)
        if not any(abs(a - o) <= (1.5 if a < 24 else 6.0) for o in options)
    ]
    assert not unreachable, f"edades sin opción que las alcance: {unreachable}"


def test_the_catalogue_names_no_country_specific_number(strings) -> None:
    """The reader's own emergency number comes from config/emergency_numbers.yaml, by country.
    A number typed into the catalogue is shown to everybody, wherever they are."""
    bad = [
        f"[{lang}] {key}: {val[:80]}"
        for lang, s in strings.items()
        for key, val in s.items()
        if COUNTRY_SPECIFIC.search(val)
    ]
    assert not bad, "\n".join(bad)


def test_the_emergency_sheet_names_no_country_specific_number() -> None:
    sheet = yaml.safe_load((ROOT / "config" / "er_checklist.yaml").read_text(encoding="utf-8"))
    bad: list[str] = []
    for name, node in sheet["levels"].items():
        for lang, text in node.items():
            if COUNTRY_SPECIFIC.search(str(text)):
                bad.append(f"levels.{name}[{lang}]: {text}")
    for i, item in enumerate(sheet["items"]):
        for lang, text in item.items():
            if lang in ("level", "cat"):
                continue
            if COUNTRY_SPECIFIC.search(str(text)):
                bad.append(f"items[{i}][{lang}]: {text}")
    assert not bad, "\n".join(bad)


def test_a_placeholder_is_in_every_language_or_none(strings) -> None:
    """French lost `{docs}` and was the only homepage that did not say how many documents there
    are. A placeholder missing from one language is a fact missing from one edition."""
    ph = re.compile(r"\{(\w+)\}")
    bad: list[str] = []
    for key in strings["en"]:
        seen = {
            lang: frozenset(ph.findall(s[key])) for lang, s in strings.items() if key in s
        }
        if len(set(seen.values())) > 1:
            bad.append(f"{key}: " + ", ".join(f"{k}={sorted(v)}" for k, v in seen.items()))
    assert not bad, "\n".join(bad)
