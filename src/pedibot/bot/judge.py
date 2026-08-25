"""Faithfulness judge (LLM-as-judge). Given the drafted answer and the exact passages it cited,
asks a second call whether every claim is supported. Used by `pedibot eval --llm` and, later,
by the nightly review (IDEAS O-02). It is a SIGNAL for the operator, not a gate in the live path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pedibot.bot.llm import LLMProvider
from pedibot.index.store import Hit

JUDGE_SYSTEM = """You are a strict medical fact-checker. You receive an ANSWER written for a parent and the
SOURCE PASSAGES it cites. Decide, sentence by sentence, whether each clinical claim is supported by
the passages (translation between languages is fine; paraphrase is fine; adding facts is NOT).

Output ONLY a JSON object:
{"verdict": "faithful" | "minor_issue" | "unfaithful",
 "unsupported": ["<claim not supported by any passage>", ...],
 "contradicted": ["<claim that contradicts a passage>", ...],
 "notes": "<one sentence>"}

"minor_issue" = a small unsupported detail that would not change what the parent does.
"unfaithful" = an unsupported or contradicted claim that could change what the parent does
(doses, timings, when to go to the emergency department, what NOT to give)."""

_JSON = re.compile(r"\{.*\}", re.S)


@dataclass
class Verdict:
    verdict: str
    unsupported: list[str]
    contradicted: list[str]
    notes: str
    cost_usd: float

    @property
    def ok(self) -> bool:
        return self.verdict == "faithful"


def judge(llm: LLMProvider, answer_text: str, hits: list[Hit], cited: list[int]) -> Verdict:
    passages = []
    for n in cited:
        if 1 <= n <= len(hits):
            c = hits[n - 1].chunk
            passages.append(f"[{n}] {c.org} — {c.doc_title} — {c.section}\n{c.text}")
    user = f"ANSWER:\n{answer_text}\n\nSOURCE PASSAGES:\n" + "\n\n".join(passages)
    res = llm.complete(JUDGE_SYSTEM, user, temperature=0.0, max_tokens=600)
    m = _JSON.search(res.text)
    if not m:
        return Verdict("unparseable", [], [], res.text[:200], res.cost_usd)
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return Verdict("unparseable", [], [], res.text[:200], res.cost_usd)
    return Verdict(
        str(d.get("verdict", "unparseable")),
        [str(x) for x in d.get("unsupported", [])],
        [str(x) for x in d.get("contradicted", [])],
        str(d.get("notes", "")),
        res.cost_usd,
    )
