"""HTML page → Extracted (same shape as the PDF extractor) for curated web sources.

Main-content heuristics per site: <main>/<article>, minus nav/header/footer/aside/script/forms.
Headings become "bigger" lines so the section splitter treats them as titles."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup, Tag

from pedibot.ingest.extract import Extracted, Line, PageText, file_sha256

_DROP = (
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "noscript",
    "svg",
    "button",
    "iframe",
)
_DROP_CLASS_HINTS = (
    "cookie",
    "breadcrumb",
    "share",
    "feedback",
    "related",
    "sidebar",
    "nhsuk-back-link",
    "site-footer",
    "print-only",
    "mlp-related",
    "usa-banner",
    "social",
    "subscribe",
    "survey",
    "menu",
    "skip",
)
_SKIP_TEXT = (
    "Page last reviewed",
    "Next review due",
    "Última revisión",
    "Last updated",
    "Skip to main content",
    "Cookies",
    "Video:",
    "Watch this video",
    "Media last reviewed",
    # 23-sep-2026, Familia y Salud: su menú y su pie entraron como si fueran la hoja. «Divulga
    # la Web» encabeza una lista de carteles descargables; «Se encuentra usted aquí» es la miga
    # de pan. Ninguna de las dos es información para un padre, y las dos son citables si se
    # quedan dentro.
    "Divulga la Web",
    "Se encuentra usted aquí",
    "Noticias Quienes somos",
)
_HEADING_SIZE = {"h1": 20.0, "h2": 15.0, "h3": 13.0, "h4": 12.0}
BODY_SIZE = 10.0


def _main_node(soup: BeautifulSoup) -> Tag:
    # MedlinePlus: only the NLM-written summary is public domain (the link lists are not ours)
    for sel in (
        "#topic-summary",
        "main",
        "article",
        "#maincontent",
        "#main-content",
        ".main-content",
        "body",
    ):
        node = soup.select_one(sel)
        # 23-sep-2026: y que TENGA texto. Las fichas de Familia y Salud abren con
        # `<a id="main-content"></a>`, un ancla de accesibilidad de cero caracteres, y las cuatro
        # se perdieron enteras detrás de ella: la ingesta las rechazó por «needs OCR», que para
        # un HTML ni siquiera es verdad. Existir no es ser el contenido.
        if node is not None and len(node.get_text(" ", strip=True)) >= 200:
            return node
    return soup


def _drop_noise(node: Tag) -> None:
    for t in node.find_all(_DROP):
        t.decompose()
    for t in list(node.find_all(True, class_=True)):
        if t.decomposed or t.attrs is None:  # parent already removed in this loop
            continue
        raw_cls = t.get("class")
        cls = " ".join(raw_cls).lower() if isinstance(raw_cls, list) else str(raw_cls or "").lower()
        if any(h in cls for h in _DROP_CLASS_HINTS):
            t.decompose()


def extract_html(path: Path) -> Extracted:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    node = _main_node(soup)
    _drop_noise(node)
    lines: list[Line] = []
    for el in node.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th", "dt", "dd"]):
        if el.find_parent(["h1", "h2", "h3", "h4", "li", "p"]) is not None and el.name in (
            "p",
            "li",
        ):
            # nested paragraph inside a list item: keep the outer element only
            if el.name == "p":
                continue
        text = el.get_text(" ", strip=True)
        if not text or len(text) < 2 or any(text.startswith(s) for s in _SKIP_TEXT):
            continue
        size = _HEADING_SIZE.get(el.name, BODY_SIZE)
        lines.append(Line(text=text, size=size, bold=el.name in _HEADING_SIZE, page=1))
    return Extracted(
        path=path,
        sha256=file_sha256(path),
        pages=[PageText(number=1, lines=lines)],
        body_size=BODY_SIZE,
    )
