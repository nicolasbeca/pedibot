"""Cada detector que lee lo que escribe un padre, en las escrituras que lee (7-sep-2026).

La regla de la L54: *cada vez que algo se escribe con una expresión regular, preguntar en qué
alfabetos está escrita esa expresión*. El proyecto habla ocho idiomas en tres escrituras, y todo
lo que se había escrito a mano se había escrito en la latina. En un día salieron de ahí seis
averías: el enrutador de vacunas, el de dosis, tres reglas de alarma —una de emergencia—, el
guardia contra dosis inventadas y el tokenizador del buscador.

**La unidad de comprobación es el detector con nombre, no la expresión suelta.** Esa distinción no
es un detalle: los patrones de edad en devanagari son entradas *aparte* dentro de `_AGE_PATTERNS`
—con su motivo escrito, porque terminan en `NOT_AFTER` en vez de `\\b`—, así que mirarlos uno a uno
daría por incompleto un diseño que está bien. Una primera versión de este fichero hizo exactamente
eso y señaló seis falsos positivos.

Lo que no se puede automatizar se declara: un detector que deba ser latino, o que cubra las
escrituras por otra vía (`\\w`, un rango `\\uXXXX`), va en `DECLARADOS` con su motivo. Declararlo
cuesta una frase; olvidarlo cuesta una prueba en rojo.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]

#: Los ficheros cuyos detectores leen lo que un padre escribe. Fuera quedan la ingesta (lee PDF en
#: español e inglés), las operaciones (registros, rutas, agentes de usuario) y la publicación.
LEEN_AL_PADRE = [
    "src/pedibot/bot/triage.py",
    "src/pedibot/bot/vaccines.py",
    "src/pedibot/index/store.py",
]

#: Detectores que no llevan caracteres de las tres escrituras, y por qué está bien.
DECLARADOS = {
    "_TOKEN": "cubre las tres por otra vía: `\\w` casa cirílico y árabe, y el rango "
    "\\u0900-\\u097f añade el devanagari con sus matras, que `\\w` no reconoce",
    "_GUIONES": "son los guiones Unicode, que no son letras de ningún alfabeto",
    "_LATINA": "es latino A PROPÓSITO: marca dónde se quita la tilde, y el árabe y el "
    "devanagari no llevan tildes sino letras — quitarles la marca combinante rompe la "
    "palabra (las matras de «बुखार»). El cirílico se trata aparte, fundiendo sólo la ё",
    "_MENOS_DE": "el cualificador que va DELANTE de la edad («menos de 3 meses»). El "
    "hindi lo pone detrás («3 महीने से कम») y por eso vive en `_MENOS_DE_DETRAS`: las dos "
    "mitades juntas cubren las cuatro escrituras, y separarlas es lo que hace que cada "
    "una funcione",
    "_MENOS_DE_DETRAS": "la otra mitad: el cualificador POSPUESTO, que es como lo dice el "
    "hindi. Las lenguas que lo anteponen están en `_MENOS_DE`",
    "_LATINA_BASE": "es latino a propósito, igual que `_LATINA` en el índice: marca dónde "
    "una marca combinante es una TILDE y se puede quitar. Sobre árabe o devanagari esa "
    "misma marca es la palabra —los harakat, las matras— y quitarla la rompe. El árabe y "
    "el devanagari los trata `aplana` con sus propias tablas (17-sep-2026)",
    "_RU_COMPUESTO": "el gemelo ruso de `_DE_COMPUESTO`: «двухмесячный», «годовалый». Es una "
    "gramática que solo existe en ruso —el número y la unidad fundidos en una palabra— y el "
    "ruso solo se escribe en cirílico. Las demás lenguas separan número y unidad, y de eso se "
    "ocupa `_AGE_PATTERNS`, que sí cubre las tres escrituras (17-sep-2026)",
    "_DE_COMPUESTO": "es la forma adjetiva alemana de decir la edad —«zweimonatiges», "
    "«dreijährige»— y el alemán se escribe en alfabeto latino y solo en él. Las otras siete "
    "lenguas dicen la edad separando el número de la unidad y las lee `_AGE_PATTERNS`, "
    "que sí cubre las tres escrituras: este detector no es una traducción a medias sino "
    "una gramática que solo existe en una lengua",
}

BLOQUES = {"cirílico": ("Ѐ", "ӿ"), "árabe": ("؀", "ۿ"), "devanagari": ("ऀ", "ॿ")}


def _detectores(fichero: pathlib.Path) -> dict[str, str]:
    """nombre del detector → todo el texto de sus patrones, concatenado.

    Un detector puede ser una `re.compile` suelta o una lista de tuplas con varias, como
    `_AGE_PATTERNS`: lo que cuenta es la unión de lo que ese nombre sabe reconocer.
    """
    arbol = ast.parse(fichero.read_text(encoding="utf-8"))
    fuera: dict[str, str] = {}
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Assign) or not nodo.targets:
            continue
        nombre = getattr(nodo.targets[0], "id", None)
        if not nombre:
            continue
        # solo lo que de verdad es un detector: la asignación tiene que contener un
        # `re.compile`. Una primera versión cogía cualquier cadena larga y señalaba consultas
        # SQL y nombres de columna — el tercer detector mío que da falsos positivos hoy.
        compila = any(
            isinstance(a, ast.Call)
            and isinstance(a.func, ast.Attribute)
            and a.func.attr == "compile"
            and getattr(a.func.value, "id", "") == "re"
            for a in ast.walk(nodo.value)
        )
        if not compila:
            continue
        trozos = [
            a.value
            for a in ast.walk(nodo.value)
            if isinstance(a, ast.Constant) and isinstance(a.value, str)
        ]
        texto = "".join(trozos)
        if sum(c.isalpha() for c in texto) >= 4:
            fuera[nombre] = texto
    return fuera


def test_the_sweep_finds_the_detectors() -> None:
    """El candado del candado: si deja de encontrarlos, deja de comprobar nada."""
    encontrados = {n for f in LEEN_AL_PADRE for n in _detectores(RAIZ / f)}
    assert {"_AGE_PATTERNS", "_VACC", "_TOKEN"} <= encontrados, f"solo se ven {sorted(encontrados)}"


@pytest.mark.parametrize("fichero", LEEN_AL_PADRE)
def test_every_detector_covers_every_script(fichero: str) -> None:
    huecos = []
    for nombre, texto in sorted(_detectores(RAIZ / fichero).items()):
        if nombre in DECLARADOS:
            continue
        faltan = [n for n, (lo, hi) in BLOQUES.items() if not any(lo <= c <= hi for c in texto)]
        if faltan:
            huecos.append(f"{fichero} :: {nombre} sin {faltan}")
    assert not huecos, (
        "detectores que leen al padre y no cubren todas las escrituras:\n  "
        + "\n  ".join(huecos)
        + "\n(si uno lo hace por otra vía o a propósito, decláralo en DECLARADOS con el motivo)"
    )


def test_the_declarations_still_point_at_something() -> None:
    """Una declaración que ya no corresponde a ningún detector es una excusa caducada, y esconde
    al siguiente que se llame igual."""
    todos = {n for f in LEEN_AL_PADRE for n in _detectores(RAIZ / f)}
    sobran = sorted(set(DECLARADOS) - todos)
    assert not sobran, f"declaraciones que ya no apuntan a ningún detector: {sobran}"


def test_the_tokeniser_keeps_a_hindi_word_whole() -> None:
    """La prueba de comportamiento que acompaña a la declaración de `_TOKEN`.

    Una exención sin comprobación es un agujero con permiso: `_TOKEN` está declarado porque cubre
    las escrituras por otra vía, y eso hay que verlo, no creerlo. Antes del 7-sep-2026:

        «मेरे बच्चे को बुखार है» → ['म','र','बच','च','क','ब','ख','र','ह']

    nueve trozos, ninguno una palabra — «बुखार» (fiebre) salía como «ब»+«ख»+«र». Y como después
    hay un filtro de tres caracteres, **una consulta en hindi producía CERO términos de búsqueda**.
    Encontraba igual gracias a las tablas cruzadas de sinónimos, pero eso dejaba toda la búsqueda
    en hindi colgando de 176 entradas escritas a mano.
    """
    from pedibot.index.store import _TOKEN, query_terms

    tokens = _TOKEN.findall("मेरे बच्चे को बुखार है")
    assert "बुखार" in tokens, f"la palabra «fiebre» sale partida: {tokens}"
    assert query_terms("मेरे बच्चे को बुखार है"), "una consulta en hindi no produce ningún término"
    # y las otras dos escrituras, que ya iban bien y tienen que seguir yendo
    assert "температура" in _TOKEN.findall("у ребёнка температура")
    assert "حمى" in _TOKEN.findall("ابني عنده حمى")
