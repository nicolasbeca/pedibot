"""Chunk schema. One chunk = one citable unit (PRD §4.2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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
    source_url: str | None = None
    source_hash: str
    n_words: int = 0

    def citation(self) -> str:
        """Human-readable citation used at the bottom of every answer."""
        year = f" ({self.year})" if self.year else ""
        pages = ", ".join(str(p) for p in self.pages)
        return f'{self.org} — "{self.doc_title}"{year}, section "{self.section}", p. {pages}'
