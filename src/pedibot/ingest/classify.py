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
    """Las claves casan por prefijo; una acabada en `$` casa la palabra entera y nada más.

    El prefijo es lo que se quiere casi siempre —«vomit» tiene que coger «vomiting» y «vacuna»
    tiene que coger «vacunación»— pero con ocho idiomas en la misma lista produce falsos amigos.
    Medido contra el vocabulario de las 483 guías (10-sep-2026): «ear» cogía «early» 85 veces,
    «infant» cogía «infantil» 62, y de las claves añadidas la víspera, «uti» cogía «utilizar» y
    «utiliser», «wee» cogía «week» y «weeks», y «dent» cogía «dentro».

    Un tema equivocado no sólo etiqueta mal: multiplica por 1,5 los fragmentos que coinciden con
    él y por 0,7 todos los demás, y además baja la puerta del «fuente o silencio» de tres
    términos a uno.
    """
    prefijos = [re.escape(str(k)) for k in kws if str(k).strip() and not str(k).endswith("$")]
    exactas = [re.escape(str(k)[:-1]) for k in kws if str(k).strip().endswith("$")]
    trozos = []
    if prefijos:
        trozos.append(r"(?:" + "|".join(prefijos) + r")\w*")
    if exactas:
        trozos.append(r"(?:" + "|".join(exactas) + r")\b")
    if not trozos:
        return re.compile(r"(?!x)x")  # never matches (empty keyword list, e.g. "general")
    return re.compile(r"\b(" + "|".join(trozos) + r")", re.I)
