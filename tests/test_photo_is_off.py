"""Las fotos del niño, apagadas por defecto (28-sep-2026).

La comprobación de foto enviaba la imagen de la piel, los labios o la cara de un niño al modelo de
visión de un proveedor externo, y la política de privacidad no lo decía. Se había usado una vez en
un mes. Se apaga en el código —no sólo en el servidor— para que tampoco venga encendida en una
copia instalada desde cero, y la web deja de enseñar el botón: un 📷 que contesta «no disponible»
es peor que no tenerlo. Volver a encenderla es una decisión, con aviso y consentimiento delante.
"""

from __future__ import annotations

import pathlib

from pedibot.settings import Settings

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_the_photo_check_is_off_unless_someone_turns_it_on(monkeypatch) -> None:
    monkeypatch.delenv("PHOTO_ENABLED", raising=False)
    assert Settings(_env_file=None).photo_enabled is False


def test_the_chat_only_shows_the_camera_when_the_build_asks_for_it() -> None:
    chat = (ROOT / "web" / "site" / "src" / "components" / "Chat.astro").read_text(encoding="utf-8")
    boton = chat.index('id="photo-btn"')
    antes = chat[max(0, boton - 400) : boton]
    assert "PUBLIC_PHOTO_ENABLED" in antes, "el botón de la cámara se pinta sin preguntar"


def test_the_built_site_has_no_camera_button() -> None:
    dist = ROOT / "web" / "site" / "dist" / "index.html"
    if not dist.exists():
        return
    assert 'id="photo-btn"' not in dist.read_text(encoding="utf-8")
