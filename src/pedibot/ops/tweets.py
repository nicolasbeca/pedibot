"""Seven tweets about PediBot, once a week, for the operator to copy and paste (6-sep-2026).

He asked for more exposure and this is the cheapest lever he has: an account he already posts
from. The job writes the drafts; a person still decides what goes out.

**The rule that shapes everything here is that a tweet is a public claim.** The site's whole
argument is that it does not guess, so a tweet that inflates a number or invents a credential
costs more than the reach it buys. So the model never writes from memory:

  1. `facts()` measures the project — guides, documents, organisations, languages, calendars —
     by counting them, right now, in this deployment.
  2. The model is given those facts and told it may use no others.
  3. `problems()` reads every draft back and rejects it if it carries a number that is not in the
     fact sheet, claims a review that never happened, or breaks the length. Rejected drafts are
     re-asked for once and then dropped: six good tweets beat seven with one lie in it.

English, and no links: the operator's calls, 6-sep. No link means each tweet has to be worth
reading on its own, which is the right constraint anyway — and X buries posts that send people
away. Previously sent drafts are remembered so the same line does not come back next Sunday.
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import pathlib
import re
import sqlite3
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pedibot.bot.llm import LLMProvider

#: X's limit. A draft longer than this is not a tweet, whatever else it is.
MAX_CHARS = 280

#: What the site is not, and must never be said to be. No clinician has reviewed the guides —
#: that is a standing rule of this project, and it is the one lie that would matter.
FORBIDDEN = re.compile(
    r"\b(doctor|physician|paediatrician|pediatrician|clinician|expert|specialist)[- ]?"
    r"(reviewed|approved|checked|verified|vetted|written)"
    r"|\breviewed by\b|\bapproved by\b|\bvetted by\b"
    r"|\bdiagnos(e|es|is|ing)\b"
    r"|\bmedical advice\b"
    r"|\b(safe|accurate|correct|reliable)\s+(always|guaranteed)\b"
    r"|\bguarantee(d|s)?\b",
    re.I,
)

#: The operator posts without links (6-sep). A draft that smuggles one back is not what he asked
#: for, and on X it also costs the post its reach.
HAS_LINK = re.compile(r"https?://|\bwww\.|pedibot\.xyz", re.I)


def facts(root: pathlib.Path, index_db: pathlib.Path) -> dict[str, Any]:
    """Everything a tweet is allowed to assert, counted here and now.

    Nothing in here is a stored constant: a guide published this week, a language added, a source
    dropped from the corpus, and next Sunday's tweets say the new number without anybody editing
    a prompt. That is the point — the alternative is a number in a template that quietly goes
    stale and starts being false.
    """
    import yaml

    per_lang = collections.Counter(
        p.parent.name for p in (root / "web" / "content").rglob("*.md")
    )
    con = sqlite3.connect(index_db)
    orgs: collections.Counter[str] = collections.Counter()
    docs: set[str] = set()
    for (raw,) in con.execute("SELECT data FROM chunks"):
        d = json.loads(raw)
        orgs[d.get("org")] += 1
        docs.add(d.get("doc_id"))
    con.close()

    vax = yaml.safe_load((root / "config" / "vaccines.yaml").read_text(encoding="utf-8"))
    drugs = yaml.safe_load((root / "config" / "drugs.yaml").read_text(encoding="utf-8"))["drugs"]

    # real headlines, so a tweet can quote a question the site actually answers instead of
    # inventing a plausible-sounding one
    titles: list[str] = []
    for p in sorted((root / "web" / "content" / "en").glob("*.md")):
        m = re.search(r'^title:\s*"?(.+?)"?\s*$', p.read_text(encoding="utf-8"), re.M)
        if m:
            titles.append(m.group(1))

    return {
        "guides": sum(per_lang.values()),
        "guides_per_language": dict(sorted(per_lang.items())),
        "languages": len(per_lang),
        "documents": len(docs),
        "organisations": len(orgs),
        "organisation_names": [o for o, _ in orgs.most_common(10) if o],
        "vaccine_countries": len(vax["countries"]),
        "vaccine_country_codes": sorted(vax["countries"]),
        "medicines_in_the_dose_calculator": len(drugs),
        "guide_titles_english": titles,
    }


def allowed_numbers(f: dict[str, Any]) -> set[str]:
    """Every number a draft may contain, taken from the fact sheet itself.

    Anything else is either invented or a medical figure — a dose, an age, a temperature — and
    neither belongs in a tweet written by a model.
    """
    out: set[str] = set()

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for k, x in v.items():
                out.add(str(k)) if str(k).isdigit() else None
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, int) and not isinstance(v, bool):
            out.add(str(v))
        elif isinstance(v, str):
            out.update(re.findall(r"\d+", v))

    walk(f)
    return out


def fact_sheet(f: dict[str, Any]) -> str:
    """The facts as the model sees them, and the only ones it may use."""
    g = f["guides_per_language"]
    return "\n".join(
        [
            f"- {f['guides']} guides, written in {f['languages']} languages",
            "- guides per language: " + ", ".join(f"{k} {v}" for k, v in g.items()),
            f"- built from {f['documents']} published documents by {f['organisations']} bodies,"
            f" including {', '.join(f['organisation_names'][:6])}",
            f"- vaccination schedules for {f['vaccine_countries']} countries:"
            f" {', '.join(f['vaccine_country_codes'])}",
            f"- a weight-based dose calculator for {f['medicines_in_the_dose_calculator']}"
            " medicines",
            "- every statement in a guide carries the number of the document it came from, and",
            "  the documents are listed at the foot with organisation, title and page",
            "- when no source covers the question, it says so instead of answering",
            "- free, no adverts, no account, no third-party trackers",
            "- it reads the question for warning signs first and says when to stop reading",
            "  and seek care",
            "- real guide titles you may quote verbatim:",
            *(f"  · {t}" for t in f["guide_titles_english"][:40]),
        ]
    )


SYSTEM = """You write posts for X (Twitter) about PediBot, a free paediatric question-answering \
site that only answers from published clinical guidelines and shows which document each statement \
came from.

