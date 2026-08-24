"""Rule-based classification of chunks (topic/subtopics/age). LLM refinement is optional later."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


class Taxonomy:
    """`config/taxonomia.yaml`: topics with keyword lists (es + en)."""

    def __init__(self, path: Path):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.topics: dict[str, list[str]] = raw["topics"]
        self.subtopics: dict[str, list[str]] = raw.get("subtopics", {})
        self.ages: dict[str, list[str]] = raw.get("age_groups", {})
        self._topic_re = {t: _compile(kws) for t, kws in self.topics.items()}
        self._sub_re = {t: _compile(kws) for t, kws in self.subtopics.items()}
        self._age_re = {t: _compile(kws) for t, kws in self.ages.items()}

    def subtopics_for(self, text: str) -> list[str]:
        return [s for s, rx in self._sub_re.items() if rx.search(text)]

    def ages_for(self, text: str) -> list[str]:
        found = [a for a, rx in self._age_re.items() if rx.search(text)]
        return found or ["todas"]

    def topic_for(self, text: str) -> str | None:
        """Best topic by keyword hits; used when the catalog does not fix one (e.g. manuals)."""
        scores = {t: len(rx.findall(text)) for t, rx in self._topic_re.items()}
        best = max(scores, key=lambda k: scores[k]) if scores else None
        return best if best and scores[best] > 0 else None


def _compile(kws: list[str]) -> re.Pattern[str]:
    parts = [re.escape(str(k)) for k in kws]
    return re.compile(r"\b(" + "|".join(parts) + r")\w*", re.I)
