"""El memo no teclea cifras: las cuenta (19-sep-2026).

`/memo` es la página que se manda a quien está decidiendo si financia esto, así que es justo
donde una cifra vieja cuesta más cara. Cuando se escribió tenía tres mal a la vez: 5 reglas en
vez de 83 y 499 documentos en vez de 496, porque contaba del fichero parecido y no del bueno, y
«48 African countries» cuando ya eran 49, porque esa estaba escrita a mano. Se le escapó a la
lectura y la cazó el build.

De ahí las dos mitades de este fichero: que ninguna cifra contable esté escrita a mano en la
plantilla, y que la página construida diga exactamente lo que dicen los ficheros de origen.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[1]
MEMO = RAIZ / "web" / "site" / "src" / "pages" / "memo.astro"
CONSTRUIDO = RAIZ / "web" / "site" / "dist" / "memo" / "index.html"

#: Los mismos códigos que usa `scripts/check_metadao.py`, que es lo que se afirma fuera.
AFRICA = (
    "DZ AO BJ BW BF BI CV CM CF TD KM CD CG CI DJ EG GQ ER SZ ET GA GM GH GN GW KE LS LR LY "
    "MG MW ML MR MU MA MZ NA NE NG RW ST SN SC SL SO ZA SS SD TZ TG TN UG ZM ZW"
).split()


def _config(nombre: str) -> dict:
    return yaml.safe_load((RAIZ / "config" / nombre).read_text(encoding="utf-8"))


def cifras_de_los_ficheros() -> dict[str, int]:
    """Lo que dicen hoy los ficheros de los que vive el sitio."""
    emergencias = _config("emergency_numbers.yaml")
    vacunas = _config("vaccines.yaml")["countries"]
    return {
        "países con número de emergencia": len([k for k in emergencias if k != "default"]),
        "países sin servicio nacional": len(
            [
                k
                for k, v in emergencias.items()
                if k != "default" and isinstance(v, dict) and v.get("no_national")
            ]
        ),
        "países con calendario": len(vacunas),
        "países con curva": len(_config("growth_charts.yaml").get("countries", {})),
        "guías": len(list((RAIZ / "web" / "content").rglob("*.md"))),
        "reglas de alarma": len(_config("red_flags.yaml")["rules"]),
        "documentos del catálogo": len(
            json.loads((RAIZ / "dataset" / "sources.json").read_text(encoding="utf-8"))
        ),
        "países africanos con ambas cosas": len(
            [c for c in AFRICA if c in emergencias and c in vacunas]
        ),
    }


def cuerpo_de_la_plantilla() -> str:
    """El HTML del memo, sin el frontmatter, y sin lo que va entre llaves.

    Lo de entre llaves es precisamente lo que SÍ está contado; lo que queda después de quitarlo
    es prosa, y en la prosa no puede haber ninguna de estas cifras.
    """
    partes = MEMO.read_text(encoding="utf-8").split("---")
    plantilla = "---".join(partes[2:])
    return re.sub(r"\{[^{}]*\}", " ", plantilla)


def test_ninguna_cifra_contable_esta_escrita_a_mano() -> None:
    prosa = cuerpo_de_la_plantilla()
    a_mano = {
        nombre: valor
        for nombre, valor in cifras_de_los_ficheros().items()
        if re.search(rf"(?<![\d.,]){valor}(?![\d.,])", prosa)
    }
    assert not a_mano, (
        "escritas a mano en memo.astro, se quedarán viejas sin que nadie se entere: "
        + ", ".join(f"{n} ({v})" for n, v in sorted(a_mano.items()))
    )


def test_el_catalogo_se_cuenta_del_publicado_y_no_del_interno() -> None:
    """`src/data/sources.json` tiene tres documentos que no se pueden redistribuir.

    El catálogo público, que es el que se cita fuera, no los lleva. Contar del interno daba 499
    donde todos los demás textos dicen 496: tres de más que nadie podría ir a comprobar.
    """
    frontmatter = MEMO.read_text(encoding="utf-8").split("---")[1]
    assert "dataset/sources.json" in frontmatter
    assert "'../data/sources.json'" not in frontmatter


@pytest.mark.parametrize("nombre", sorted(cifras_de_los_ficheros()))
def test_la_pagina_construida_dice_lo_que_dicen_los_ficheros(nombre: str) -> None:
    if not CONSTRUIDO.exists():
        pytest.skip("el sitio no está construido; esto se comprueba tras `npm run build`")
    texto = re.sub(r"<[^>]*>", " ", CONSTRUIDO.read_text(encoding="utf-8"))
    valor = cifras_de_los_ficheros()[nombre]
    assert re.search(rf"(?<![\d.,]){valor}(?![\d.,])", texto), (
        f"«{nombre}» son {valor} y el memo construido no lo dice en ningún sitio"
    )
