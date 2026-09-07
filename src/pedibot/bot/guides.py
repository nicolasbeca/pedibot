"""The guide an answer should send the reader to (5-sep-2026).

An answer is four sentences. The guide on the same subject is eight hundred words with the same
sources at the bottom, and until now nothing connected the two: somebody could ask about fever,
get an answer, and never learn that a whole page about fever exists on the site they are on.

**How the guide is chosen.** Not by keywords in the question — by the DOCUMENTS. Every answer
records which chunks it used, and every guide topic declares which documents it was written from.
The guide to link is the one built out of the same material the answer just quoted, which is a
claim we can actually defend: the page it opens says the same things with the same sources.

Keywords were the obvious alternative and they are worse. "My son has a rash after the vaccine"
is about vaccines, or about rashes, depending on which word you weigh — and a wrong guide under
a right answer reads like the site does not know what it is talking about.

What counts is how MUCH of each document the answer used, not whether it touched it. That is the
difference between the subject and a passing mention: a Russian fever answer quoted the fever
sheet twice and the heat-stroke sheet once, for one "when to consult" line, and the first version
of this offered the reader the guide to heat stroke. Remaining ties break on the words of the
question that appear in the guide's own title, then on how much of the guide's material was used,
then on the more specific guide.

When nothing overlaps there is no link: a related-looking guide is not worth the click, and this
is a health site.
"""

from __future__ import annotations

import functools
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class GuideLink:
    """A published guide, ready to put under an answer."""

    topic: str
    slug: str
    title: str
    lang: str

    @property
    def url(self) -> str:
        """English is served from the root of the site; the rest carry their prefix."""
        prefix = "" if self.lang == "en" else f"/{self.lang}"
        return f"{prefix}/guides/{self.slug}"


_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_WORD = re.compile(r"\w{4,}", re.UNICODE)


@functools.lru_cache(maxsize=1)
def _docs_by_topic() -> dict[str, list[str]]:
    """Imported here and not at the top: `publish.articles` imports `bot.answer`, which imports
    this module, and a module-level import would close the circle."""
    from pedibot.publish.articles import TOPIC_PLAN

    out: dict[str, list[str]] = {}
    for topic, plan in TOPIC_PLAN.items():
        docs = plan.get("docs", [])
        if isinstance(docs, list):
            out[topic] = [str(d) for d in docs]
    return out


class GuideIndex:
    """Every published guide, read once from the folder `pedibot publish` writes into."""

    def __init__(self, content_dir: Path) -> None:
        self.by_lang: dict[str, list[GuideLink]] = {}
        if not content_dir.is_dir():
            return
        for d in sorted(content_dir.iterdir()):
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md")):
                m = _FRONTMATTER.match(f.read_text(encoding="utf-8"))
                if not m:
                    continue
                try:
                    meta = yaml.safe_load(m.group(1)) or {}
                except yaml.YAMLError:
                    continue
                if meta.get("draft") or not meta.get("topic") or not meta.get("title"):
                    continue
                lang = str(meta.get("lang") or d.name)
                self.by_lang.setdefault(lang, []).append(
                    GuideLink(str(meta["topic"]), f.stem, str(meta["title"]), lang)
                )

    def __len__(self) -> int:
        return sum(len(v) for v in self.by_lang.values())

    def best_for(self, chunk_ids: list[str], lang: str, query: str = "") -> GuideLink | None:
        """The guide written from the documents this answer cited, or nothing."""
        guides = self.by_lang.get(lang)
        if not guides or not chunk_ids:
            return None
        # "seup_fiebre#3" → "seup_fiebre", counted: how MUCH of each document the answer used is
        # the difference between the subject and a passing mention. A Russian fever answer quoted
        # the fever sheet twice and the heat-stroke sheet once, for its "when to consult" line —
        # and offered the reader the guide to heat stroke.
        weight = Counter(c.split("#", 1)[0] for c in chunk_ids)
        asked = set(_WORD.findall(query.lower()))
        plans = _docs_by_topic()

        best: tuple[int, int, float, int] | None = None
        pick: GuideLink | None = None
        for g in guides:
            docs = plans.get(g.topic)
            if not docs:
                continue
            shared = [d for d in docs if d in weight]
            if not shared:
                continue
            key = (
                sum(weight[d] for d in shared),  # how much material in common
                # words of the question that appear in the guide's own title
                len(asked & set(_WORD.findall(g.title.lower()))),
                len(shared) / len(docs),  # how much of the guide it covers
                -len(docs),  # the more specific guide
            )
            if best is None or key > best:
                best, pick = key, g
        return pick
