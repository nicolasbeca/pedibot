"""Las páginas de medicamento dicen su concentración como la lee el padre (30-sep-2026).

Search Console traía «dosis dalsy 40 calculadora» y «calculadora apiretal» con las páginas en la
posición 81 (página 9 de Google). Dos causas que estaban en nuestra mano: la concentración
escrita como nadie la busca («suspensión 4 % (200 mg/5 ml)») y unas páginas de marca casi
idénticas entre sí, que casi ninguna página propia enlazaba. Ahora cada medicamento con más de
una concentración —o una marca que se vende junto a otra de distinta— tiene su sección «X 20
mg/ml o X 40 mg/ml: no son lo mismo», y las guías de fiebre, dolor, oído y dientes enlazan las
calculadoras de las marcas de su lengua.
"""

from __future__ import annotations

import pathlib
import re

import pytest

DIST = pathlib.Path(__file__).resolve().parents[1] / "web" / "site" / "dist"


def _html(ruta: str) -> str:
    f = DIST / ruta / "index.html"
    if not f.exists():
        pytest.skip("el sitio no está construido en esta copia")
    return f.read_text(encoding="utf-8")


def _texto(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_dalsy_dice_20_y_40_mg_ml_con_sus_mililitros() -> None:
    t = _texto(_html("es/dose/dalsy"))
    assert "Dalsy 20 mg/ml o Dalsy 40 mg/ml" in t
    # 10 kg de ibuprofeno = 100 mg: 5 ml del de 20 mg/ml y 2,5 del de 40, como dice la tabla
    assert re.search(r"Dalsy 20 mg/ml .{0,60}?5 ml", t) and re.search(r"Dalsy 40 mg/ml .{0,60}?2.5 ml", t)


def test_apiretal_se_compara_con_el_jarabe_que_se_vende_al_lado() -> None:
    t = _texto(_html("es/dose/apiretal"))
    assert "Apiretal 100 mg/ml" in t and "24 mg/ml" in t
    assert "uno da 4,2 veces la dosis del otro" in t


@pytest.mark.parametrize("ruta", ["dose/calpol", "fr/dose/doliprane", "ar/dose/dalsy", "es/dose/ibuprofeno"])
def test_la_seccion_sale_en_otras_lenguas_y_medicamentos(ruta: str) -> None:
    assert 'class="str card"' in _html(ruta), ruta


def test_la_guia_de_fiebre_enlaza_las_calculadoras_de_su_lengua() -> None:
    html = _html("es/guides/a_partir_de_que_temperatura_se_considera_fiebre_en_ninos")
    i = html.index('class="dbridge')
    bloque = html[i : html.index("</nav>", i)]
    for ruta in ("/es/dose/paracetamol", "/es/dose/dalsy", "/es/dose/apiretal"):
        assert f'href="{ruta}"' in bloque, ruta


def test_una_guia_que_no_es_de_fiebre_no_lleva_el_bloque() -> None:
    # las de vacunas tienen su propio puente, a los calendarios
    for p in (DIST / "es" / "guides").glob("*vacun*/index.html"):
        assert 'class="dbridge' not in p.read_text(encoding="utf-8"), p.parent.name
