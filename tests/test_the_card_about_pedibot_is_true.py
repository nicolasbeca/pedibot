"""La ficha que el chat lee sobre sí mismo tiene que ser verdad (22-sep-2026).

`config/sobre_pedibot.md` se le enseña al padre como si fuera cierta: si ahí dice que hay una
calculadora de dosis, la página tiene que existir; si dice que habla ocho idiomas, tienen que ser
los ocho del motor; si dice 24 horas de memoria, tiene que ser lo que el servidor borra. Una
ficha que envejece mal es peor que no tener ficha, porque nadie la mira otra vez.

Los números no se prueban aquí porque no están escritos: son huecos que el motor rellena.
"""

from __future__ import annotations

import re

from pedibot.bot.about import FICHA, ficha_de
from pedibot.bot.answer import SUPPORTED_LANGS
from pedibot.bot.dose import DRUGS
from pedibot.ops.store import OpsStore
from pedibot.settings import ROOT

TEXTO = FICHA.read_text(encoding="utf-8")


def test_every_page_it_names_exists() -> None:
    paginas = set(re.findall(r"pedibot\.xyz/([a-z]+)", TEXTO))
    for p in sorted(paginas):
        raiz = ROOT / "web" / "site" / "src" / "pages"
        assert (raiz / f"{p}.astro").exists() or (raiz / p).is_dir(), p


def test_it_names_the_eight_languages_the_engine_has() -> None:
    nombres = {
        "es": "Spanish",
        "en": "English",
        "fr": "French",
        "de": "German",
        "ru": "Russian",
        "ar": "Arabic",
        "pt": "Portuguese",
        "hi": "Hindi",
    }
    dichos = {n for lang, n in nombres.items() if n in TEXTO}
    assert dichos == {nombres[x] for x in SUPPORTED_LANGS}
    assert "eight languages" in TEXTO


def test_the_dose_calculator_has_the_drugs_it_promises() -> None:
    import yaml

    catalogo = yaml.safe_load((ROOT / "config" / "drugs.yaml").read_text(encoding="utf-8"))
    assert set(catalogo["drugs"]) == {"paracetamol", "ibuprofen"}
    assert {"paracetamol", "ibuprofen"} <= set(DRUGS)
    assert "paracetamol and ibuprofen" in TEXTO


def test_the_memory_it_promises_is_the_one_the_server_deletes() -> None:
    assert OpsStore.TURN_TTL_HOURS == 24
    assert "24 hours" in TEXTO


def test_the_holes_are_filled_and_none_is_left() -> None:
    f = ficha_de(docs=570, rules=92, countries=91, vax=66)
    assert "{" not in f and "}" not in f
    for n in ("570", "92", "91", "66"):
        assert n in f
