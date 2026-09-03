"""Chunk schema. One chunk = one citable unit (PRD §4.2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from pedibot.ingest.sections import LEAD_SECTION

Usage = Literal["publico", "citar_solo", "excluido"]
DocType = Literal["hoja_padres", "guia_clinica", "calendario", "manual", "libro", "informe"]
Evidence = Literal[
    "sociedad_cientifica", "organismo_publico", "universidad", "editorial", "hospital"
]


class SourceDoc(BaseModel):
    """One entry of `config/fuentes.yaml` (the catalog)."""

    doc_id: str
    file: str
    org: str
    org_full: str = ""
    title: str
    year: int | None = None
    lang: str = "es"
    topic: str
    doc_type: DocType
    evidence: Evidence
    usage: Usage
    age_groups: list[str] = Field(default_factory=lambda: ["todas"])
    url: str | None = None
    # true only for material we are willing to turn into a dose for a parent (the AEPap dosing
    # guide, same source as the calculator). Professional textbooks prescribe corticoids and
    # antibiotics: their mg/kg figures must never unlock a dose in an answer.
    dose_source: bool = False
    notes: str = ""


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    org: str
    doc_title: str
    year: int | None
    lang: str
    section: str
    pages: list[int]
    text: str
    topic: str
    subtopics: list[str] = Field(default_factory=list)
    age_groups: list[str] = Field(default_factory=lambda: ["todas"])
    doc_type: DocType
    evidence: Evidence
    usage: Usage
    is_red_flag: bool = False
    is_dose_table: bool = False
    is_dose_source: bool = False
    source_url: str | None = None
    source_hash: str
    n_words: int = 0

    def citation(self) -> str:
        """Human-readable citation used at the bottom of every answer.

        The section is named only when the document actually has one. Text before the first
        heading gets a synthetic label from the chunker, and printing that as if it were a
        heading sends a reader looking for something that is not there.
        """
        year = f" ({self.year})" if self.year else ""
        pages = ", ".join(str(p) for p in self.pages)
        head = f'{self.org} — "{self.doc_title}"{year}'
        # "Introducción" is the old sentinel: it is still in the index until the next full ingest
        if self.section and self.section not in (LEAD_SECTION, "Introducción"):
            head += f', section "{self.section}"'
        return f"{head}, p. {pages}"
