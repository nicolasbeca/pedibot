"""Cada guía tiene que citar algo que su lector pueda abrir (18-sep-2026).

L167 se escribió el 16-sep por una guía: «una guía escrita para un lector que no puede abrir sus
fuentes». Se arregló aquella y no se midieron las demás. Esto mide las 502.

La regla: una guía tiene que citar al menos una fuente en el idioma del lector, en inglés —que
este proyecto trata como puente para todos, y lo tiene escrito en FUENTES/INDIA.md— o en la lengua
puente que el buscador ya reconoce (`READABLE_FALLBACK`, que añade el castellano para el lector
portugués). Es lo mismo que hace el recuperador al subir una fuente legible entre las tres
primeras, un escalón más abajo: que la guía **publicada** no se quede sin ninguna.

Medido al escribirla: **6 de 502**, y las seis son el mismo tema —los espasmos del sollozo— en
árabe, alemán, inglés, francés, hindi y ruso. Su única fuente en todo el corpus es la hoja de la
SEUP, en castellano, y se buscó la que falta sin encontrarla: el NHS retiró su página (devuelve
200 diciendo «This page has been removed», que es L151 en vivo) y la de MedlinePlus está en
`/ency/`, que es contenido con licencia y una línea que este proyecto no cruza. El rastreo está
en `FUENTES/CANDIDATAS.md`.

Por eso las seis están en la lista de excepciones **con su motivo**, y no se silencia la prueba:
una guía nueva que nazca así sigue fallando aquí.
"""

from __future__ import annotations

import pathlib
import re

import pytest
import yaml

from pedibot.index.store import READABLE_FALLBACK

RAIZ = pathlib.Path(__file__).resolve().parents[1]
CONTENIDO = RAIZ / "web" / "content"

#: El tema que hoy no tiene fuente abierta fuera del castellano, y por qué (ver CANDIDATAS.md).
SIN_FUENTE_ABIERTA = {"espasmos_sollozo"}

#: doc_id → idioma, del catálogo.
def _idiomas_de_las_fuentes() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in ("config/fuentes.yaml", "config/fuentes_web.yaml"):
        for s in yaml.safe_load((RAIZ / f).read_text(encoding="utf-8"))["sources"]:
            out[s["doc_id"]] = s.get("lang", "es")
    return out


IDIOMAS = _idiomas_de_las_fuentes()
#: Los organismos, para reconocer una cita que no lleva el doc_id escrito.
POR_NOMBRE = (
    ("nhs", "en"), ("cdc", "en"), ("medlineplus", "en"), ("who", "en"),
    ("seup", "es"), ("aepap", "es"), ("aeped", "es"), ("rki", "de"),
)


def _idioma(cita: str) -> str | None:
    low = cita.lower()
    for doc_id, lang in IDIOMAS.items():
        if doc_id in low:
            return lang
    for nombre, lang in POR_NOMBRE:
        if nombre in low:
            return lang
    return None


def _guias() -> list[tuple[str, pathlib.Path]]:
    if not CONTENIDO.exists():
        return []
    return [
        (d.name, f)
        for d in sorted(CONTENIDO.iterdir())
        if d.is_dir()
        for f in sorted(d.glob("*.md"))
    ]


GUIAS = _guias()


def test_there_are_guides_to_look_at() -> None:
    assert len(GUIAS) > 100, f"sólo {len(GUIAS)} guías: no se están leyendo"


@pytest.mark.parametrize("lang,fichero", GUIAS, ids=lambda x: str(x)[-44:])
def test_the_guide_cites_at_least_one_readable_source(lang: str, fichero: pathlib.Path) -> None:
    texto = fichero.read_text(encoding="utf-8")
    bloque = re.search(r"\nsources:\n((?:\s*-\s.*\n)+)", texto)
    if not bloque:
        return  # sin bloque de fuentes lo mira otra prueba
    tema = re.search(r"^topic:\s*(\S+)", texto, re.M)
    idiomas = {x for x in (_idioma(c) for c in re.findall(r"-\s*(.+)", bloque.group(1))) if x}
    if not idiomas:
        return  # ninguna reconocible: no se acusa sin saber
    # Qué cuenta como legible, y por qué estas tres cosas y no otras:
    #
    # · el idioma de la guía, obviamente;
    # · **el inglés, para todos**. No es una suposición: es la posición escrita del proyecto en
    #   FUENTES/INDIA.md —«el motor responde en hindi citando fichas del NHS, la OMS y el CDC,
    #   que un padre indio puede abrir (el inglés es lengua oficial allí)»— y es la misma razón
    #   por la que el suajili entró con la explicación en inglés (L183);
    # · y la lengua puente que el buscador ya reconoce, que añade el castellano para el lector
    #   portugués.
    #
    # La primera versión de esta prueba usó sólo el idioma y su puente, y señaló 74 guías
    # portuguesas que citan al NHS. Eso no era un hallazgo: era convertir una preferencia de
    # ORDEN —cuál se sube al tercer puesto— en una regla dura sobre lo que un padre puede leer.
    legibles = {lang, "en", READABLE_FALLBACK.get(lang, "")}
    if idiomas & legibles:
        return
    if tema and tema.group(1) in SIN_FUENTE_ABIERTA:
        pytest.skip(f"{tema.group(1)}: no hay fuente abierta fuera del castellano, ver CANDIDATAS")
    raise AssertionError(
        f"[{lang}] {fichero.name}: sus fuentes están sólo en {sorted(idiomas)} y este lector "
        f"lee {sorted(x for x in legibles if x)}. Una guía cuyas fuentes no se pueden abrir le "
        "pide al padre que confíe sin comprobar, y comprobar es lo único que este producto "
        "ofrece por encima de un buscador (L167)."
    )
