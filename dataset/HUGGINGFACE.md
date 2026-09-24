---
license: cc0-1.0
language:
  - en
  - es
  - fr
  - de
  - ru
  - ar
  - pt
  - hi
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

**645 documents from 21 organisations**, in 8 languages, each classified by topic and linked to
its original. CC0: take it.

Guidance written for parents — what to do when a child has a fever, when to worry about a rash,
how to rehydrate after vomiting — is published by health services, medical societies and health
ministries across a dozen countries. It is public, it is good, and it is scattered: there was no
single machine-readable index of it. This is one.

## What is in here, and what is not

**In:** the catalogue. Organisation, full name of the organisation, document title, year,
language, topic, document type, the URL of the original, and `usage` — whether that document
may be reproduced (`publico`) or only cited and linked (`citar_solo`). The licence itself is
the one its organisation publishes; `usage` is what it means in practice.

**Not in:** the documents themselves, or any text extracted from them. They belong to the NHS,
the WHO, the CDC, the AAP, the RKI and the rest. Pointing at them is a service to their authors;
copying them would not be. Follow the `url` column to the source. Three further documents in the
corpus cannot be redistributed at all; they are not listed here.

## Where it comes from

It is the index of a working service: [PediBot](https://pedibot.xyz) answers parents' questions
using only these documents and cites the one each sentence came from. The catalogue is generated
from the same files the service runs on, so it is not a snapshot someone curated once — it is
what the system is actually reading today.

Code: [github.com/nicolasbeca/pedibot](https://github.com/nicolasbeca/pedibot) (AGPL-3.0),
archived on Zenodo with DOI [10.5281/zenodo.22932517](https://doi.org/10.5281/zenodo.22932517).

## Using it

```python
from datasets import load_dataset

d = load_dataset("csv", data_files="sources.csv")["train"]
print(d[0]["org"], d[0]["title"], d[0]["usage"], d[0]["url"])

# every organisation in the catalogue
print(sorted(set(d["org"])))
```

## Licence

The catalogue — the selection, the classification, the topic taxonomy and the metadata — is
dedicated to the public domain under [CC0 1.0](LICENSE). The documents it points at are not: each
row carries its organisation and its `usage`, and the licence that governs a document is the one
its organisation publishes.

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

⚠️ This is a catalogue of health information, not health advice. Nothing here replaces a doctor.
