---
license: cc0-1.0
language:
  - ar
  - de
  - en
  - es
  - fr
  - hi
  - pt
  - ru
  - sw
tags:
  - paediatrics
  - child-health
  - health
  - catalogue
  - multilingual
  - digital-public-good
pretty_name: Paediatric guidance for parents — an open catalogue
size_categories:
  - n<1K
configs:
  - config_name: default
    data_files: sources.csv
---

# Paediatric guidance for parents — an open catalogue

**729 documents from 26 organisations**, in 9 languages, each classified by topic and linked to its original.

Guidance written for parents — what to do when a child has a fever, when to worry about
a rash, how to rehydrate after vomiting — is published by health services, medical
societies and health ministries across a dozen countries. It is public, it is good, and
it is scattered: there is no single machine-readable index of it. This is one.

## What is in here, and what is not

**In:** the catalogue. Organisation, full name of the organisation, document title, year,
language, topic, document type, the URL of the original, and `usage` — what may be done
with that document.

**Not in:** the documents themselves, or any text extracted from them. They belong to
the NHS, the WHO, the CDC, the AAP, the RKI and the rest. Pointing at them is a service
to their authors; copying them would not be. Follow the `url` column to the source.

## Files

| file | what it is |
|---|---|
| `sources.csv` | the catalogue, one row per document |
| `sources.json` | the same, as an array of objects |

## Columns

| column | notes |
|---|---|
| `doc_id` | stable identifier, unique in this catalogue |
| `org` / `org_full` | the publisher, short and full |
| `title` | as published, in the document's own language — never translated |
| `year` | where the document states one (341 of 729 do) |
| `lang` | ISO 639-1 of the document itself |
| `topic` | our classification, see below |
| `doc_type` | e.g. `hoja_padres` (parent leaflet), `guia_clinica`, `ficha_tecnica` |
| `usage` | `publico` (698) may be reproduced under its publisher's terms; `citar_solo` (31) may be cited and linked, not reproduced |
| `url` | link to the original (681 of 729 are online; the rest are books and printed manuals, identified in `notes`) |
| `notes` | ISBN, edition, or how to find a document that has no URL |

## By organisation

| organisation | documents |
|---|---|
| WHO — World Health Organization | 220 |
| NHS — NHS (National Health Service, England) | 191 |
| MedlinePlus — MedlinePlus (U.S. National Library of Medicine) | 118 |
| Immunize.org — Immunize.org — translation of the CDC Vaccine Information Statement | 40 |
| RKI — Robert Koch-Institut (Deutschland) | 30 |
| SEUP — Sociedad Española de Urgencias de Pediatría | 29 |
| CDC — Centers for Disease Control and Prevention (USA) | 22 |
| Gouvernement du Canada — Gouvernement du Canada / Government of Canada (santé publique) | 20 |
| Vikaspedia — Vikaspedia (C-DAC, Government of India) | 19 |
| Ministério da Saúde — Ministério da Saúde (Brasil) | 14 |
| AEPap — Familia y Salud — Asociación Española de Pediatría de Atención Primaria | 5 |
| AAP — American Academy of Pediatrics | 4 |
| AEP — Asociación Española de Pediatría — Protocolos de Neonatología (Doménech, González, Rodríguez-Alarcón) | 2 |
| Junta de Andalucía — Consejería de Salud de la Junta de Andalucía | 2 |
| NHM — National Health Mission, Ministry of Health & Family Welfare, Government of India | 2 |
| AEMPS — Agencia Española de Medicamentos y Productos Sanitarios — CIMA (prospecto autorizado) | 1 |
| CAV-AEP — Comité Asesor de Vacunas de la Asociación Española de Pediatría — Manual de Inmunizaciones en línea | 1 |
| College of the Canyons — College of the Canyons — Open Educational Resource (Paris, Ricardo, Rymond) | 1 |
| Ecimed — Editorial Ciencias Médicas (La Habana) | 1 |
| H. Niño Jesús — Hospital Infantil Universitario Niño Jesús (Casado Flores, Jiménez García) | 1 |
| H. U. Donostia — Hospital Universitario Donostia — Comité de Política Antibiótica | 1 |
| Ministerio de Sanidad — Ministerio de Sanidad (España) — Consejo Interterritorial del SNS | 1 |
| NHSRC — National Health Systems Resource Centre, Ministry of Health & Family Welfare, Government of India | 1 |
| PUC Chile — Pontificia Universidad Católica de Chile — Escuela de Medicina | 1 |
| SENeo — Sociedad Española de Neonatología (con la AEPap) | 1 |
| nidirect — nidirect (Northern Ireland Government Services) | 1 |

## By language

| language | documents |
|---|---|
| English (`en`) | 364 |
| Spanish (`es`) | 117 |
| Arabic (`ar`) | 56 |
| French (`fr`) | 51 |
| Russian (`ru`) | 47 |
| German (`de`) | 30 |
| hi (`hi`) | 29 |
| sw (`sw`) | 21 |
| Portuguese (`pt`) | 14 |

## By topic (23 topics)

| topic | documents |
|---|---|
| `vacunas` | 97 |
| `respiratorio` | 77 |
| `general` | 76 |
| `piel` | 74 |
| `digestivo` | 66 |
| `accidentes` | 58 |
| `alimentacion` | 44 |
| `desarrollo` | 38 |
| `salud_mental` | 22 |
| `orl` | 19 |
| `recien_nacido` | 18 |
| `fiebre` | 18 |
| `neurologia` | 17 |
| `medicamentos` | 16 |
| `alergia` | 15 |
| `urgencias` | 14 |
| `crianza` | 14 |
| `ojos` | 12 |
| `intoxicacion` | 11 |
| `dental` | 9 |
| `lactante` | 8 |
| `auto` | 3 |
| `urinario` | 3 |

## How it was put together

By reading. Each document was found, checked to be current, classified and linked by
hand. Selection favoured guidance **written for parents** over clinical guidance written
for doctors, and organisations that publish openly and keep what they publish updated.

It is not exhaustive and does not pretend to be: it is what one project needed to answer
parents' questions without inventing anything. Gaps are real. German has fewer sources
than English because there is genuinely less openly published German material for
parents; Arabic and Russian have fewer still.

## Where it comes from

This is the source catalogue behind [PediBot](https://pedibot.xyz), which answers
parents' questions using only these documents and names the document in every clinical
sentence. The catalogue is published separately because it is useful on its own — to
anyone building something similar, and to anyone who wants to check our work.

The live version is always at <https://pedibot.xyz/sources.json>.

## Licence

The catalogue — the classification, the topic taxonomy, the curation — is released under
**CC0 1.0**: use it for anything, no attribution required, though a link back is
appreciated. This applies to the catalogue only. **The documents it points to are the
property of their publishers** and are governed by whatever terms each of them sets.

## Using it

```python
from datasets import load_dataset

d = load_dataset("csv", data_files="sources.csv")["train"]
print(d[0]["org"], d[0]["title"], d[0]["usage"], d[0]["url"])
```

## Citation

```bibtex
@software{beca_pedibot,
  author    = {Beca, Nicolás},
  title     = {PediBot — a paediatric answer with the source attached},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.22932517},
  url       = {https://pedibot.xyz}
}
```

## Not medical advice

This is an index of documents, not medical guidance. Nothing here is a diagnosis and
nothing here replaces a doctor. If a child is unwell, the right move is to ask one.
