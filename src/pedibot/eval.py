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
import re
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
    #: cases whose retrieval could not be judged here — see run_eval
    unmeasured_sources: list[str] = field(default_factory=list)

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
        # Not measurable without a model when the language has no local synonyms: retrieval for
        # it goes through a translation call that this harness deliberately does not make. Marked
        # None (skipped) rather than False, so the ratio stays a fact about the system.
        local = engine.retriever.expand(q, g.get("lang") or "en")
        measurable = bool(local) or not isinstance(engine.llm, FakeProvider)
        source_hit = (
            (any(d in docs_pred[:k] for d in docs_expected) if docs_expected else None)
            if measurable
            else None
        )
        if not measurable:
            rep.unmeasured_sources.append(g["id"])
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


# ---------------------------------------------------------------------------------------------
# LLM-in-the-loop evaluation (needs a real provider; PRD §5.5 citation_validity, cost, latency)
# ---------------------------------------------------------------------------------------------


@dataclass
class LLMCase:
    id: str
    q: str
    verification: str
    level: str
    n_sources: int
    cost_usd: float
    latency_ms: int
    tokens_in: int
    tokens_out: int
    judge_verdict: str | None = None
    judge_notes: str = ""
    judge_issues: list[str] = field(default_factory=list)
    answer_text: str = ""


@dataclass
class LLMReport:
    cases: list[LLMCase] = field(default_factory=list)

    def summary(self) -> dict[str, object]:
        drafted = [c for c in self.cases if c.verification in ("ok", "regenerated", "fallback")]
        ok = [c for c in drafted if c.verification in ("ok", "regenerated")]
        lat = sorted(c.latency_ms for c in self.cases)
        p95 = lat[int(len(lat) * 0.95) - 1] if lat else None
        return {
            "n": len(self.cases),
            "drafted": len(drafted),
            "citation_validity": _ratio([c.verification != "fallback" for c in drafted]),
            "regenerated_rate": _ratio([c.verification == "regenerated" for c in drafted]),
            "with_sources": _ratio([c.n_sources > 0 for c in ok]),
            "cost_total_usd": round(sum(c.cost_usd for c in self.cases), 5),
            "cost_mean_usd": round(sum(c.cost_usd for c in drafted) / len(drafted), 6)
            if drafted
            else None,
            "latency_p95_ms": p95,
            "judged": len([c for c in self.cases if c.judge_verdict]),
            "faithful_rate": _ratio(
                [c.judge_verdict == "faithful" for c in self.cases if c.judge_verdict]
            ),
            "unfaithful": [c.id for c in self.cases if c.judge_verdict == "unfaithful"],
        }


def run_llm_eval(
    engine: Engine, golden: list[dict], only_drafted: bool = True, use_judge: bool = False
) -> LLMReport:
    """Ask the real engine every golden question; measure the drafting/verification layer."""
    import time

    rep = LLMReport()
    for g in golden:
        if only_drafted and g.get("expect") in ("asked_age", "dose_calculator", "no_source"):
            continue
        t0 = time.perf_counter()
        a = engine.ask(g["q"], lang=g.get("lang"))
        ms = int((time.perf_counter() - t0) * 1000)
        case = LLMCase(
            g["id"],
            g["q"],
            a.verification,
            a.level,
            len(a.sources),
            a.llm.cost_usd if a.llm else 0.0,
            ms,
            a.llm.tokens_in if a.llm else 0,
            a.llm.tokens_out if a.llm else 0,
            answer_text=a.text,
        )
        if use_judge and a.verification in ("ok", "regenerated") and a.chunk_ids:
            from pedibot.bot.judge import judge
            from pedibot.index.store import Hit

            chunks = [engine.retriever.index.get(cid) for cid in a.chunk_ids]
            hits = [Hit(c, 0.0, 0) for c in chunks if c]
            cited = sorted({int(n) for n in re.findall(r"\[(\d{1,2})\]", a.text)})
            v = judge(engine.llm, a.text, hits, cited)
            case.judge_verdict, case.judge_notes = v.verdict, v.notes
            case.judge_issues = v.unsupported + v.contradicted
            case.cost_usd += v.cost_usd
        rep.cases.append(case)
    return rep
