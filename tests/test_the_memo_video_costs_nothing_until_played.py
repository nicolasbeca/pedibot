"""El vídeo de la memo no le cuesta nada a quien no le da al play (9-oct-2026).

La memo lleva el vídeo de presentación para inversores. El sitio entero está hecho para quien
paga los datos por megas: una página que descargase de entrada varios megas de vídeo rompería
eso en la única página que no es para padres, y el service worker, que guarda en el móvil todo
lo que no es la API, metería el vídeo entero en la caché de cada lector que lo viese.
"""

from __future__ import annotations

import re

from pedibot.settings import ROOT

SITE = ROOT / "web" / "site"
MEMO = (SITE / "src" / "pages" / "memo.astro").read_text(encoding="utf-8")
SW = (SITE / "public" / "sw.js").read_text(encoding="utf-8")
VIDEO = SITE / "public" / "video" / "pedibot-pitch.mp4"
POSTER = SITE / "public" / "video" / "pedibot-pitch.jpg"


def _video_tag() -> str:
    m = re.search(r"<video\b[^>]*>", MEMO)
    assert m, "la memo no tiene vídeo"
    return m.group(0)


def test_the_memo_shows_the_video() -> None:
    tag = _video_tag()
    assert 'src="/video/pedibot-pitch.mp4"' in MEMO
    assert "controls" in tag


def test_nothing_downloads_until_play() -> None:
    tag = _video_tag()
    assert 'preload="none"' in tag, tag
    assert 'poster="/video/pedibot-pitch.jpg"' in tag, tag
    assert "autoplay" not in tag


def test_the_files_exist_and_are_light() -> None:
    assert VIDEO.exists() and POSTER.exists()
    assert VIDEO.stat().st_size < 10_000_000, VIDEO.stat().st_size
    assert POSTER.stat().st_size < 150_000, POSTER.stat().st_size


def test_the_service_worker_leaves_video_alone() -> None:
    """Va antes de cualquier `respondWith`: el navegador lo pide por trozos y no se guarda."""
    fetch = SW[SW.index("addEventListener('fetch'") :]
    salida = re.search(r"destination === 'video'[^\n]*\n\s*return;", fetch) or re.search(
        r"if \([^\n]*(destination === 'video'|\\\.mp4)[^\n]*\) return;", fetch
    )
    assert salida, "el service worker no deja pasar el vídeo"
    assert salida.start() < fetch.index("respondWith")
