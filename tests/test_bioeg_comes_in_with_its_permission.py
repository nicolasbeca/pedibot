"""kindergesundheit-info.de entra en el índice (20-oct-2026).

El BIÖG lo autorizó el 19-oct (Claudia Thienel, hilo «Freigabe Nutzung der Texte mit
Quellenangabe»): «Sie können die Inhalte ab jetzt gerne so nutzen», con el aviso de que de lo
que publicamos respondemos nosotros. El 8-oct prometimos además pasar la lista de «wann ein
Arztbesuch dringend ist» entera, con el punto de no conseguir que el niño beba. Condiciones al
pie de la letra en ops/PERMISOS.md.

Lo que se cierra aquí: que sus páginas para padres estén, con su permiso escrito en la ficha y
su nombre en la cita; que no se cuele lo que es para profesionales ni su lista de bibliografía;
y que la página del vómito llegue al índice con la lista de alarma completa.
"""

from __future__ import annotations

import pathlib

import yaml

from pedibot.ingest.extract_html import extract_html

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = "https://www.kindergesundheit-info.de/themen/"


def _bioeg() -> list[dict]:
    data = yaml.safe_load((ROOT / "config" / "fuentes_web.yaml").read_text(encoding="utf-8"))
    return [s for s in data["sources"] if s.get("org") == "BIÖG"]


def test_its_parent_pages_are_in_the_catalog() -> None:
    docs = _bioeg()
    assert len(docs) >= 100, len(docs)
    for d in docs:
        assert d["url"].startswith(SITE), d["url"]
        assert d["lang"] == "de"
        assert d["usage"] == "publico"
        assert "2026-10-19" in d["notes"], "el permiso escrito tiene que ir en la ficha"


def test_nothing_for_professionals_or_lists_of_links() -> None:
    for d in _bioeg():
        url = d["url"]
        assert "/fachkraefte/" not in url
        for ruido in ("downloads", "linktipps", "contentbox", "/default-", "/faq"):
            assert ruido not in url, url


def test_the_vomiting_page_keeps_the_whole_warning_list() -> None:
    (d,) = [x for x in _bioeg() if "erbrechen-von-babys-und-kleinkindern" in x["url"]]
    texto = "\n".join(
        l.text for l in extract_html(ROOT / "FUENTES" / d["file"]).pages[0].lines
    )
    assert "Wann bei Erbrechen ein Arztbesuch dringend ist" in texto
    assert "Kind zum Trinken zu bewegen" in texto  # el punto que Claudia pidió no perder
    assert "morgens nüchtern erbricht" in texto  # el último de la lista
    # su bibliografía no es información para un padre, y sería citable si se queda dentro
    assert "Zugriffsdatum" not in texto


def test_the_sources_page_links_their_site() -> None:
    fuente = (ROOT / "web" / "site" / "src" / "components" / "SourcesTable.astro").read_text(
        encoding="utf-8"
    )
    assert "https://www.kindergesundheit-info.de/" in fuente


def test_the_front_page_band_can_name_them() -> None:
    fuente = (ROOT / "web" / "site" / "src" / "components" / "Sections.astro").read_text(
        encoding="utf-8"
    )
    assert "'BIÖG':" in fuente


def test_each_page_carries_its_own_date() -> None:
    # junto al título, en `ce__meta`: «0-6 Jahre · 11.02.2026». Es lo que /sources enseña como año.
    docs = _bioeg()
    (d,) = [x for x in docs if "erbrechen-von-babys-und-kleinkindern" in x["url"]]
    assert d["year"] == 2026
    assert sum(1 for x in docs if x["year"]) >= 0.9 * len(docs)
