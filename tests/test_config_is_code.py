"""Los ficheros de datos son código, y nadie los comprueba salvo que se le pida (8-sep-2026).

Salió de un fallo real y vivo: `emergency: [urgencias, 112]` en `synonyms.yaml`. Sin comillas, el
cargador de YAML lee `112` como **entero**, el motor hace `" ".join(términos)` y salta un
TypeError que le llega al padre como *Internal Server Error* — para cualquier pregunta en inglés
con la palabra «emergency», en el idioma principal del producto.

No lo encontró ninguno de los 1.800 tests, y no podían: todos ejercitan el motor con ficheros de
prueba o con preguntas que no llevaban esa palabra. Lo encontró medir otra cosa y tropezar con el
tipo del dato.

Esto comprueba los ficheros de verdad, los que se despliegan:

  · que todos cargan,
  · que no hay claves repetidas —YAML se queda con la última **en silencio**, así que una regla
    duplicada en un fichero de 1.600 líneas pierde la primera sin decir nada,
  · que ninguna lista de palabras lleva un número suelto,
  · que ninguna cadena está vacía,
  · y que toda expresión regular compila.
"""

from __future__ import annotations

import pathlib
import re

import pytest
import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "config"
FICHEROS = sorted(CONFIG.glob("*.yaml"))

#: Listas cuyo contenido son palabras que el motor va a unir, comparar o compilar. Un número
#: suelto aquí es un olvido de comillas, no un dato.
LISTAS_DE_TEXTO = {
    "patterns",
    "terms",
    "aliases",
    "forms",
    "keywords",
    "words",
    "markers",
    "topics",
    "subtopics",
    "docs",
    "items",
    "sources",
}


class _Duplicados(yaml.SafeLoader):
    """Cargador que anota las claves repetidas en vez de tragárselas."""

    repetidas: list[tuple[str, int]] = []

    def construct_mapping(self, node, deep=False):  # type: ignore[no-untyped-def]
        vistas: set[str] = set()
        for k, _ in node.value:
            clave = self.construct_object(k, deep=True)
            if isinstance(clave, str):
                if clave in vistas:
                    _Duplicados.repetidas.append((clave, k.start_mark.line + 1))
                vistas.add(clave)
        return super().construct_mapping(node, deep)


def _recorre(nodo: object, ruta: str = ""):  # type: ignore[no-untyped-def]
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            yield from _recorre(v, f"{ruta}.{k}" if ruta else str(k))
    elif isinstance(nodo, list):
        for i, v in enumerate(nodo):
            yield from _recorre(v, f"{ruta}[{i}]")
    else:
        yield ruta, nodo


def test_the_sweep_finds_the_files() -> None:
    """El candado del candado: si deja de ver los ficheros, deja de comprobar nada."""
    nombres = {f.name for f in FICHEROS}
    assert {"red_flags.yaml", "synonyms.yaml", "drugs.yaml", "taxonomia.yaml"} <= nombres
    assert len(FICHEROS) >= 8


@pytest.mark.parametrize("fichero", FICHEROS, ids=lambda f: f.name)
def test_no_key_is_silently_overwritten(fichero: pathlib.Path) -> None:
    """YAML se queda con la última clave repetida y no avisa. En un fichero de 1.600 líneas eso
    es una regla que desaparece sin dejar rastro."""
    _Duplicados.repetidas = []
    yaml.load(fichero.read_text(encoding="utf-8"), Loader=_Duplicados)
    assert not _Duplicados.repetidas, (
        f"{fichero.name}: claves repetidas (la primera se pierde en silencio): "
        + ", ".join(f"«{k}» línea {n}" for k, n in _Duplicados.repetidas)
    )


def _listas(nodo: object, ruta: str = ""):  # type: ignore[no-untyped-def]
    """Cada lista del fichero, con su ruta."""
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            yield from _listas(v, f"{ruta}.{k}" if ruta else str(k))
    elif isinstance(nodo, list):
        yield ruta, nodo
        for i, v in enumerate(nodo):
            yield from _listas(v, f"{ruta}[{i}]")


@pytest.mark.parametrize("fichero", FICHEROS, ids=lambda f: f.name)
def test_a_list_of_words_holds_no_bare_number(fichero: pathlib.Path) -> None:
    """Una lista MEZCLADA de texto y número es siempre un olvido de comillas.

    La primera versión de esta comprobación miraba el nombre del campo (`patterns`, `terms`…) y
    con eso NO habría cazado el fallo que la motivó: en `synonyms.yaml` el campo se llama como el
    disparador —`emergency: [urgencias, 112]`—, así que no había nombre que reconocer. La forma
    del dato sí se reconoce: donde hay palabras, un número suelto sobra.

    Las listas de puros números —concentraciones en mg/ml, horas entre dosis— no se tocan, que
    ahí el número es el dato.
    """
    datos = yaml.safe_load(fichero.read_text(encoding="utf-8"))
    malos = []
    for ruta, lista in _listas(datos):
        if len(lista) < 2:
            continue
        textos = [x for x in lista if isinstance(x, str)]
        numeros = [x for x in lista if isinstance(x, (int, float)) and not isinstance(x, bool)]
        if textos and numeros:
            malos.append((ruta, numeros))
    assert not malos, (
        f"{fichero.name}: listas con palabras Y números sueltos (faltan comillas): "
        + ", ".join(f"{r} → {v!r}" for r, v in malos)
    )


@pytest.mark.parametrize("fichero", FICHEROS, ids=lambda f: f.name)
def test_no_string_is_empty(fichero: pathlib.Path) -> None:
    datos = yaml.safe_load(fichero.read_text(encoding="utf-8"))
    vacias = [r for r, v in _recorre(datos) if isinstance(v, str) and not v.strip()]
    assert not vacias, f"{fichero.name}: cadenas vacías en {vacias}"


def test_every_pattern_compiles() -> None:
    """Una expresión que no compila revienta al cargar las reglas, o sea al arrancar el API."""
    reglas = yaml.safe_load((CONFIG / "red_flags.yaml").read_text(encoding="utf-8"))
    malas = []
    for regla in reglas["rules"]:
        for p in regla.get("patterns", []):
            try:
                re.compile(str(p))
            except re.error as e:
                malas.append((regla["id"], str(p)[:50], str(e)))
    for grupo in (reglas.get("context") or {}).values():
        for p in grupo:
            try:
                re.compile(str(p))
            except re.error as e:
                malas.append(("context", str(p)[:50], str(e)))
    assert not malas, "expresiones que no compilan: " + str(malas)


def test_no_control_character_slipped_in() -> None:
    r"""El retroceso (0x08) es el que se cuela: escribir `"\b"` en un script de Python sin `r`
    delante no produce una barra y una be, produce un carácter de control — y entonces el YAML no
    carga. Pasó tres veces en la sesión del 8-sep."""
    for f in FICHEROS:
        texto = f.read_text(encoding="utf-8")
        malos = {c for c in texto if ord(c) < 32 and c not in "\n\r\t"}
        assert not malos, f"{f.name}: caracteres de control {[hex(ord(c)) for c in malos]}"
