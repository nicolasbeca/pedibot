"""Ningún frente puede llamar al modelo a pelo (7-sep-2026).

PediBot tiene tres frentes sobre el mismo motor: la web, Telegram y el endpoint del agente ACP.
Los tres tienen que cumplir dos reglas, y **los tres se las saltaban**, cada uno descubierto por
separado y con el mismo asombro:

1. **El tope de gasto del día.** Existía solo en el API. Telegram llamaba al modelo con el
   presupuesto agotado; el endpoint del agente también, y encima su docstring decía «same safety
   checks».
2. **Sobrevivir a que el modelo no conteste.** Sin recoger `LLMUnavailable`, una avería de
   DeepSeek es un 500: se pierde el triaje ya hecho, se pierden los pasajes ya recuperados y no
   queda registro de que haya pasado.

Arreglarlos de uno en uno no vale de nada, porque **el cuarto frente volverá a nacer sin ellas**.
Este fichero lee el código con el AST —el árbol de la sintaxis, o sea el propio código, no un
grep— y falla si aparece una llamada a `.ask(` del motor sin su red debajo.

Es el mismo candado que MultiBot tiene sobre `policy.py`, por la misma razón: una regla que hay
que acordarse de aplicar no es una regla.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "pedibot"

#: Ficheros que llaman al motor sin ser un frente de cara al público: la CLI del operador y el
#: evaluador del conjunto dorado. Ahí un fallo del modelo DEBE explotar — es lo que se quiere ver.
NO_SON_FRENTES = {"cli.py", "eval.py"}


def _llamadas_al_motor(arbol: ast.AST) -> list[ast.Call]:
    """Toda llamada `<algo>.ask(...)` donde `<algo>` termina en `engine`."""
    fuera = []
    for n in ast.walk(arbol):
        if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Attribute):
            continue
        if n.func.attr != "ask":
            continue
        obj = n.func.value
        nombre = obj.attr if isinstance(obj, ast.Attribute) else getattr(obj, "id", "")
        if nombre == "engine":
            fuera.append(n)
    return fuera


def _protegida(arbol: ast.AST, llamada: ast.Call) -> bool:
    """¿Está la llamada dentro de un `try` que recoja `LLMUnavailable`?"""
    for n in ast.walk(arbol):
        if not isinstance(n, ast.Try):
            continue
        if not any(llamada is c for c in ast.walk(ast.Module(body=n.body, type_ignores=[]))):
            continue
        for h in n.handlers:
            tipos = (
                h.type
                if isinstance(h.type, ast.Tuple)
                else ast.Tuple(elts=[h.type or ast.Constant(None)])
            )
            for t in tipos.elts:
                if isinstance(t, ast.Name) and t.id == "LLMUnavailable":
                    return True
                if isinstance(t, ast.Attribute) and t.attr == "LLMUnavailable":
                    return True
    return False


def _frentes() -> list[pathlib.Path]:
    fuera = []
    for f in SRC.rglob("*.py"):
        if f.name in NO_SON_FRENTES or "__pycache__" in f.parts:
            continue
        if _llamadas_al_motor(ast.parse(f.read_text(encoding="utf-8"))):
            fuera.append(f)
    return sorted(fuera)


def test_there_is_more_than_one_front() -> None:
    """El candado del candado: si un día no encuentra frentes, es que dejó de buscar bien."""
    nombres = {f.name for f in _frentes()}
    assert {"api.py", "telegram_bot.py"} <= nombres, f"solo se ven estos frentes: {nombres}"


@pytest.mark.parametrize("fichero", _frentes(), ids=lambda f: f.name)
def test_every_front_survives_a_dead_model(fichero: pathlib.Path) -> None:
    codigo = fichero.read_text(encoding="utf-8")
    arbol = ast.parse(codigo)
    sueltas = [c.lineno for c in _llamadas_al_motor(arbol) if not _protegida(arbol, c)]
    assert not sueltas, (
        f"{fichero.name}: engine.ask sin recoger LLMUnavailable en la línea "
        f"{sueltas} — una avería del modelo será un 500 y se perderá el triaje"
    )


@pytest.mark.parametrize("fichero", _frentes(), ids=lambda f: f.name)
def test_every_front_honours_the_daily_spending_cap(fichero: pathlib.Path) -> None:
    """El agujero era de dinero, así que este es el candado que más falta hacía.

    Se comprueba por presencia de la llamada, no por su lógica: un frente que lea el gasto del día
    puede seguir haciéndolo mal, pero uno que ni lo mire está mal seguro."""
    codigo = fichero.read_text(encoding="utf-8")
    assert "cost_today_usd()" in codigo, (
        f"{fichero.name} llama al motor sin mirar el tope de gasto del día: "
        "el freno tendría una puerta abierta al lado (L38)"
    )
