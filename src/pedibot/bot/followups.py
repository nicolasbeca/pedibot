"""Las preguntas que vienen después de una respuesta.

Tras «tiene fiebre» viene «¿cuánto paracetamol?» o «¿cuándo voy a urgencias?». El chat las
ofrece como botones según el asunto de la taxonomía que la respuesta tocó, en la lengua del
padre. Viven en `config/followups.yaml`, y cada una tiene fuente en el corpus: hay una prueba que
las busca una a una, porque una pregunta que ofrecemos nosotros y acaba en «no tengo fuente» es
peor que ninguna.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from pedibot.index.store import fold


class Followups:
    def __init__(self, path: Path) -> None:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
        self._table: dict[str, dict[str, list[str]]] = (raw or {}).get("followups", {})

    def for_topic(self, topic: str | None, lang: str, asked: str = "") -> list[str]:
        """Las preguntas del asunto en esa lengua, sin la que el padre acaba de hacer."""
        if not topic:
            return []
        hecha = fold(asked).casefold().strip()
        todas = self._table.get(topic, {}).get(lang, [])
        return [q for q in todas if fold(q).casefold().strip() != hecha]

    @property
    def topics(self) -> set[str]:
        return set(self._table)
