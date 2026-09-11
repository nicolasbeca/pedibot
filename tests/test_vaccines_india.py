"""El calendario de India, transcrito del PDF oficial de la NHM (11-sep-2026).

Encargo del operador: potenciar los idiomas de los países con menos recursos, e India la primera.
Hasta hoy el hindi tenía **cero documentos** en el índice y ningún calendario propio: un padre en
Delhi veía los de España, Reino Unido, EE. UU., Francia, Alemania, Brasil y Portugal, traducidos
a su idioma y sin servirle para nada.

La licencia se leyó antes de tocar el dato, en la página de la propia National Health Mission:
«The contents on this website may not be reproduced partially or fully, **without duly &
prominently acknowledging the source**» — reproducible citando, excluido lo de terceros. Es la
misma clase que Canada.ca, ya aceptada en septiembre.

**Lo que se fija aquí son las diferencias que un europeo corregiría por instinto y estropearía:**

- **MR, no MMR.** India vacuna de sarampión y rubéola; **no** hay paperas en el calendario.
- **Pentavalente**, no hexavalente: la polio va aparte (OPV oral + fIPV inyectada).
- **fIPV**: dosis *fraccionada* de polio inactivada, que no existe en ningún otro calendario del
  sitio.
- **OPV oral con dosis 0 al nacer**, retirada hace décadas en Europa y aquí es la columna
  vertebral del programa.
- **PCV y JE no son nacionales**: la neumocócica sólo en algunos estados y la encefalitis
  japonesa sólo en distritos endémicos. Decirle a un padre que le tocan sin ese matiz es
  mandarle a un centro a por algo que allí no hay.
- **Td a los 10 y a los 16 años**, dos citas de adolescencia que los calendarios europeos no
  tienen así.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

RAIZ = pathlib.Path(__file__).resolve().parents[1]
PAISES = yaml.safe_load((RAIZ / "config" / "vaccines.yaml").read_text(encoding="utf-8"))["countries"]
LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")


@pytest.fixture
def india() -> dict:
    assert "IN" in PAISES, "India no está en config/vaccines.yaml"
    return PAISES["IN"]


def _citas(india: dict) -> dict[float, str]:
    """Normaliza quitando espacios y paréntesis: el documento oficial escribe «(RVV)-1» y
    «(fIPV)-1», y lo que se vigila es qué vacuna y qué dosis, no el estilo de los paréntesis."""
    fuera = str.maketrans("", "", " ()")
    return {
        float(s["age"]): " ".join(s["vaccines"]).lower().translate(fuera)
        for s in india["schedule"]
    }


def test_la_fuente_es_la_nhm_y_se_nombra(india: dict):
    assert "nhm.gov.in" in india["source_url"], india["source_url"]
    assert "immunization" in india["source_url"].lower()
    # la licencia obliga a nombrar la fuente de forma prominente: el campo `source` es ese sitio
    assert "National Health Mission" in india["source"] or "NHM" in india["source"]


def test_al_nacer_van_bcg_opv_cero_y_hepatitis_b(india: dict):
    v = _citas(india)[0.0]
    assert "bcg" in v
    assert "opv" in v
    assert "hepatitisb" in v


@pytest.mark.parametrize(
    ("semanas", "edad", "esperadas"),
    [
        (6, 1.5, ("opv-1", "pentavalent-1", "rvv-1", "fipv-1", "pcv-1")),
        (10, 2.5, ("opv-2", "pentavalent-2", "rvv-2")),
        (14, 3.5, ("opv-3", "pentavalent-3", "fipv-2", "rvv-3", "pcv-2")),
    ],
)
def test_las_tres_citas_de_semanas(india: dict, semanas: int, edad: float, esperadas: tuple):
    """6, 10 y 14 semanas: el corazón del programa indio, y no cae en ningún mes redondo."""
    citas = _citas(india)
    assert edad in citas, f"falta la cita de las {semanas} semanas (edad {edad})"
    for v in esperadas:
        assert v in citas[edad], f"{v} no está en las {semanas} semanas"


def test_es_sarampion_y_rubeola_nunca_paperas(india: dict):
    """India pone MR, no MMR. Escribir MMR sería inventarse una vacuna que allí no se pone."""
    todo = " ".join(" ".join(s["vaccines"]) for s in india["schedule"]).lower()
    assert "measles" in todo and "rubella" in todo
    assert "mumps" not in todo, "el calendario indio no lleva paperas"
    assert "mmr" not in todo.replace("-", "")


def test_la_polio_es_oral_y_fraccionada(india: dict):
    todo = " ".join(" ".join(s["vaccines"]) for s in india["schedule"]).lower()
    assert "opv" in todo, "la polio oral es la columna del programa indio"
    assert "fipv" in todo.replace(" ", ""), "la fIPV es dosis fraccionada y no existe en otro país"
    assert "hexavalent" not in todo, "India usa pentavalente; la polio va aparte"


def test_pcv_y_je_se_dicen_como_lo_que_son_no_como_nacionales(india: dict):
    """La neumocócica es de algunos estados y la encefalitis japonesa de distritos endémicos."""
    nota = " ".join(india["note"].values()).lower()
    assert "state" in nota or "estado" in nota, "hay que decir que la PCV no es de todo el país"
    assert "endemic" in nota or "endémic" in nota, "hay que decir que la JE es de zonas endémicas"


def test_las_dos_citas_de_adolescencia(india: dict):
    citas = _citas(india)
    assert 120.0 in citas and "td" in citas[120.0], "Td a los 10 años"
    assert 192.0 in citas and "td" in citas[192.0], "Td a los 16 años"


@pytest.mark.parametrize("lang", LANGS)
def test_el_nombre_y_la_nota_estan_en_los_ocho_idiomas(india: dict, lang: str):
    assert india["name"].get(lang), f"sin nombre en {lang}"
    assert india["note"].get(lang), f"sin nota en {lang}"


def test_el_hindi_no_es_el_ingles_copiado(india: dict):
    """La trampa de siempre: rellenar los ocho idiomas pegando el inglés."""
    assert india["name"]["hi"] != india["name"]["en"]
    assert india["note"]["hi"] != india["note"]["en"]
