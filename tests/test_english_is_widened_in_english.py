"""Una pregunta en inglés se amplía con palabras en inglés (7-oct-2026).

Desde el primer día, cuando los sinónimos traían menos de tres términos, el LLM añadía palabras
clave en castellano: el corpus era castellano. Hoy el inglés tiene tres veces más documentos, y
con esas palabras 469 de 1.043 preguntas en inglés de las baterías no tenían ni un pasaje en
inglés entre los tres primeros («dry cough for three weeks» → la tuberculosis del Ministério da
Saúde). Con palabras en inglés, 79. En el conjunto difícil, las respuestas en inglés sin ninguna
fuente en inglés pasan de 72 a 33 y la utilidad no cambia.
"""

from __future__ import annotations

from types import SimpleNamespace

from pedibot.bot import retrieval
from pedibot.bot.retrieval import Retriever


class _LLM:
    def __init__(self) -> None:
        self.sistemas: list[str] = []

    def complete(self, system: str, user: str, **_: object) -> SimpleNamespace:
        self.sistemas.append(system)
        return SimpleNamespace(text="cough, chronic cough")


class _Sinonimos:
    def expand(self, query: str, lang: str) -> list[str]:
        return []


def _retriever(llm: _LLM) -> Retriever:
    r = Retriever.__new__(Retriever)
    r.synonyms, r.llm, r.expansion_en = _Sinonimos(), llm, "en"
    return r


def test_el_ingles_pide_palabras_en_ingles() -> None:
    llm = _LLM()
    assert _retriever(llm).expand("my son has had a dry cough for three weeks", "en") == [
        "cough",
        "chronic cough",
    ]
    assert llm.sistemas == [retrieval.TRANSLATE_SYSTEM_EN]


def test_las_demas_lenguas_siguen_en_castellano() -> None:
    llm = _LLM()
    _retriever(llm).expand("mon fils tousse depuis trois semaines", "fr")
    assert llm.sistemas == [retrieval.TRANSLATE_SYSTEM]


def test_es_lo_que_trae_el_motor() -> None:
    import inspect

    assert 'self.expansion_en = "en"' in inspect.getsource(Retriever.__init__)
