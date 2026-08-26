"""Public-health notices for the home banner (idea 7). Official feeds only, filtered to child health.

Feeds: WHO news (RSS), PAHO (RSS), UK Health Security Agency (Atom), CDC newsroom (RSS).
Output: web/site/src/data/alerts.json — max 3 items from the last 14 days, each with source, title,
link and date. Runs before the daily site build (pedibot-publish.service). Fails soft (empty list).
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

import httpx

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "site" / "src" / "data" / "alerts.json"
FEEDS = [
    ("WHO", "https://www.who.int/rss-feeds/news-english.xml"),
    ("PAHO", "https://www.paho.org/en/rss.xml"),
    ("UKHSA", "https://www.gov.uk/government/organisations/uk-health-security-agency.atom"),
    ("CDC", "https://tools.cdc.gov/api/v2/resources/media/132608.rss"),
]
# A notice qualifies only if it names a child-relevant disease/hazard AND sounds like an event
# (outbreak, alert, rise…) — never statistics, coverage reports or institutional statements.
TOPIC = re.compile(
    r"\b(measles|pertussis|whooping cough|rsv|bronchiolitis|polio|meningitis|meningococcal|scarlet fever|"
    r"hand,? foot|rotavirus|chickenpox|varicella|heat ?wave|extreme heat|heatstroke|mpox|influenza|flu|"
    r"enterovirus|mumps|diphtheria|strep a|group a strep|children|infants?|babies|paediatric|pediatric|newborn)\b",
    re.I,
)
EVENT = re.compile(
    r"\b(outbreak|alert|warning|cases|rise|rising|surge|increase|spread|recall|advice for parents|urges|season)\b",
    re.I,
)
EXCLUDE = re.compile(
    r"official statistics|coverage|research:|statement on|guidance:|report:|annual|weekly|quarterly|"
    r"transparency|older adults|\badults?\b|older people|pregnan",
    re.I,
)
NS = {"a": "http://www.w3.org/2005/Atom"}


def parse(source: str, xml_text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    # RSS 2.0
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        date = (it.findtext("pubDate") or "").strip()
        items.append(
            {"source": source, "title": re.sub(r"<[^>]+>", "", title), "link": link, "date": date}
        )
    # Atom
    for it in root.findall("a:entry", NS):
        title = (it.findtext("a:title", default="", namespaces=NS) or "").strip()
        link_el = it.find("a:link", NS)
        link = link_el.get("href", "") if link_el is not None else ""
        date = (it.findtext("a:updated", default="", namespaces=NS) or "").strip()
        items.append({"source": source, "title": title, "link": link, "date": date})
    return items


def to_date(s: str) -> dt.date | None:
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            return dt.datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    m = re.search(r"\d{4}-\d{2}-\d{2}", s)
    return dt.date.fromisoformat(m.group(0)) if m else None


def main() -> int:
    picked: list[dict[str, str]] = []
    cutoff = dt.date.today() - dt.timedelta(days=14)
    with httpx.Client(
        timeout=25, headers={"User-Agent": "Mozilla/5.0 PediBot-alerts"}, follow_redirects=True
    ) as c:
        for source, url in FEEDS:
            try:
                r = c.get(url)
                r.raise_for_status()
            except Exception as e:  # noqa: BLE001
                print(f"{source}: {e}", file=sys.stderr)
                continue
            for it in parse(source, r.text):
                d = to_date(it["date"])
                t = it["title"]
                if (
                    not t
                    or EXCLUDE.search(t)
                    or not (TOPIC.search(t) and EVENT.search(t))
                    or (d and d < cutoff)
                ):
                    continue
                it["date"] = d.isoformat() if d else ""
                picked.append(it)
    picked.sort(key=lambda x: x["date"], reverse=True)
    seen: set[str] = set()
    out = []
    for it in picked:
        key = re.sub(r"\W+", " ", it["title"].lower())[:60]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
        if len(out) == 3:
            break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} alerts → {OUT}")
    for it in out:
        print(f"  [{it['source']}] {it['date']} {it['title'][:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
