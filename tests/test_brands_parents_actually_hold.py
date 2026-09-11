"""La marca que el padre tiene en la mano (11-sep-2026).

El sitio publica una página de dosis por marca —`/dose/panadol`, `/dose/nurofen`— y el
asistente **no reconocía ninguna de las dos** si el padre escribía sólo la marca. En el
catálogo están como «Panadol Children» y «Nurofen for Children», y el emparejador trata un
nombre con espacios como una frase: tenía que aparecer entera. Nadie escribe «Panadol Children
120 mg/5 ml»; se escribe «panadol».

Importa más de lo que parece por dónde duele. **Panadol es el antitérmico infantil dominante en
todo el Golfo** y Nurofen lo es en media Europa, así que el agujero estaba justo en el mercado
que el proyecto ha decidido atacar. Medido: de diez marcas árabes de uso corriente, el buscador
reconocía **una** — y era la escrita en árabe.

Dos reglas, las dos de fondo:

1. **Si el sitio publica una página de una marca, el asistente tiene que conocer esa marca**, y
   por el nombre a secas. Publicar `/dose/panadol` y contestar «no tengo información fiable
   sobre esto» a quien escribe «panadol» es peor que no tener la página.
2. **El catálogo tiene dos moléculas y nada más.** Una marca que NO sea una de las dos —Meftal-P
   es ácido mefenámico, Combiflam es una combinación— no puede recibir una dosis por parecido.
"""

from __future__ import annotations

import pytest
import yaml

from pedibot.bot.retrieval import Synonyms
from pedibot.settings import ROOT

DIST = ROOT / "web" / "site" / "dist"


@pytest.fixture(scope="module")
def sinonimos() -> Synonyms:
    return Synonyms(ROOT / "config" / "synonyms.yaml", ROOT / "config" / "drugs.yaml")


def _marcas() -> list[tuple[str, str]]:
    """(marca tal cual está en el catálogo, molécula)."""
    drugs = yaml.safe_load((ROOT / "config" / "drugs.yaml").read_text(encoding="utf-8"))["drugs"]
    return [(b["name"], k) for k, v in drugs.items() for b in (v.get("brands") or [])]


def _slug(nombre: str) -> str:
    """El mismo corte que hace `export_catalog.py` para la URL de la marca."""
    return nombre.lower().split(" ")[0].split("/")[0]


@pytest.mark.parametrize("marca", sorted({_slug(n) for n, _ in _marcas()}))
def test_la_marca_a_secas_se_reconoce(sinonimos: Synonyms, marca: str):
    """Tal y como la escribe un padre: una palabra, la del bote."""
    assert sinonimos.expand(f"{marca} 12 kg", "en"), (
        f"«{marca}» no se reconoce escrito a secas, y el sitio publica /dose/{marca}"
    )


def test_toda_pagina_de_marca_publicada_tiene_quien_la_entienda(sinonimos: Synonyms):
    if not (DIST / "dose").exists():
        pytest.skip("el sitio no está construido en esta copia")
    sordas = [
        d.name
        for d in sorted((DIST / "dose").iterdir())
        if d.is_dir() and not sinonimos.expand(f"{d.name} 12 kg", "en")
    ]
    assert not sordas, f"páginas de marca que el asistente no reconoce: {sordas}"


#: Lo que un padre indio tiene de verdad en el armario y NO son nuestras dos moléculas.
#: Meftal-P es ácido mefenámico; Combiflam, ibuprofeno + paracetamol en un solo comprimido.
FUERA_DEL_CATALOGO = ["meftal", "combiflam", "sumo", "nimesulide"]


@pytest.mark.parametrize("nombre", FUERA_DEL_CATALOGO)
def test_lo_que_no_esta_en_el_catalogo_no_recibe_dosis_por_parecido(
    sinonimos: Synonyms, nombre: str
):
    extra = sinonimos.expand(f"{nombre} 12 kg", "en")
    assert not any(
        t in ("paracetamol", "ibuprofen", "ibuprofeno", "acetaminophen") for t in extra
    ), f"«{nombre}» no es ninguna de las dos moléculas del catálogo y expande a {extra}"
