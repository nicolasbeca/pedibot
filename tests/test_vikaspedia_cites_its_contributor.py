"""Vikaspedia entra citando a quien aporta cada página (1-oct-2026).

El permiso de Vikaspedia (C-DAC), por correo del 1-oct, tiene una condición que no es la de
siempre: «proper citation of the source of the content contributor and the Vikaspedia page
link». Cada página firma al pie quién aporta el contenido —«स्रोत: स्वास्थ्य विभाग, झारखण्ड
सरकार», el departamento de salud de Jharkhand— y ese nombre tiene que viajar con la cita. Va en el
título del documento, porque el título es lo que acompaña a la cita en todas partes: el chat, la
página de fuentes y el catálogo descargable. Las condiciones enteras: ops/PERMISOS.md.

Y la página no se puede leer como las demás: es una aplicación Next.js y el texto viene dentro de
un JSON, así que el HTML que se guarda es el contenido sacado de ahí, con su título.
"""

from __future__ import annotations

import importlib.util
import json

from pedibot.settings import ROOT

spec = importlib.util.spec_from_file_location(
    "fetch_web_sources", ROOT / "scripts" / "fetch_web_sources.py"
)
fws = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(fws)  # type: ignore[union-attr]


def _pagina(contenido: str, titulo: str = "बच्चों में दस्‍त से होने वाली मौतों से बचाव") -> str:
    datos = {
        "props": {
            "pageProps": {
                "ssrPageContent": {
                    "title": titulo,
                    "content": contenido,
                    "created_by_name": "Shruti Sahay",
                    "updated_at": "2023-02-02T06:44:49.000+00:00",
                }
            }
        }
    }
    return (
        "<html><head><title>x</title></head><body><div id='__next'></div>"
        f"<script id='__NEXT_DATA__' type='application/json'>{json.dumps(datos)}</script>"
        "</body></html>"
    )


DIARREA = _pagina(
    "<h3>दस्‍त रोग क्‍यों होता है?</h3><p>दस्‍त रोग नवजात एवं 5 वर्ष से कम आयु के "
    "बच्‍चों की मौत का एक प्रमुख कारण है।</p><p>स्त्रोत:</p>"
    "<p>स्वास्थ्य विभाग, झारखण्ड सरकार</p>"
)


def test_the_saved_page_has_the_text_and_the_title() -> None:
    limpio, titulo, _ = fws.vikaspedia_page(DIARREA)
    assert "<main>" in limpio and "</main>" in limpio
    assert "प्रमुख कारण" in limpio
    assert "<h1>" in limpio and titulo in limpio
    assert "‍" not in titulo, "el título se enseña y se busca: sin el ZWJ invisible"


def test_the_contributor_is_read_from_the_footer() -> None:
    _, _, autor = fws.vikaspedia_page(DIARREA)
    assert autor == "स्वास्थ्य विभाग, झारखण्ड सरकार"


def test_the_contributor_on_the_same_line() -> None:
    _, _, autor = fws.vikaspedia_page(_pagina("<p>texto</p><p>स्रोत: पत्र सूचना कार्यालय</p>"))
    assert autor == "पत्र सूचना कार्यालय"


def test_the_last_footer_wins_not_a_word_inside_the_text() -> None:
    """«जलस्रोत» (fuente de agua) dentro del texto no es la firma."""
    html = _pagina(
        "<p>स्रोत: वह नहीं</p><p>पानी के जलस्रोत साफ़ रखें।</p>"
        "<p>स्रोत: महिला एवं बाल विकास मंत्रालय, भारत सरकार</p>"
    )
    _, _, autor = fws.vikaspedia_page(html)
    assert autor == "महिला एवं बाल विकास मंत्रालय, भारत सरकार"


def test_a_signature_split_across_tags_is_read_whole() -> None:
    """«प्रतिरक्षण» firma con tres fuentes en tres trozos de HTML: se quedaba en la primera."""
    html = _pagina(
        "<p>texto</p><p>स्रोत: <a>डब्लू. एच. ओ.</a> , <span>नेशनल इम्यूनाइजेशन सिड्यूल</span>,"
        "इंडियन अकादमी ऑफ़ पीडियाट्रिक्स</p>"
    )
    _, _, autor = fws.vikaspedia_page(html)
    assert autor == (
        "डब्लू. एच. ओ., नेशनल इम्यूनाइजेशन सिड्यूल, इंडियन अकादमी ऑफ़ पीडियाट्रिक्स"
    ), autor


def test_the_year_is_the_page_update() -> None:
    limpio, _, _ = fws.vikaspedia_page(DIARREA)
    assert fws.saved_year(limpio) == 2023


def test_without_a_footer_the_contributor_is_vikaspedia() -> None:
    _, _, autor = fws.vikaspedia_page(_pagina("<p>texto sin firma</p>"))
    assert autor == "Vikaspedia"


def test_every_vikaspedia_entry_names_its_contributor_in_the_title() -> None:
    """Lo que entra al catálogo, no sólo la función: cada título dice «स्रोत: …»."""
    import yaml

    web = yaml.safe_load((ROOT / "config" / "fuentes_web.yaml").read_text(encoding="utf-8"))
    vk = [d for d in web["sources"] if d["org"] == "Vikaspedia"]
    assert len(vk) >= 15, len(vk)
    for d in vk:
        assert "स्रोत:" in d["title"], d["title"]
        assert d["url"].startswith("https://health.vikaspedia.in/"), d["url"]
        assert d["lang"] == "hi"
        assert d["year"], f"sin año: {d['title']}"
        assert "non-commercial" in d["notes"] and "PERMISOS" in d["notes"], d["notes"]


def test_doc_ids_are_readable() -> None:
    """La dirección de Vikaspedia está en devanagari: el doc_id sale de su número de página."""
    url = next(u for k, u, *_ in fws.WEB_SOURCES if k == "vikaspedia")
    did = fws.doc_id_for("vikaspedia", url, "hi")
    assert did.startswith("vikaspedia_hi_") and did[len("vikaspedia_hi_") :].isdigit(), did
