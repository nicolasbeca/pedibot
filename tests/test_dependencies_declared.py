"""Todo lo que importa el código de producción está declarado, y no de rebote (29-sep-2026).

El 28-sep salieron `eth-account` y `virtuals-acp` porque nada los importaba. Era verdad, pero se
llevaron con ellos **PyJWT**, que `ops/search.py` sí importaba sin haberlo declarado nunca: llegaba
de rebote. La suite pasó —en el PC seguía instalado— y a la mañana siguiente el refresco de Search
Console murió en el servidor con `No module named 'jwt'`.

Lo que se comprueba es la regla, no el caso: cada módulo de terceros que se importa en `src/` y en
`ops/` tiene que salir de una distribución que `pyproject.toml` declara fuera del grupo `dev`,
porque el servidor corre con `uv run --no-dev`.
"""

from __future__ import annotations

import ast
import importlib.metadata as md
import re
import sys
import tomllib

from pedibot.settings import ROOT


def _normal(nombre: str) -> str:
    return re.sub(r"[-_.]+", "-", nombre).lower()


def _declaradas() -> set[str]:
    py = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    specs = list(py.get("dependencies", []))
    for extra in py.get("optional-dependencies", {}).values():
        specs += extra
    return {_normal(re.split(r"[\s\[<>=!~;]", s, maxsplit=1)[0]) for s in specs}


def _importados() -> dict[str, set[str]]:
    locales = {p.stem for p in (ROOT / "ops").glob("*.py")} | {"pedibot", "ops"}
    out: dict[str, set[str]] = {}
    for raiz in (ROOT / "src" / "pedibot", ROOT / "ops"):
        for f in raiz.rglob("*.py"):
            for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
                if isinstance(n, ast.Import):
                    mods = [a.name for a in n.names]
                elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                    mods = [n.module]
                else:
                    continue
                for m in mods:
                    top = m.split(".")[0]
                    if top not in sys.stdlib_module_names and top not in locales:
                        out.setdefault(top, set()).add(str(f.relative_to(ROOT)))
    return out


def test_cada_import_de_terceros_sale_de_una_dependencia_declarada():
    declaradas = _declaradas()
    dists = md.packages_distributions()
    sueltos = []
    for mod, ficheros in sorted(_importados().items()):
        de = {_normal(d) for d in dists.get(mod, [])}
        if not de & declaradas:
            sueltos.append(f"{mod} ({', '.join(sorted(de)) or '¿sin instalar?'}) en {sorted(ficheros)}")
    assert not sueltos, (
        "importados sin declarar en [project] de pyproject.toml; hoy llegan de rebote y se irán "
        "con la dependencia que los trae: " + "; ".join(sueltos)
    )


def test_el_candado_ve_el_caso_que_lo_abrio():
    assert "jwt" in _importados(), "search.py importa jwt dentro de una función: tiene que verse"
