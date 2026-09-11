"""Las dos publicaciones periódicas que no dependen de que se genere una guía (11-sep-2026).

Hasta hoy Bluesky sólo recibía algo cuando `pedibot publish` creaba una guía nueva. Como no
había ningún timer que lo lanzara —se descubrió el 11-sep buscando por qué Bing no rastreaba—,
la última publicación era del 4 de septiembre. Encargo del operador:

1. **Del proyecto**, cada dos días: qué es PediBot y qué sabe hacer.
2. **De una guía por idioma**, una vez a la semana: ocho publicaciones, una en cada lengua.

Regla que manda sobre las dos: **ninguna cifra se escribe a mano**. Los números salen del índice
y de los ficheros de configuración en el momento de publicar, porque `CLAUDE.md` prohíbe repetir
métricas no medidas desde que se heredó el dossier de 2025, y esto va hacia fuera.
"""

from __future__ import annotations

import json
import pathlib
import re
import sqlite3
from typing import Any

from pedibot.publish.social import Post
from pedibot.settings import ROOT

LANGS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")

#: Cada mensaje dice UNA cosa verdadera y lleva a la página donde se comprueba. Sin superlativos,
#: sin etiquetas y sin hablar de dinero. Sólo inglés y castellano: son los dos públicos que el
#: registro de búsqueda enseña de verdad (España 365 impresiones, EE. UU. 191 en 90 días), y las
#: ocho lenguas ya salen cada semana en la publicación de guías.
PROJECT_POSTS: dict[str, list[dict[str, str]]] = {
    "en": [
        {
            "text": "PediBot answers questions about your child from {documents} verified "
            "paediatric documents — NHS, WHO, CDC, SEUP, AEP and others. If the sources do not "
            "say it, PediBot does not say it.",
            "path": "/",
        },
        {
            "text": "Paracetamol and ibuprofen by weight, read from fixed tables taken from the "
            "dosing guide. No language model does the arithmetic, ever.",
            "path": "/dose",
        },
        {
            "text": "Childhood vaccination schedules for {schedules} countries, each transcribed "
            "from its own official source and dated.",
            "path": "/vaccines",
        },
        {
            "text": "When should a child go to hospital? A checklist built from the warning signs "
            "in the paediatric emergency sheets, with the right number for {countries} countries.",
            "path": "/emergency",
        },
        {
            "text": "{guides} guides for parents, every claim with the body it came from at the "
            "foot of the page. Free, no account, no trackers.",
            "path": "/guides",
        },
        {
            "text": "Ask in any of {languages} languages. The warning-sign rules are written in "
            "all of them, not translated from one — that difference is the safety layer.",
            "path": "/",
        },
    ],
    "es": [
        {
            "text": "PediBot responde sobre tu hijo a partir de {documents} documentos "
            "pediátricos verificados: AEP, SEUP, AEPap, OMS, NHS y más. Si las fuentes no lo "
            "dicen, PediBot no lo dice.",
            "path": "/es",
        },
        {
            "text": "Paracetamol e ibuprofeno por peso, leídos de tablas fijas de la guía de "
            "dosificación. El modelo no multiplica nunca.",
            "path": "/es/dose",
        },
        {
            "text": "Calendarios de vacunación infantil de {schedules} países, cada uno "
            "transcrito de su fuente oficial y con su fecha.",
            "path": "/es/vaccines",
        },
        {
            "text": "¿Cuándo hay que ir a urgencias? Una lista hecha con los signos de alarma de "
            "las hojas de urgencias pediátricas, y el teléfono de {countries} países.",
            "path": "/es/emergency",
        },
        {
            "text": "{guides} guías para padres, con el organismo del que sale cada frase al pie "
            "de la página. Gratis, sin cuenta y sin rastreadores.",
            "path": "/es/guides",
        },
        {
            "text": "Pregunta en {languages} idiomas. Las reglas de los signos de alarma están "
            "escritas en todos, no traducidas de uno — esa diferencia es la capa de seguridad.",
            "path": "/es",
        },
    ],
}


