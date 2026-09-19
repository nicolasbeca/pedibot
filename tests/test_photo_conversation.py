"""La foto entra en la conversación, con lo que se vio (9-sep-2026).

El bot mira una foto, ve unas manchas y le pide al padre que haga la prueba del vaso. Eso es
correcto: una imagen no puede saber si la mancha desaparece al apretar, así que la lectura se
queda en «urgente» y pide la comprobación que sí lo decide.

Pero la foto no se registraba como turno. Cuando el padre contestaba «no desaparecen cuando
aprieto» —la respuesta a lo que le acababan de pedir— ese mensaje llegaba solo, y solo es rutina.

    El producto pedía hacer la prueba del meningococo y luego no escuchaba la respuesta.

Ahora la foto deja escrito en la conversación lo que vio, con las mismas palabras que se le
enseñan al padre. No se inventa nada: se escribe el signo que el modelo de visión dijo haber
visto.
"""

from __future__ import annotations

import pytest

from pedibot.bot.photo import interpret, signs_seen
from pedibot.eval import fake_engine_from_settings

IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")

#: La respuesta del padre a la prueba del vaso, en los ocho idiomas.
RESPUESTA = {
    "en": "they don't fade when I press them",
    "es": "no desaparecen cuando aprieto",
    "fr": "elles ne disparaissent pas quand j'appuie",
    "de": "sie verschwinden nicht beim Draufdrücken",
    "ru": "они не бледнеют при надавливании",
    "ar": "لا تختفي عند الضغط عليها",
    "pt": "não somem quando aperto",
    "hi": "दबाने पर नहीं मिटते",
}

VISTO_MANCHAS = {
    "petechiae": "yes",
    "cyanosis": "no",
    "swelling": "no",
    "quality": "ok",
    "note": "",
}


@pytest.fixture(scope="module")
def engine():
    return fake_engine_from_settings()


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_photo_writes_down_what_it_saw_in_the_readers_language(lang: str) -> None:
    texto = signs_seen(VISTO_MANCHAS, lang)
    assert texto.strip(), f"[{lang}] la foto no deja constancia de lo que vio"


@pytest.mark.parametrize("lang", IDIOMAS)
def test_the_answer_to_the_glass_test_raises_the_alarm(engine, lang: str) -> None:
    """El circuito entero: la foto ve manchas, pide la prueba, el padre contesta."""
    historial = [
        {"role": "user", "text": "[foto] " + signs_seen(VISTO_MANCHAS, lang)},
        {"role": "assistant", "text": interpret(VISTO_MANCHAS, lang, "112")[1]},
    ]
    a = engine.ask(RESPUESTA[lang], lang=lang, history=historial)
    assert a.level == "emergency", (
        f"[{lang}] «{RESPUESTA[lang]}» tras una foto con manchas sale {a.level}"
    )


@pytest.mark.parametrize("lang", IDIOMAS)
def test_a_clean_photo_leaves_nothing_written(lang: str) -> None:
    """La otra mitad: una foto sin signos no puede meter palabras en la conversación que luego
    disparen nada."""
    limpia = {"petechiae": "no", "cyanosis": "no", "swelling": "no", "quality": "ok", "note": ""}
    assert signs_seen(limpia, lang) == ""


def test_a_photo_with_spots_is_urgent_and_asks_for_the_glass_test() -> None:
    """Y la lectura de la foto sigue siendo la prudente que era: urgente, no emergencia, porque
    una imagen no decide si la mancha desaparece al apretar. Lo que decide es la prueba."""
    nivel, texto = interpret(VISTO_MANCHAS, "es", "112")
    assert nivel == "urgent"
    assert "vaso" in texto.lower(), "la respuesta ya no pide la prueba del vaso"
