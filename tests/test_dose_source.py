"""Only a sanctioned dosing source unlocks a dose in an answer (26-ago-2026).

`verify()` let a text state mg/ml as long as ANY retrieved chunk looked like a dose table — and
"looks like a dose table" is just `mg/kg` in the text. That is true of every professional textbook
in the corpus (antibiotic guides, the 402-page primary-care manual added today), which prescribe
corticoids and antibiotics. PediBot must never hand a parent those numbers, so the exception is
now tied to `dose_source: true` in the catalogue — today only the AEPap dosing guide, the same
source the calculator uses.
"""

from __future__ import annotations

import pathlib

import yaml

from pedibot.bot.answer import verify
from pedibot.index.store import Hit
from pedibot.ingest.schema import Chunk

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _hit(dose_table: bool, dose_source: bool) -> Hit:
    return Hit(
        Chunk(
            chunk_id="d#1",
            doc_id="d",
            org="ORG",
            doc_title="Doc",
            year=2024,
            lang="es",
            section="S",
            pages=[1],
            text="dexametasona 1 mg/kg dosis única",
            topic="medicamentos",
            doc_type="libro",  # type: ignore[arg-type]
            evidence="editorial",
            usage="citar_solo",  # type: ignore[arg-type]
            is_dose_table=dose_table,
            is_dose_source=dose_source,
            source_hash="h",
            n_words=6,
        ),
        1.0,
        1,
    )


_TEXT = "Puede darle 250 mg cada 8 horas [1]."


def test_a_textbook_dose_table_does_not_unlock_a_dose():
    assert "dose_without_table" in verify(_TEXT, [_hit(dose_table=True, dose_source=False)])


def test_the_sanctioned_dosing_source_does_unlock_it():
    assert verify(_TEXT, [_hit(dose_table=True, dose_source=True)]) == []


def test_the_catalogue_marks_exactly_the_dosing_guide():
    cat = yaml.safe_load((ROOT / "config" / "fuentes.yaml").read_text(encoding="utf-8"))["sources"]
    marked = {d["doc_id"] for d in cat if d.get("dose_source")}
    assert marked == {"aepap_guia_dosificacion_3ed"}, marked