Voice: plain, specific, unexcited. You are one person who built a thing, not a brand. No emoji, \
no hashtags, no "🚀", no "Introducing", no "game-changer", no rhetorical questions used as hooks. \
A good post is a fact a parent or a developer would find worth knowing even if they never visit \
the site. A bad post is an advertisement.

HARD RULES, and a post that breaks one is thrown away:
- Every number you use must appear in the FACTS below. Never invent, round, or estimate one.
- Never state a dose, an age threshold, or a temperature. Not one.
- Never say or imply that a doctor, paediatrician or any clinician reviewed, approved or wrote \
anything. Nobody has. Saying so would be the one lie that matters.
- Never promise accuracy, safety or a diagnosis.
- No links, no URLs, no @handles.
- At most 280 characters each, counted exactly.
- Each post must stand alone. No threads, no numbering, no "1/7".

Return exactly the posts asked for, one per line, nothing else: no numbering, no quotation \
marks, no commentary, no blank lines between them."""


def problems(text: str, ok_numbers: set[str]) -> list[str]:
    """Why this draft cannot be sent. Empty means it can."""
    out: list[str] = []
    t = text.strip()
    if not t:
        return ["vacío"]
    if len(t) > MAX_CHARS:
        out.append(f"{len(t)} caracteres, el límite es {MAX_CHARS}")
    if HAS_LINK.search(t):
        out.append("lleva enlace y se pidió sin enlaces")
    if m := FORBIDDEN.search(t):
        out.append(f"afirmación prohibida: «{m.group(0)}»")
    if "@" in t:
        out.append("menciona una cuenta")
    unknown = sorted({n for n in re.findall(r"\d+", t) if n not in ok_numbers})
    if unknown:
        out.append(f"números que no están en los datos medidos: {unknown}")
    return out


def _split(raw: str) -> list[str]:
    """One draft per line, with the shapes a model reaches for stripped off."""
    out: list[str] = []
    for line in raw.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        line = line.strip('"“”')
        if len(line) > 25:
            out.append(line)
    return out


def write_batch(
    llm: LLMProvider,
    f: dict[str, Any],
    n: int = 7,
    already_sent: tuple[str, ...] = (),
) -> tuple[list[str], list[str]]:
    """(the drafts that survived, the reasons the others did not).

    Asks for more than it needs, because the verifier throws some away and coming back with six
    good posts is a better outcome than seven with an invented number in one of them. It asks
    twice at most: a model that has already failed the same rules twice is not going to be
    argued into it a third time, and this runs unattended.
    """
    ok_numbers = allowed_numbers(f)
    sheet = fact_sheet(f)
    avoid = (
        "\n\nYou have already used these, so write different ones:\n"
        + "\n".join(f"- {t}" for t in already_sent[-40:])
        if already_sent
        else ""
    )
    kept: list[str] = []
    rejected: list[str] = []
    seen = {t.strip().lower() for t in already_sent}
    for _attempt in range(2):
        want = n - len(kept)
        if want <= 0:
            break
        user = (
            f"FACTS (the only ones you may use):\n{sheet}{avoid}\n\n"
            f"Write {want + 3} posts. Make them different from each other: one about the "
            "sourcing, one about the languages, one a real guide title quoted verbatim followed "
            "by what the site does with it, one about what it refuses to do, and the rest free."
        )
        raw = llm.complete(SYSTEM, user, temperature=0.9, max_tokens=1200).text
        for draft in _split(raw):
            if len(kept) >= n:
                break
            key = draft.strip().lower()
            if key in seen:
                rejected.append(f"repetido: {draft[:60]}")
                continue
            if bad := problems(draft, ok_numbers):
                rejected.append(f"{'; '.join(bad)} → {draft[:60]}")
                continue
            seen.add(key)
            kept.append(draft)
        if len(kept) >= n:
            break
    return kept, rejected


# ---- the memory of what has gone out ----------------------------------------------------------


def history_path(root: pathlib.Path) -> pathlib.Path:
    return root / "data" / "tweets_sent.jsonl"


def load_history(root: pathlib.Path) -> list[str]:
    p = history_path(root)
    if not p.exists():
        return []
    out: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(str(json.loads(line)["text"]))
            except (json.JSONDecodeError, KeyError):
                continue
    return out


def remember(root: pathlib.Path, drafts: list[str]) -> None:
    p = history_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    day = dt.date.today().isoformat()
    with p.open("a", encoding="utf-8", newline="\n") as fh:
        for t in drafts:
            fh.write(json.dumps({"date": day, "text": t}, ensure_ascii=False) + "\n")
