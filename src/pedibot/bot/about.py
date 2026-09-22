"""Las preguntas sobre el propio PediBot, contestadas una a una (22-sep-2026).

Hasta hoy, cualquier pregunta sobre el servicio —«¿guarda las conversaciones?», «¿entiende
hindi?», «¿puede leer un informe del pediatra?», «¿puede buscar una farmacia abierta?»— recibía
el mismo párrafo de presentación. De las 854 preguntas de la batería del operador, 220 eran de
esas, y ninguna quedaba contestada.

Funciona igual que una pregunta de salud, cambiando las guías por una ficha nuestra
(`config/sobre_pedibot.md`): el modelo contesta **sólo** con lo que la ficha dice, y lo que no
está en la ficha no se dice. Los números de la ficha —cuántos documentos, cuántas reglas de
alarma, cuántos países— no están escritos a mano: se rellenan del sistema que está corriendo, que
es la única manera de que no envejezcan mal.

Y la mitad de estas preguntas son cosas que PediBot **no** puede hacer. Eso también es una
respuesta, y darla clara vale más que un folleto: quien pregunta si puede subir una foto de una
erupción necesita saber que no, hoy, no dentro de tres párrafos sobre guías pediátricas.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pedibot.settings import ROOT

SOBRE = (
    "You answer a parent's question about PediBot itself, using ONLY the card below. "
    "Rules:\n"
    "1. Answer the question that was asked, in the first sentence, and nothing else. If the "
    "answer is no, say no first.\n"
    "2. Use only what the card says. If the card does not answer the question, say plainly "
    "that you cannot confirm it, and say what you do know that is closest.\n"
    "3. Never invent a feature, a number, a price, a partner or a plan for the future.\n"
    "4. Two to four sentences, plain words a tired parent reads at 3 a.m. No lists, no "
    "headings, no markdown.\n"
    "5. Do not add a medical disclaimer: the page already carries one.\n"
    "6. If what is asked is something PediBot cannot do, say what it can do instead, in one "
    "sentence, only if the card names it.\n"
    "7. Write the whole answer in {language}.\n"
    "8. Web addresses are copied EXACTLY as the card writes them and are NEVER translated: "
    "pedibot.xyz/dose stays pedibot.xyz/dose, not pedibot.xyz/dosis. The one change allowed is "
    "the language, and ONLY these eight codes: es, en, fr, de, ru, ar, pt, hi. Then the code "
    "goes after the domain — pedibot.xyz/es/dose, pedibot.xyz/fr/growth. In ANY other language, "
    "Italian or Polish or Dutch included, write the address with no code at all "
    "(pedibot.xyz/dose): the page does not exist with another code and the link would be dead.\n"
    "9. Do not open with «yes» when the question is not a yes-or-no question.\n\n"
    "THE CARD:\n{card}"
)

#: Dónde vive la ficha. Fuera del código a propósito: la escribe quien sabe qué hace el sitio.
FICHA = ROOT / "config" / "sobre_pedibot.md"


@lru_cache(maxsize=8)
def _texto(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def ficha_de(*, docs: int, rules: int, countries: int, vax: int, path: Path | None = None) -> str:
    """La ficha con sus huecos rellenos por el sistema que está corriendo."""
    t = _texto(str(path or FICHA))
    return (
        t.replace("{docs}", str(docs))
        .replace("{rules}", str(rules))
        .replace("{countries}", str(countries))
        .replace("{vax}", str(vax))
    )


def responde_sobre(llm: object, pregunta: str, language: str, ficha: str) -> str | None:
    """La respuesta a una pregunta sobre PediBot, o `None` si no se puede redactar.

    `None` no es un fallo: el motor tiene el párrafo de presentación de siempre para caer en él.
    """
    if llm is None or not pregunta or not pregunta.strip() or not ficha:
        return None
    system = SOBRE.replace("{language}", language or "English").replace("{card}", ficha)
    try:
        res = llm.complete(system, pregunta.strip()[:600], temperature=0.2, max_tokens=400)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — si el modelo no está, se contesta como antes
        return None
    texto = (getattr(res, "text", "") or "").strip()
    return texto or None
