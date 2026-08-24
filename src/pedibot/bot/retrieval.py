"""Retrieval with cross-lingual expansion: synonyms (offline) + optional LLM translation."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from pedibot.bot.llm import LLMProvider
from pedibot.index.store import Hit, Index, query_terms

_TOKEN = re.compile(r"[\wáéíóúñü]+", re.I)

TRANSLATE_SYSTEM = (
    "You translate a parent's question about a child's health into 5-10 Spanish medical search "
    "keywords (nouns, symptoms, condition names). Output only the keywords separated by commas. "
    "No explanations."
)


class Synonyms:
    def __init__(self, path: Path):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self._map: dict[str, list[str]] = raw.get("en", {})

    def expand(self, query: str) -> list[str]:
        extra: list[str] = []
        for tok in _TOKEN.findall(query.lower()):
            for trigger, terms in self._map.items():
                if tok.startswith(trigger):
                    for t in terms:
                        if t not in extra:
                            extra.append(t)
        return extra


def detect_lang(text: str) -> str:
    """Tiny heuristic: es vs en (enough to pick synonym direction and answer language hints)."""
    low = " " + re.sub(r"[¿¡?!.,;:]", " ", text.lower()) + " "
    es_markers = [
        " mi ",
        " hijo",
        " hija",
        " tiene ",
        " fiebre",
        " años",
        " meses",
        " le ",
        " qué ",
        " que ",
        " puedo",
        " está ",
        " bebé",
        " niño",
        " niña",
        " puede",
        " tomar",
        " cuánto",
        " cuanto",
        " perro",
        " se ",
        " ha ",
        " una ",
        " con ",
        " del ",
        " para ",
        " los ",
        " las ",
    ]
    en_markers = [
        " my ",
        " has ",
        " fever",
        " old ",
        " should ",
        " the ",
        " is ",
        " can ",
        " what ",
        " baby",
        " son ",
        " daughter",
        " he ",
        " she ",
    ]
    es = sum(m in low for m in es_markers) + sum(ch in "áéíóúñ¿¡" for ch in text.lower())
    en = sum(m in low for m in en_markers)
    if es == en == 0:
        return "en"
    return "es" if es >= en else "en"


class Retriever:
    def __init__(
        self, index: Index, synonyms: Synonyms, llm: LLMProvider | None = None, top_k: int = 6
    ):
        self.index = index
        self.synonyms = synonyms
        self.llm = llm
        self.top_k = top_k

    def expand(self, query: str, lang: str) -> list[str]:
        extra = self.synonyms.expand(query) if lang != "es" else []
        if self.llm is not None and lang != "es" and len(extra) < 3:
            try:
                out = self.llm.complete(
                    TRANSLATE_SYSTEM, query, temperature=0.0, max_tokens=60
                ).text
                for kw in out.split(","):
                    kw = kw.strip().lower()
                    if kw and kw not in extra:
                        extra.append(kw)
            except Exception:  # noqa: BLE001 — expansion is best-effort
                pass
        return extra

    def search(
        self, query: str, lang: str, red_flag_boost: bool = False
    ) -> tuple[list[Hit], list[str]]:
        extra = self.expand(query, lang)
        hits = self.index.search(
            query, top_k=self.top_k, extra_terms=extra, red_flag_boost=red_flag_boost
        )
        # "source or silence": require at least one meaningful term matched in the text itself
        terms = query_terms(query, extra)
        good = [h for h in hits if h.matched_terms >= 1] if terms else []
        return good, extra
