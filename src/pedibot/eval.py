"""Golden-set evaluation of triage + retrieval + routing. Runs WITHOUT an LLM (PRD §5.5).

Metrics:
  triage_exact       level == expected level
  red_flag_recall    expected non-routine → predicted non-routine        (gate: 1.0)
  red_flag_precision expected routine → predicted routine                (target ≥ 0.7)
  rules_hit          every expected rule id fired
  source_hit@k       any expected doc_id among the top-k retrieved chunks (target ≥ 0.85)
  routing            expected verification (asked_age / dose_calculator / no_source) matched
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pedibot.bot.answer import Engine
from pedibot.bot.llm import FakeProvider


@dataclass
class CaseResult:
    id: str
    q: str
    level_expected: str
    level_pred: str
    rules_expected: list[str]
    rules_pred: list[str]
    docs_expected: list[str]
    docs_pred: list[str]
    expect: str | None
    verification: str
    source_hit: bool | None
    routing_ok: bool | None

    @property
    def triage_ok(self) -> bool:
        return self.level_expected == self.level_pred

    @property
    def rules_ok(self) -> bool:
        return all(r in self.rules_pred for r in self.rules_expected)


@dataclass
class Report:
    cases: list[CaseResult] = field(default_factory=list)

    def metric(self, name: str) -> float | None:
        c = self.cases
        if name == "triage_exact":
            return _ratio([x.triage_ok for x in c])
        if name == "red_flag_recall":
            return _ratio([x.level_pred != "routine" for x in c if x.level_expected != "routine"])
        if name == "red_flag_precision":
            return _ratio([x.level_pred == "routine" for x in c if x.level_expected == "routine"])
        if name == "rules_hit":
            return _ratio([x.rules_ok for x in c if x.rules_expected])
        if name == "source_hit":
            return _ratio([bool(x.source_hit) for x in c if x.source_hit is not None])
        if name == "routing":
            return _ratio([bool(x.routing_ok) for x in c if x.routing_ok is not None])
        raise KeyError(name)

    def summary(self) -> dict[str, float | None]:
        return {
            m: self.metric(m)
            for m in (
                "triage_exact",
                "red_flag_recall",
                "red_flag_precision",
                "rules_hit",
                "source_hit",
                "routing",
            )
        }

    def failures(self) -> list[str]:
        out = []
        for x in self.cases:
            probs = []
            if not x.triage_ok:
                probs.append(f"level {x.level_pred}≠{x.level_expected}")
            if not x.rules_ok:
                probs.append(f"rules {x.rules_pred}≠{x.rules_expected}")
            if x.source_hit is False:
                probs.append(f"source top={x.docs_pred[:3]} want {x.docs_expected}")
            if x.routing_ok is False:
                probs.append(f"routing {x.verification}≠{x.expect}")
            if probs:
                out.append(f"{x.id} «{x.q}» → " + "; ".join(probs))
        return out


def _ratio(xs: list[bool]) -> float | None:
    return round(sum(xs) / len(xs), 3) if xs else None


def load_golden(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_eval(engine: Engine, golden: list[dict], k: int = 3) -> Report:
    rep = Report()
    for g in golden:
        q = g["q"]
        tr = engine.triage.assess(q)
        docs_expected = g.get("docs", [])
        hits, _ = engine.retriever.search(q, g.get("lang") or "en", red_flag_boost=tr.is_alarm)
        docs_pred = []
        for h in hits:
            if h.chunk.doc_id not in docs_pred:
                docs_pred.append(h.chunk.doc_id)
        source_hit = any(d in docs_pred[:k] for d in docs_expected) if docs_expected else None
        expect = g.get("expect")
        a = engine.ask(q, lang=g.get("lang"))
        routing_ok = (a.verification == expect) if expect else None
        rep.cases.append(
            CaseResult(
                id=g["id"],
                q=q,
                level_expected=g["level"],
                level_pred=tr.level,
                rules_expected=g.get("rules", []),
                rules_pred=[r.id for r in tr.matched],
                docs_expected=docs_expected,
                docs_pred=docs_pred,
                expect=expect,
                verification=a.verification,
                source_hit=source_hit,
                routing_ok=routing_ok,
            )
        )
    return rep


def fake_engine_from_settings() -> Engine:
    from pedibot.bot.answer import EmergencyNumbers
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.bot.triage import Triage
    from pedibot.index.store import Index
    from pedibot.ingest.classify import Taxonomy
    from pedibot.settings import get_settings

    s = get_settings()
    llm = FakeProvider("Grounded draft [1].")
    return Engine(
        Retriever(
            Index(s.index_db_path),
            Synonyms(s.config_dir / "synonyms.yaml"),
            top_k=s.retrieval_top_k,
            taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
        ),
        Triage(s.config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(s.config_dir / "emergency_numbers.yaml"),
    )
