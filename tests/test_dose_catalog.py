"""El catálogo de dosis, comprobado entero (6-sep-2026).

Es la única parte de la web donde una cifra mal puesta se convierte en una dosis mal puesta. El
6-sep se tocó bastante: la calculadora entró en las ocho páginas de medicamento, el título cambió
en ocho idiomas y se añadieron diecisiete nombres comerciales. Estas comprobaciones son el repaso
que se hizo entonces, convertido en candado.

Qué buscan, y por qué cada una:

  · Una marca colgando del principio activo equivocado. El fichero llevaba —como apunte suelto de
    quien lo escribió— una entrada «Dalsy (no, Dalsy is ibuprofen)» dentro de la lista de
    PARACETAMOL. No llegaba a verse, pero un recordatorio disfrazado de dato, en un fichero que
    decide dosis de niños, es justo lo que hay que impedir.
  · Un mismo nombre apuntando a dos fármacos: quien preguntase por él recibiría una respuesta u
    otra según el orden del diccionario, que es azar.
  · Una concentración de marca que no exista entre las del fármaco, que daría una tabla imposible.
  · Un producto que no se dosifica en casa. Perfalgan es paracetamol INTRAVENOSO, de hospital:
    reconocerlo haría que a quien pregunta por un vial le respondiéramos con la dosis de un jarabe.
  · Y que las ocho páginas sigan siendo la misma página, con la calculadora que su título promete.
"""

from __future__ import annotations

import collections
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAT = yaml.safe_load((ROOT / "config" / "drugs.yaml").read_text(encoding="utf-8"))["drugs"]
TPLS = sorted((ROOT / "web" / "site" / "src" / "pages").glob("**/dose/[[]slug[]].astro"))

#: qué es cada nombre comercial, de verdad
PARACETAMOL = {
    "apiretal", "termalgin", "gelocatil", "efferalgan", "doliprane", "tachipirina",
    "panadol", "tylenol", "calpol", "tempra", "ben", "ben-u-ron", "benuron",
}
IBUPROFENO = {
    "dalsy", "junifen", "nurofen", "advil", "motrin", "alivium", "apirofeno",
    "nureflex", "brufen", "algifor", "ibufen",
}

#: no se dosifican en casa, así que no deben reconocerse
NO_DOMICILIARIOS = {"perfalgan", "propacetamol"}

_STRENGTH = re.compile(r"(\d+(?:[.,]\d+)?)\s*mg\s*/\s*(\d+)?\s*ml")


def _names() -> set[str]:
    out: set[str] = set()
    for drug in CAT.values():
        out.update(str(a).lower() for a in drug.get("aliases", []))
        out.update(str(b["name"]).lower() for b in drug.get("brands", []))
    return out


def test_no_brand_hangs_from_the_wrong_active_ingredient() -> None:
    bad: list[str] = []
    for key, drug in CAT.items():
        for b in drug.get("brands", []):
            n = str(b["name"]).lower()
            if key == "paracetamol" and n in IBUPROFENO:
                bad.append(f"«{b['name']}» es ibuprofeno y está bajo paracetamol")
            if key == "ibuprofen" and n in PARACETAMOL:
                bad.append(f"«{b['name']}» es paracetamol y está bajo ibuprofeno")
    assert not bad, "\n".join(bad)


def test_no_name_points_at_two_medicines() -> None:
    """Un nombre en dos fármacos se resolvería por el orden del diccionario, que es azar."""
    where: dict[str, list[str]] = collections.defaultdict(list)
    for key, drug in CAT.items():
        for a in drug.get("aliases", []):
            where[str(a).lower()].append(key)
        for b in drug.get("brands", []):
            where[str(b["name"]).lower()].append(key)
    bad = [f"«{n}» → {sorted(set(k))}" for n, k in where.items() if len(set(k)) > 1]
    assert not bad, "\n".join(bad)


def test_a_hospital_only_product_is_not_recognised() -> None:
    """Perfalgan es paracetamol intravenoso. Estuvo un momento en la lista de alias el 6-sep y
    salió de ella: responder con la dosis de un jarabe a quien pregunta por un vial es peor que
    no reconocer el nombre."""
    found = _names() & NO_DOMICILIARIOS
    assert not found, f"reconoce productos que no se dosifican en casa: {sorted(found)}"


def test_every_brand_strength_exists_in_its_medicine() -> None:
    bad: list[str] = []
    for key, drug in CAT.items():
        strengths = set(drug.get("strengths_mg_per_ml", []))
        for b in drug.get("brands", []):
            for f in b.get("forms", []):
                m = _STRENGTH.search(str(f))
                assert m, f"[{key}] «{b['name']}»: no se puede leer la concentración de «{f}»"
                mg = float(m.group(1).replace(",", "."))
                ml = float(m.group(2)) if m.group(2) else 1.0
                per_ml = mg / ml
                if per_ml not in strengths and round(per_ml) not in strengths:
                    bad.append(
                        f"[{key}] «{b['name']}» {f} = {per_ml:g} mg/ml, "
                        f"que no está en {sorted(strengths)}"
                    )
    assert not bad, "\n".join(bad)


def test_the_ceilings_agree_with_each_other() -> None:
    bad: list[str] = []
    for key, drug in CAT.items():
        lo, hi = drug["per_dose_mg_per_kg"]
        if lo > hi:
            bad.append(f"[{key}] la dosis por kilo va al revés: {lo}-{hi}")
        if drug["max_single_mg"] > drug["max_daily_mg"]:
            bad.append(f"[{key}] una sola toma supera el máximo del día")
        if hi * (24 / drug["interval_hours"][0]) < drug["max_mg_per_kg_day"]:
            bad.append(f"[{key}] el máximo diario es inalcanzable con su propio intervalo")
    assert not bad, "\n".join(bad)


def test_the_eight_medicine_pages_are_still_the_same_page() -> None:
    assert len(TPLS) == 8, f"hay {len(TPLS)} plantillas de medicamento, no 8"
    bad: list[str] = []
    for t in TPLS:
        src = t.read_text(encoding="utf-8")
        for needed in ("<DoseCalc", "drug={name}", "dosedrug_title", "weightTable"):
            if needed not in src:
                bad.append(f"{t.parent.parent.name}/{t.name}: falta {needed}")
    assert not bad, "\n".join(bad)


def test_the_title_promises_a_calculator_in_every_language() -> None:
    """Prometerla sin llevarla sería falso. Llevarla sin decirlo deja fuera la palabra que la
    gente escribe: «calculadora apiretal» es la consulta que más nos muestra sin ser de marca."""
    i18n = (ROOT / "web" / "site" / "src" / "i18n.ts").read_text(encoding="utf-8")
    word = {
        "en": "calculator", "es": "Calculadora", "fr": "Calculateur", "de": "rechner",
        "ru": "Калькулятор", "ar": "حاسبة", "pt": "Calculadora", "hi": "कैलकुलेटर",
    }
    bad: list[str] = []
    for lang, w in word.items():
        m = re.search(rf"\n  {lang}: \{{.*?dosedrug_title: (['\"])(.*?)\1", i18n, re.S)
        if not m:
            bad.append(f"[{lang}] no hay dosedrug_title")
        elif w.lower() not in m.group(2).lower():
            bad.append(f"[{lang}] el título no dice calculadora: «{m.group(2)}»")
    assert not bad, "\n".join(bad)
