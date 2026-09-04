"""No catalogue entry may carry a field nobody defined (4-sep-2026).

`config/fuentes*.yaml` writes one document per line as a YAML flow mapping,
`{doc_id: x, org_full: y, ...}`. In a flow mapping an unquoted scalar ends at the first comma —
so a value that legitimately contains one, like a list of authors, is truncated there and the
remainder becomes extra keys with null values. There is no error and no warning.

It had happened three times and nobody had noticed: the catalogue was publishing
"Asociación Española de Pediatría — Protocolos de Neonatología (Doménech" with the parenthesis
left open, plus junk fields called 'González' and 'Rodríguez-Alarcón)'. Since the catalogue is
what every citation on the site is built from, a silently truncated publisher name is a citation
that names the wrong thing.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = sorted((ROOT / "config").glob("fuentes*.yaml"))

#: Every field a catalogue entry is allowed to have. Adding one here is a deliberate act; finding
#: one that is not here means a comma ate a value.
ALLOWED = {
    "doc_id", "file", "url", "org", "org_full", "title", "year", "lang", "topic", "doc_type",
    "evidence", "usage", "age_groups", "notes", "dose_source",
}


def entries(path: pathlib.Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["sources"]


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_entry_carries_a_field_nobody_defined(path: pathlib.Path) -> None:
    strays = {}
    for e in entries(path):
        extra = set(e) - ALLOWED
        if extra:
            strays[e.get("doc_id", "?")] = sorted(extra)
    assert not strays, (
        f"campos inesperados en {path.name} — casi seguro una coma sin comillas: {strays}"
    )


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_publisher_name_is_left_hanging_open(path: pathlib.Path) -> None:
    """The visible symptom of the same bug, checked directly: a name cut at a comma usually ends
    with an unclosed bracket."""
    bad = []
    for e in entries(path):
        for field in ("org_full", "title", "notes"):
            v = e.get(field)
            if isinstance(v, str) and v.count("(") != v.count(")"):
                bad.append((e.get("doc_id"), field, v))
    assert not bad, f"paréntesis sin cerrar en {path.name}: {bad}"


def test_the_catalogue_files_are_the_whole_catalogue() -> None:
    """If a third file of sources appears, this suite must be told about it rather than silently
    checking two thirds of the catalogue."""
    assert len(FILES) == 2, [p.name for p in FILES]
    assert sum(len(entries(p)) for p in FILES) >= 288
