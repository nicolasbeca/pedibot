"""Una guía de vacunas tiene que decir de qué país habla (7-sep-2026).

El consejo sobre la fiebre vale igual en Hamburgo que en Sevilla. **El calendario de vacunas no**:
las vacunas que le tocan a un niño dependen de dónde vive, y las diferencias son reales — el
MenACWY va a los 12 meses en Portugal y a los 12-14 AÑOS en Alemania, y el MenC de los 12 meses
existe en España y no en Alemania.

El corpus es asimétrico (L20): las mejores hojas para padres están en español, así que varias
guías de vacunas se escriben desde el calendario español aunque estén en otro idioma. Eso es
legítimo mientras la guía **diga que es el español**. Si no lo dice, un padre alemán se lleva a
casa el calendario de otro país creyendo que es el suyo, y encima contradice el calendario alemán
que la propia web publica en `/de/vaccines/de`.

Las tablas de autoridades y gentilicios se mudaron a `pedibot.publish.paises` el 23-sep-2026,
cuando la novena guía se olvidó y esta prueba la vio catorce horas tarde: ahora el publicador usa
las mismas listas y puede negarse a escribirla. Esto sigue mirando lo que ya está publicado.

Este candado existe para que la décima no se olvide — es el error
que no avisa: el texto sería verdadero, estaría bien citado, y aun así estaría mal.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from pedibot.publish.paises import AUTORIDAD, NOMBRES

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def _guias_de_vacunas() -> list[pathlib.Path]:
    fuera = []
    for f in sorted((RAIZ / "web" / "content").rglob("*.md")):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"^topic:\s*(\S+)", t, re.M)
        if m and ("vacun" in m.group(1) or "vaccin" in m.group(1)):
            fuera.append(f)
    return fuera


def _pais_dominante(cabecera: str) -> str | None:
    """El país cuya autoridad firma la mayoría de las citas, si hay una clara."""
    paises = [p for clave, p in AUTORIDAD.items() if clave in cabecera]
    if not paises:
        return None
    top = max(set(paises), key=paises.count)
    return top if paises.count(top) / len(paises) >= 0.8 else None


def test_there_are_vaccine_guides_to_check() -> None:
    """El candado del candado."""
    assert len(_guias_de_vacunas()) >= 5


@pytest.mark.parametrize("f", _guias_de_vacunas(), ids=lambda f: f"{f.parent.name}/{f.stem[:28]}")
def test_a_vaccine_guide_names_the_country_it_describes(f: pathlib.Path) -> None:
    texto = f.read_text(encoding="utf-8")
    partes = texto.split("---")
    cabecera, cuerpo = partes[1], "---".join(partes[2:])
    pais = _pais_dominante(cabecera)
    if pais is None:
        return  # ninguna autoridad nacional manda: no describe el calendario de un país
    lang = f.parent.name
    formas = NOMBRES.get(pais, {}).get(lang)
    assert formas, f"falta cómo se dice «{pais}» en [{lang}] — añádelo, no borres la comprobación"
    assert any(n.lower() in cuerpo.lower() for n in formas), (
        f"{f.parent.name}/{f.name}: describe el calendario de {pais} y no lo dice. "
        "Un calendario de vacunas es de un país; el lector lo va a tomar por el suyo."
    )
