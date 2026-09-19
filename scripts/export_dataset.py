"""Build the open catalogue of paediatric guidance documents, ready to publish (4-sep-2026).

The problem this dataset answers is real and boring: paediatric guidance for parents is scattered
across health services, medical societies and ministries in a dozen countries, in several
languages, and there is no single machine-readable index of it. Building one took months of
reading. Handing it over costs nothing and is the kind of thing people link to — which is the
actual bottleneck for the site (over 30 days: 27 arrivals from Google, and almost no inbound
links anywhere).

**Metadata only, and deliberately.** Organisation, title, year, language, topic and the link to
the original. Never the extracted text: those documents belong to the NHS, the WHO, the CDC and
the rest, and a catalogue that points at them is a service to their authors while a copy of them
would be a theft. The catalogue itself — the classification, the topic taxonomy, the curation —
is ours to give away.

Generated, not hand-written, for the same reason as llms.txt: a hand-maintained index drifts.
"""

from __future__ import annotations

import collections
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCES = ROOT / "web" / "site" / "public" / "sources.json"
OUT = ROOT / "dataset"

FIELDS = ["doc_id", "org", "org_full", "title", "year", "lang", "topic", "doc_type", "url", "notes"]


def main() -> int:
    raw = json.loads(SOURCES.read_text(encoding="utf-8"))
    docs = [d for d in raw if d.get("usage") != "excluido"]
    OUT.mkdir(exist_ok=True)

    # --- the data, two ways -------------------------------------------------------------------
    rows = [{k: (d.get(k) or "") for k in FIELDS} for d in docs]
    rows.sort(key=lambda r: (r["org"], r["title"]))

    with (OUT / "sources.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    (OUT / "sources.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    # --- the shape of it, for the README -------------------------------------------------------
    by_org = collections.Counter(d["org"] for d in rows)
    by_lang = collections.Counter(d["lang"] for d in rows)
    by_topic = collections.Counter(d["topic"] for d in rows)
    with_url = sum(1 for d in rows if d["url"])
    with_year = sum(1 for d in rows if d["year"])

    LANG_NAME = {
        "es": "Spanish",
        "en": "English",
        "fr": "French",
        "de": "German",
        "ru": "Russian",
        "ar": "Arabic",
        "pt": "Portuguese",
        "it": "Italian",
    }

    lines: list[str] = [
        "# Paediatric guidance for parents — an open catalogue",
        "",
        f"**{len(rows)} documents from {len(by_org)} organisations**, in "
        f"{len(by_lang)} languages, each classified by topic and linked to its original.",
        "",
        "Guidance written for parents — what to do when a child has a fever, when to worry about",
        "a rash, how to rehydrate after vomiting — is published by health services, medical",
        "societies and health ministries across a dozen countries. It is public, it is good, and",
        "it is scattered: there is no single machine-readable index of it. This is one.",
        "",
        "## What is in here, and what is not",
        "",
        "**In:** the catalogue. Organisation, full name of the organisation, document title, year,",
        "language, topic, document type and the URL of the original.",
        "",
        "**Not in:** the documents themselves, or any text extracted from them. They belong to",
        "the NHS, the WHO, the CDC, the AAP, the RKI and the rest. Pointing at them is a service",
        "to their authors; copying them would not be. Follow the `url` column to the source.",
        "",
        "## Files",
        "",
        "| file | what it is |",
        "|---|---|",
        "| `sources.csv` | the catalogue, one row per document |",
        "| `sources.json` | the same, as an array of objects |",
        "",
        "## Columns",
        "",
        "| column | notes |",
        "|---|---|",
        "| `doc_id` | stable identifier, unique in this catalogue |",
        "| `org` / `org_full` | the publisher, short and full |",
        "| `title` | as published, in the document's own language — never translated |",
        f"| `year` | where the document states one ({with_year} of {len(rows)} do) |",
        "| `lang` | ISO 639-1 of the document itself |",
        "| `topic` | our classification, see below |",
        "| `doc_type` | e.g. `hoja_padres` (parent leaflet), `guia_clinica`, `ficha_tecnica` |",
        f"| `url` | link to the original ({with_url} of {len(rows)} are online; the rest are books "
        "and printed manuals, identified in `notes`) |",
        "| `notes` | ISBN, edition, or how to find a document that has no URL |",
        "",
        "## By organisation",
        "",
        "| organisation | documents |",
        "|---|---|",
    ]
    for org, n in by_org.most_common():
        # The commonest spelling, not the first one in the file: SEUP has 28 documents under its
        # plain name and one under "(Grupo de Trabajo de Intoxicaciones)", and picking whichever
        # came first put a single working group's name on the whole society.
        spellings = collections.Counter(
            d["org_full"] for d in rows if d["org"] == org and d["org_full"]
        )
        full = spellings.most_common(1)[0][0] if spellings else ""
        lines.append(f"| {org}{f' — {full}' if full and full != org else ''} | {n} |")

    lines += ["", "## By language", "", "| language | documents |", "|---|---|"]
    for lang, n in by_lang.most_common():
        lines.append(f"| {LANG_NAME.get(lang, lang)} (`{lang}`) | {n} |")

    lines += [
        "",
        f"## By topic ({len(by_topic)} topics)",
        "",
        "| topic | documents |",
        "|---|---|",
    ]
    for topic, n in by_topic.most_common():
        lines.append(f"| `{topic}` | {n} |")

    lines += [
        "",
        "## How it was put together",
        "",
        "By reading. Each document was found, checked to be current, classified and linked by",
        "hand. Selection favoured guidance **written for parents** over clinical guidance written",
        "for doctors, and organisations that publish openly and keep what they publish updated.",
        "",
        "It is not exhaustive and does not pretend to be: it is what one project needed to answer",
        "parents' questions without inventing anything. Gaps are real. German has fewer sources",
        "than English because there is genuinely less openly published German material for",
        "parents; Arabic and Russian have fewer still.",
        "",
        "## Where it comes from",
        "",
        "This is the source catalogue behind [PediBot](https://pedibot.xyz), which answers",
        "parents' questions using only these documents and names the document in every clinical",
        "sentence. The catalogue is published separately because it is useful on its own — to",
        "anyone building something similar, and to anyone who wants to check our work.",
        "",
        "The live version is always at <https://pedibot.xyz/sources.json>.",
        "",
        "## Licence",
        "",
        "The catalogue — the classification, the topic taxonomy, the curation — is released under",
        "**CC0 1.0**: use it for anything, no attribution required, though a link back is",
        "appreciated. This applies to the catalogue only. **The documents it points to are the",
        "property of their publishers** and are governed by whatever terms each of them sets.",
        "",
        "## Not medical advice",
        "",
        "This is an index of documents, not medical guidance. Nothing here is a diagnosis and",
        "nothing here replaces a doctor. If a child is unwell, the right move is to ask one.",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")

    (OUT / "LICENSE").write_text(
        "CC0 1.0 Universal — Public Domain Dedication\n"
        "\n"
        "This dedication applies to THE CATALOGUE in this repository: the selection, the\n"
        "classification, the topic taxonomy and the metadata fields.\n"
        "\n"
        "It does NOT apply to the documents the catalogue points at. Those are the property of\n"
        "their respective publishers (NHS, WHO, CDC, AAP, RKI, SEUP, AEP, MedlinePlus and others)\n"
        "and remain governed by the terms each publisher sets.\n"
        "\n"
        "To the extent possible under law, the authors have waived all copyright and related or\n"
        "neighbouring rights to the catalogue. Full text: https://creativecommons.org/publicdomain/zero/1.0/\n",
        encoding="utf-8",
        newline="\n",
    )

    # Y el mismo conjunto, servido por la web (17-sep-2026). Estaba sólo en el repositorio,
    # así que la frase «cualquiera puede cogerlo» era verdad únicamente para quien supiera que
    # existe un repositorio. Ahora se descarga desde la propia portada, que es donde se promete.
    publico = ROOT / "web" / "site" / "public" / "dataset"
    publico.mkdir(parents=True, exist_ok=True)
    for nombre in ("sources.csv", "sources.json", "LICENSE", "README.md"):
        origen = OUT / nombre
        if origen.exists():
            (publico / nombre).write_bytes(origen.read_bytes())
    print(f"  publicado en la web: {publico.relative_to(ROOT)}")

    print(f"{len(rows)} documentos → {OUT}")
    print(f"  organismos: {len(by_org)} · idiomas: {len(by_lang)} · temas: {len(by_topic)}")
    print(f"  con enlace: {with_url}/{len(rows)} · con año: {with_year}/{len(rows)}")
    for f in sorted(OUT.iterdir()):
        print(f"  {f.name:16} {f.stat().st_size:>8,} b")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
