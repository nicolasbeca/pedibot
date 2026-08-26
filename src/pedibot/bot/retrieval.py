"""Retrieval with cross-lingual expansion: synonyms (offline) + optional LLM translation."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from pedibot.bot.llm import LLMProvider
from pedibot.index.store import Hit, Index, query_terms
from pedibot.ingest.classify import Taxonomy

_TOKEN = re.compile(r"[\wáéíóúñü]+", re.I)
TRANSLATE_SYSTEM = (
    "You translate a parent's question about a child's health into 5-10 Spanish medical search "
    "keywords (nouns, symptoms, condition names). Output only the keywords separated by commas. "
    "No explanations."
)


class Synonyms:
    def __init__(self, path: Path):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self._maps: dict[str, dict[str, list[str]]] = {k: v or {} for k, v in raw.items()}

    def _tables(self, lang: str) -> list[dict[str, list[str]]]:
        """`es` (colloquial → leaflet) plus any cross-lingual table such as `es_en`."""
        return [v for k, v in self._maps.items() if k == lang or k.startswith(f"{lang}_")]

    def expand(self, query: str, lang: str = "en") -> list[str]:
        low = query.lower()
        tokens = _TOKEN.findall(low)
        extra: list[str] = []
        for table in self._tables(lang):
            for trigger, terms in table.items():
                # a trigger with a space is a phrase ("stomach bug"), matched on the whole query;
                # a single word is matched by prefix on each token ("vomit" → "vomiting")
                if " " in trigger:
                    hit = trigger in low
                else:
                    hit = any(t.startswith(trigger) for t in tokens)
                if hit:
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
        self,
        index: Index,
        synonyms: Synonyms,
        llm: LLMProvider | None = None,
        top_k: int = 6,
        taxonomy: Taxonomy | None = None,
    ):
        self.index = index
        self.synonyms = synonyms
        self.llm = llm
        self.top_k = top_k
        self.taxonomy = taxonomy

    def expand(self, query: str, lang: str) -> list[str]:
        extra = self.synonyms.expand(query, lang)
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
        topic = self.taxonomy.topic_for(query + " " + " ".join(extra)) if self.taxonomy else None
        hits = self.index.search(
            query,
            top_k=self.top_k,
            extra_terms=extra,
            red_flag_boost=red_flag_boost,
            boost_topic=topic,
        )
        # "source or silence": a hit must match a query term in its own text, and the question must
        # look paediatric (a taxonomy topic) unless it matches >= 3 terms; "my dog ate chocolate"
        # would otherwise match "perro" in the croup leaflet (one term, no topic).
        terms = query_terms(query, extra)
        if not terms:
            return [], extra
        min_matched = 1 if topic else 3
        good = [h for h in hits if h.matched_terms >= min_matched]
        # NOTE (26-ago-2026): a relevance floor was measured here and REJECTED. Neither an absolute
        # bm25 threshold nor a term-coverage ratio separates "the corpus covers this" from "it does
        # not": legitimate questions match as little as 1 term of 7 (g23) and score 20, while
        # "se hace pis en la cama" — covered by nothing — scores 10 and matches 1 of 3. The ranges
        # overlap, and an absolute score is not even comparable between corpora (it silenced every
        # test fixture). Separating them needs semantic similarity, not another threshold.
        return good, extra
