"""Brand/alias catalogue for the dose calculator (`config/drugs.yaml`). The arithmetic stays in
`dose.py`; this module resolves what the parent typed ("Calpol", "Tylenol", "Dalsy") to a molecule
and lists the liquid strengths sold under that name in their country."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_STRENGTH = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*mg\s*/\s*(\d+(?:[.,]\d+)?)?\s*ml", re.I
)  # "100 mg/ml" → 1 ml


@dataclass(frozen=True)
class Brand:
    name: str
    countries: tuple[str, ...]
    forms: tuple[str, ...]

    def strengths_mg_per_ml(self) -> list[tuple[str, float]]:
        out = []
        for f in self.forms:
            m = _STRENGTH.search(f)
            if m:
                mg = float(m.group(1).replace(",", "."))
                ml = float((m.group(2) or "1").replace(",", "."))
                out.append((f, round(mg / ml, 3)))
        return out


@dataclass(frozen=True)
class DrugInfo:
    key: str
    generic: dict[str, str]
    aliases: tuple[str, ...]
    brands: tuple[Brand, ...]
    notes: dict[str, str]
    source: str


class DrugCatalog:
    def __init__(self, path: Path):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))["drugs"]
        self.drugs: dict[str, DrugInfo] = {}
        for key, d in raw.items():
            brands = tuple(
                Brand(b["name"], tuple(b.get("countries", [])), tuple(b.get("forms", [])))
                for b in d.get("brands", [])
                if not b.get("hidden")
            )
            self.drugs[key] = DrugInfo(
                key,
                dict(d["generic"]),
                tuple(str(a).lower() for a in d.get("aliases", [])),
                brands,
                dict(d.get("notes", {})),
                str(d["source"]),
            )

    def resolve(self, name: str) -> tuple[str, Brand | None] | None:
        """'calpol' → ('paracetamol', Brand Calpol); 'ibuprofeno' → ('ibuprofen', None)."""
        n = name.strip().lower()
        # El árabe pega el artículo a la palabra: «الباراسيتامول» es «باراسيتامول» con ال delante.
        candidatos = {n, n[2:]} if n.startswith("ال") and len(n) > 4 else {n}
        for key, d in self.drugs.items():
            # TODOS los idiomas del catálogo, no solo el inglés y el español: hasta el
            # 7-sep-2026 comparaba con dos de los ocho, así que «парацетамол» o «पैरासिटामोल»
            # no resolvían aunque el nombre estuviera escrito en la ficha.
            genericos = {str(v).lower() for v in d.generic.values()}
            exactos = {key} | set(d.aliases) | genericos
            if candidatos & exactos:
                return key, None
            # El ruso declina: un padre escribe «сколько парацетамолА», no el nominativo suelto.
            # Por raíz, y solo contra nombres largos, que no pescan de más.
            if any(c.startswith(g) for c in candidatos for g in genericos if len(g) >= 8):
                return key, None
        for key, d in self.drugs.items():
            for b in d.brands:
                first = b.name.lower().split(" ")[0].split("/")[0]
                if n == b.name.lower() or n == first or n.startswith(first) and len(first) >= 4:
                    return key, b
        return None

    def brands_for(self, key: str, country: str | None = None) -> list[Brand]:
        """Las marcas de esa molécula, o ninguna si no se la conoce por ese nombre.

        20-sep-2026: esto reventaba con un `KeyError` ante una clave desconocida, y la misma
        molécula llega por dos nombres —el catálogo la llama «ibuprofen» y el resto del código
        «ibuprofeno»—. Una consulta que no encuentra nada devuelve nada; no tumba la calculadora
        de dosis, que es de lo último que puede caerse en esta web.
        """
        d = self.drugs.get(key) or self.drugs.get(key.lower())
        if d is None:
            return []
        bs = list(d.brands)
        if country:
            c = country.upper()
            bs.sort(key=lambda b: (c not in b.countries, b.name))
        return bs

    def all_names(self) -> list[str]:
        names: list[str] = []
        for d in self.drugs.values():
            names.append(d.generic["en"])
            names.extend(b.name for b in d.brands)
        return names
