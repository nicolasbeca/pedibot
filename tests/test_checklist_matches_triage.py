"""La lista de urgencias y el triaje son dos copias de la misma idea (9-sep-2026).

`config/er_checklist.yaml` son 34 signos con tres niveles —llamar ahora, acudir hoy, ver al
pediatra— y salen tal cual en la web. `config/red_flags.yaml` son las 35 reglas que deciden lo
mismo en el chat. Se escribieron por separado y nadie las había puesto una al lado de la otra.

Al hacerlo salieron cuatro huecos, y el primero es el que más dice del asunto: la lista enuncia
«**Bebé menor de 3 meses con fiebre**» y esa frase, escrita tal cual, **no disparaba la regla del
lactante** — el lector de edades sacaba el 3 y la comparación es `< 3`.

Los otros tres: un bebé de menos de un mes que rechaza las tomas, la sobredosis de paracetamol
(que no estaba en la lista de productos del envenenamiento, siendo el fármaco que hay en todas
las casas) y la herida que necesita puntos, que no tenía regla ninguna.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]
LISTA = yaml.safe_load((RAIZ / "config" / "er_checklist.yaml").read_text(encoding="utf-8"))
IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")
ORDEN = {"routine": 0, "mental_health": 1, "urgent": 2, "emergency": 3}

#: Los ítems que son referencias a otras secciones y no una situación que un padre describa.
META = ("Fiebre que se acompaña de cualquier signo",)


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


@pytest.mark.parametrize("item", LISTA["items"], ids=lambda i: str(i["es"])[:34])
def test_every_sign_is_written_in_every_language(item: dict) -> None:
    faltan = [lg for lg in IDIOMAS if not str(item.get(lg, "")).strip()]
    assert not faltan, f"«{item['es'][:40]}» sin {faltan}"


@pytest.mark.parametrize("item", LISTA["items"], ids=lambda i: str(i["es"])[:34])
def test_every_sign_declares_a_known_level_and_category(item: dict) -> None:
    assert item.get("level") in LISTA["levels"], f"nivel desconocido: {item.get('level')}"
    assert item.get("cat") in LISTA["categories"], f"categoría desconocida: {item.get('cat')}"


@pytest.mark.parametrize(
    "item",
    [i for i in LISTA["items"] if i["level"] in ("call_now", "go_today")],
    ids=lambda i: str(i["es"])[:34],
)
def test_what_the_list_sends_to_hospital_the_triage_also_sees(triage: Triage, item: dict) -> None:
    """Si la lista dice «ve hoy» y el chat dice «rutina», una de las dos está mal y el padre no
    tiene forma de saber cuál."""
    frase = str(item["es"])
    if frase.startswith(META):
        pytest.skip("es una referencia a otras secciones, no una situación")
    nivel = triage.assess(frase).level
    assert nivel != "routine", f"la lista lo pone en «{item['level']}» y el triaje lo ve rutina"


def test_the_two_lists_are_both_there() -> None:
    """El candado del candado."""
    assert len(LISTA["items"]) >= 30
    reglas = yaml.safe_load((RAIZ / "config" / "red_flags.yaml").read_text(encoding="utf-8"))
    assert len(reglas["rules"]) >= 30
