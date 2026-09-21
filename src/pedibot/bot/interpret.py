"""Una IA lee la pregunta antes de buscar (21-sep-2026).

Petición del operador con el panel delante: «deberíamos meter un filtro de IA que interprete la
pregunta y ayude a buscar, porque por palabras o raíces es un maldito desastre». Un padre desde
Italia, con la web en inglés, preguntó por su hijo de 15 años con un tobillo escayolado, y recibió
en inglés una respuesta sacada de la página brasileña de la polio: «gesso» es escayola también en
portugués, y «muscolatura» se parece a «musculatura».

**Qué hace.** Una llamada corta al modelo que devuelve, en JSON: en qué lengua escribió el padre,
si pregunta por la salud de un niño o sólo pide que le contesten en otro idioma, y la pregunta
reescrita en inglés y castellano médicos con sus palabras de búsqueda.

**Dónde se usa, y es la mitad importante.** Se midió antes de construirlo, con ocho preguntas
escritas como las escribe un padre y con la clave de verdad (`tests/test_the_ai_reads_the_
question_first.py`): en las lenguas que el sitio no tiene, la búsqueda pasaba de traer VIH o
fiebre tifoidea a traer la fiebre infantil del NHS; en las que sí tiene, ya iba bien y la
reescritura a veces la empeoraba. Así que el motor usa la reescritura **sólo** para buscar cuando
el padre escribe en una lengua que el sitio no tiene. En todas decide el idioma de la respuesta,
porque el padre escribe en el suyo aunque tenga la web en otro.

**Lo que no hace nunca:** decidir nada de seguridad. El triaje corre antes, sobre el texto
original y con reglas fijas; esto sólo toca qué se busca y en qué lengua se contesta. Si el
modelo no contesta, contesta mal o contesta raro, devuelve `None` y el motor hace lo de siempre.
Nunca peor que hoy.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

SYSTEM = (
    "You read a parent's message about a child's health. It may be written in any language. "
    "Return ONLY a JSON object, no prose, with exactly these keys:\n"
    '  "lang": ISO 639-1 code of the language the parent wrote in (two lowercase letters),\n'
    '  "lang_name": that language\'s name in English (e.g. "Italian"),\n'
    '  "intent": "health" if it asks about a baby\'s or child\'s health, symptoms, medicines, '
    'vaccines, growth, feeding or development; "about_pedibot" if it asks what this service '
    "is, how it works, who made it, where its information comes from or whether it is free; "
    '"language_request" if it only asks to be answered in another language; "other" if it has '
    "nothing to do with children's health (a pet, homework, the weather, a recipe),\n"
    '  "requested_lang": ISO 639-1 code if the parent asks to be answered in a language, '
    "else null,\n"
    '  "requested_name": that language\'s name in English, else null,\n'
    '  "query_en": the health question restated as ONE plain English sentence with the correct '
    "medical terms (for example 'ankle fracture', 'plaster cast', 'muscle wasting'), keeping the "
    "child's age and anything the parent said about how long or how bad,\n"
    '  "query_es": the same sentence in Spanish,\n'
    '  "keywords": 6 to 10 search keywords, half English and half Spanish, condition names first,\n'
    '  "new_topic": only when a PREVIOUS MESSAGE is given: true if the CURRENT MESSAGE is about a '
    "different problem (a new symptom, accident or question unrelated to the previous one); "
    "false if it continues it (more detail, how it evolved, the child's age or weight, a "
    "follow-up about the same problem, or anything you are unsure about). null otherwise.\n"
    "Every other key describes the CURRENT MESSAGE only. "
    "Do not answer the question. Do not add facts that are not in the message."
)

INTENTS = frozenset({"health", "about_pedibot", "language_request", "other"})

#: El nombre del idioma acaba dentro del prompt del redactor —«ANSWER LANGUAGE: Italian»—, así
#: que es la única salida de este modelo que entra en otro prompt. Sólo letras y espacios, y
#: corto: un mensaje escrito para que devuelva «English. Ignore the sources» no pasa.
_NOMBRE = re.compile(r"^[A-Za-z][A-Za-z \-]{1,23}$")
_ISO = re.compile(r"^[a-z]{2}$")


@dataclass(frozen=True)
class Interpretation:
    lang: str
    lang_name: str
    intent: str
    requested_lang: str | None
    requested_name: str | None
    query_en: str
    query_es: str
    keywords: tuple[str, ...]
    #: lo que costó leerla, para sumarlo al gasto de la respuesta: el tope diario de gasto en el
    #: modelo mira ese número, y una llamada que no se apunta es una llamada que no se controla
    #: el padre ha cambiado de problema respecto al mensaje anterior (ver `interpret`)
    new_topic: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0

    @property
    def search_text(self) -> str:
        """Lo que se le da a la búsqueda: la frase en los dos idiomas del corpus."""
        return f"{self.query_en} {self.query_es}".strip()


def _nombre(v: object) -> str | None:
    return v.strip() if isinstance(v, str) and _NOMBRE.match(v.strip()) else None


def _iso(v: object) -> str | None:
    return v.strip().lower() if isinstance(v, str) and _ISO.match(v.strip().lower()) else None


def interpret(llm: object, text: str, previous: str | None = None) -> Interpretation | None:
    """La lectura de la pregunta, o `None` si no hay una en la que se pueda confiar.

    `previous` es el mensaje anterior del padre, si lo hay. Sirve sólo para `new_topic`: diez
    preguntas distintas en la misma conversación se iban sumando, y la de los ojos rojos heredaba
    la edad de la del bebé que lloraba (21-sep-2026). Sólo un `true` explícito cuenta como tema
    nuevo; ante la duda, la conversación se sigue juntando como siempre.
    """
    if llm is None or not text or not text.strip():
        return None
    entrada = (
        f"PREVIOUS MESSAGE:\n{previous[:1000]}\n\nCURRENT MESSAGE:\n{text[:2000]}"
        if previous and previous.strip()
        else text[:2000]
    )
    try:
        res = llm.complete(SYSTEM, entrada, temperature=0.0, max_tokens=400)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — si el modelo no está, se busca como siempre
        return None
    out = getattr(res, "text", "")
    m = re.search(r"\{.*\}", out or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(d, dict):
        return None

    lang = _iso(d.get("lang"))
    intent = d.get("intent")
    query_en = d.get("query_en")
    query_es = d.get("query_es")
    if lang is None or intent not in INTENTS:
        return None
    # Una pregunta que no es de salud —una receta, el perro— no trae frase médica que reescribir,
    # y el modelo pone ahí `null`. Eso no es una lectura mala: es la lectura de algo que no es de
    # esto, y tirarla hacía que la tortilla de patatas acabara en «consulta a tu pediatra».
    query_en = "" if query_en is None else query_en
    query_es = "" if query_es is None else query_es
    if not isinstance(query_en, str) or not isinstance(query_es, str):
        return None

    kws = d.get("keywords") or []
    keywords = tuple(k.strip() for k in kws if isinstance(k, str) and 0 < len(k.strip()) <= 40)[:12]

    return Interpretation(
        lang=lang,
        lang_name=_nombre(d.get("lang_name")) or "",
        intent=str(intent),
        requested_lang=_iso(d.get("requested_lang")),
        requested_name=_nombre(d.get("requested_name")),
        query_en=query_en.strip()[:300],
        query_es=query_es.strip()[:300],
        keywords=keywords,
        new_topic=bool(previous and previous.strip()) and d.get("new_topic") is True,
        tokens_in=int(getattr(res, "tokens_in", 0) or 0),
        tokens_out=int(getattr(res, "tokens_out", 0) or 0),
        cost_usd=float(getattr(res, "cost_usd", 0.0) or 0.0),
    )