def site_url() -> str:
    """El mismo `SITE_URL` que lee la construcción de la web, con el mismo valor por defecto."""
    import os

    return os.environ.get("SITE_URL", "https://pedibot.xyz").rstrip("/")


def facts() -> dict[str, int]:
    """Los números, leídos de donde viven. Nunca escritos en el texto."""
    import yaml

    docs = 0
    db = ROOT / "index" / "pedibot.db"
    if db.exists():
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        docs = con.execute("SELECT COUNT(DISTINCT doc_id) FROM chunks").fetchone()[0]
        con.close()

    def _cuantos(nombre: str) -> int:
        f = ROOT / "config" / nombre
        if not f.exists():
            return 0
        d = yaml.safe_load(f.read_text(encoding="utf-8"))
        return len(d.get("countries", d)) if isinstance(d, dict) else len(d)

    return {
        "documents": docs,
        "schedules": _cuantos("vaccines.yaml"),
        "countries": _cuantos("emergency_numbers.yaml"),
        "guides": len(list((ROOT / "web" / "content").rglob("*.md"))),
        "languages": len(LANGS),
    }


def _state(path: pathlib.Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8", newline="\n")


def _default_state() -> pathlib.Path:
    return ROOT / "data" / "broadcast_sent.json"


def project_post(
    lang: str | None = None,
    state_path: pathlib.Path | None = None,
    advance: bool = True,
) -> Post:
    """El siguiente mensaje del proyecto, alternando idioma y sin repetir hasta agotarlos."""
    p = state_path or _default_state()
    st = _state(p)
    n = int(st.get("project_n", 0))
    idiomas = list(PROJECT_POSTS)
    idioma = lang or idiomas[n % len(idiomas)]
    plantillas = PROJECT_POSTS[idioma]
    # el índice avanza sobre el total, así que alterna idioma Y cambia de mensaje cada vez
    tpl = plantillas[(n // len(idiomas)) % len(plantillas)]
    if advance:
        st["project_n"] = n + 1
        _save(p, st)
    return Post(
        title=tpl["text"].format(**facts()),
        summary="",
        url=f"{site_url()}{tpl['path']}",
        lang=idioma,
    )


def _guides_by_lang() -> dict[str, list[tuple[str, str, str]]]:
    """(slug, título, descripción) por idioma, leídos del frontmatter publicado."""
    out: dict[str, list[tuple[str, str, str]]] = {}
    for lang in LANGS:
        d = ROOT / "web" / "content" / lang
        filas: list[tuple[str, str, str]] = []
        for md in sorted(d.glob("*.md")) if d.exists() else []:
            head = md.read_text(encoding="utf-8")[:900]
            t = re.search(r'^title:\s*"(.*?)"\s*$', head, re.M)
            desc = re.search(r'^description:\s*"(.*?)"\s*$', head, re.M)
            if t:
                filas.append((md.stem, t.group(1), desc.group(1) if desc else ""))
        out[lang] = filas
    return out


def weekly_guides(
    state_path: pathlib.Path | None = None, advance: bool = True
) -> list[Post]:
    """Una guía por idioma, la que lleve más tiempo sin salir."""
    p = state_path or _default_state()
    st = _state(p)
    hechas: dict[str, list[str]] = dict(st.get("guides_done", {}))
    posts: list[Post] = []
    base = site_url()
    for lang, filas in _guides_by_lang().items():
        if not filas:
            continue
        ya = list(hechas.get(lang, []))
        quedan = [f for f in filas if f[0] not in ya]
        if not quedan:  # agotado el idioma: se vuelve a empezar
            ya, quedan = [], filas
        slug, titulo, desc = quedan[0]
        prefijo = "" if lang == "en" else f"/{lang}"
        posts.append(Post(titulo, desc, f"{base}{prefijo}/guides/{slug}", lang))
        hechas[lang] = [*ya, slug]
    if advance:
        st["guides_done"] = hechas
        _save(p, st)
    return posts
