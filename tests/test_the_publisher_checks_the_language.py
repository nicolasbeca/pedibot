"""Una guía con el idioma mezclado no se publica (16-sep-2026).

El servidor publica guías solo, con su temporizador, y el 16-sep sacó una en portugués con un
encabezado medio en castellano:

    ## Quando acudir al médico ou a urgencias

Estuvo viva. El publicador SÍ comprobaba el idioma —`detect_lang` sobre el artículo entero— y
no la vio, porque el artículo era portugués: la fuga era una línea. El guardián que sí la vio,
`scripts/check_lang_leak.py`, corre sobre el sitio CONSTRUIDO, o sea después de publicar y de
desplegar; sirve para enterarse, no para impedirlo.

Así que la misma lista de marcadores se usa ahora en el publicador, sobre el título y los
encabezados, que es justo donde se cuelan. Un artículo que falla se reintenta una vez y, si
vuelve a fallar, no se escribe: mejor ninguna guía que una guía en dos idiomas.

Y la segunda prueba de aquí mira las guías YA publicadas, porque lo que se arregla a mano vuelve:
esa corrección se perdió sola en el despliegue siguiente (el despliegue se trae `web/content` del
servidor antes de subir), y el commit posterior la dio por buena.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from pedibot.lang_markers import MARKERS, foreign_markers
from pedibot.publish.articles import _problems

RAIZ = pathlib.Path(__file__).resolve().parents[1]
CONTENIDO = RAIZ / "web" / "content"

#: El artículo real que se publicó, recortado a lo que importa.
CUERPO_PT = """Os percentis comparam o tamanho do seu filho com o de outras crianças [1].

## O que é

Os percentis são as linhas das curvas de crescimento [1].

## O que você pode fazer em casa

- Leve o seu filho às consultas de rotina [1].

## {encabezado}

Procure seu médico ou o pronto-socorro se você notar sinais de alarme [1]:

- Perda de peso sem explicação [1].

## Perguntas frequentes

**O que é um percentil?** É uma linha da curva [1].
"""


def test_el_encabezado_en_castellano_de_una_guia_portuguesa_no_pasa() -> None:
    fuga = foreign_markers("Quando acudir al médico ou a urgencias", "pt")
    assert fuga and fuga[0][0] == "es", fuga


def test_y_el_encabezado_bueno_pasa() -> None:
    assert not foreign_markers("Quando procurar o médico ou o pronto-socorro", "pt")


def test_cada_lengua_puede_escribir_lo_suyo() -> None:
    """La mitad que hace segura a la otra: los marcadores de una lengua no se disparan en ella."""
    for lang, palabras in MARKERS.items():
        linea = " ".join(palabras)
        assert not foreign_markers(linea, lang), f"{lang} se acusa a sí misma"


def test_el_publicador_rechaza_el_borrador_con_la_fuga() -> None:
    malo = CUERPO_PT.format(encabezado="Quando acudir al médico ou a urgencias")
    problemas = _problems("O que são os percentis de crescimento", malo, [], "pt")
    assert any("language_leak" in p for p in problemas), problemas


def test_el_publicador_acepta_el_mismo_borrador_bien_escrito() -> None:
    bueno = CUERPO_PT.format(encabezado="Quando procurar o médico ou o pronto-socorro")
    problemas = _problems("O que são os percentis de crescimento", bueno, [], "pt")
    assert not any("language_leak" in p for p in problemas), problemas


def _titulo_y_encabezados(texto: str) -> list[str]:
    m = re.match(r"\A---\n(.*?)\n---\n", texto, re.S)
    front, cuerpo = (m.group(1), texto[m.end() :]) if m else ("", texto)
    titulo = re.search(r'^title:\s*"?(.*?)"?\s*$', front, re.M)
    return ([titulo.group(1)] if titulo else []) + re.findall(r"^#+ (.+)$", cuerpo, re.M)


@pytest.mark.skipif(not CONTENIDO.is_dir(), reason="sin guías publicadas")
def test_ninguna_guia_publicada_mezcla_idiomas() -> None:
    mal: dict[str, list[tuple[str, str]]] = {}
    for f in sorted(CONTENIDO.rglob("*.md")):
        for linea in _titulo_y_encabezados(f.read_text(encoding="utf-8")):
            fuga = foreign_markers(linea, f.parent.name)
            if fuga:
                mal.setdefault(f"{f.parent.name}/{f.stem}", []).extend(fuga)
    assert not mal, f"guías con el idioma mezclado en un titular: {list(mal.items())[:5]}"
