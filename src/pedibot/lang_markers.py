"""Palabras que sólo pertenecen a una de las ocho lenguas del sitio (16-sep-2026).

Vivían dentro de `scripts/check_lang_leak.py`, que revisa el sitio CONSTRUIDO: eso llega
después de publicar y de desplegar, o sea que sirve para enterarse y no para impedirlo. El
16-sep el servidor publicó una guía portuguesa con un encabezado medio en castellano —«Quando
acudir al médico ou a urgencias»— y estuvo viva: el publicador comprobaba el idioma con
`detect_lang` sobre el artículo entero, y el artículo era portugués. La fuga era una línea.

Así que la lista se muda aquí, al paquete, y la usan los dos: el guardián del sitio y el
publicador, antes de escribir el fichero.

La lista es corta a propósito. Una palabra sólo entra si NO existe en las otras siete: «dosis»
estuvo hasta que llegó el alemán, que la escribe igual, y «gratuit» tuvo que llevar espacio
detrás porque casaba dentro del «gratuito» español.
"""

from __future__ import annotations

from collections.abc import Iterable

MARKERS: dict[str, tuple[str, ...]] = {
    "es": (
        "¿",
        "años",
        "niño",
        "hijo",
        "qué ",
        "cómo",
        "vacunas",
        "urgencias",
        "guías",
        # "dosis" was a marker until German arrived and spells it the same way
        "síntomas",
        "medicación",
        "cuándo",
        "preguntas frecuentes",
    ),
    "en": (
        "child",
        "should",
        "what ",
        "when ",
        "vaccination schedule",
        "symptom diary",
        "dose calculator",
        "guidelines",
        "warning signs",
        "how it works",
        "common questions",
        "where they agree",
        "where they differ",
    ),
    # the last four were added on 4-sep: the German, Russian and Arabic home pages carried the
    # French title for weeks and none of the words above appear in it
    "fr": (
        "enfant",
        "urgences",
        "vaccinal",
        "posologie",
        "dois-je",
        "médicaments",
        "quels ",
        "âge",
        "santé",
        "questions fréquentes",
        "gratuit ",
        "réponses",
        "sourcé",
        "pour les parents",
        "toutes les",
    ),
    "de": (
        "kind",
        "notaufnahme",
        "impfkalender",
        "dosisrechner",
        "warnzeichen",
        "soll ich",
        "ratgeber",
        "häufige fragen",
        "quellen",
        "symptomtagebuch",
    ),
    # Russian is in its own script, so any Cyrillic at all on a non-Russian page is a leak
    "ru": (
        "ребён",
        "ребен",
        "температур",
        "прививк",
        "источник",
        "калькулятор доз",
        "тревожн",
        "статьи для родителей",
        "дневник симптомов",
    ),
    "ar": (
        "طفل",
        "الطوارئ",
        "التطعيمات",
        "حاسبة الجرعات",
        "المصادر",
        "علامات التحذير",
        "أدلة للوالدين",
        "مفكرة الأعراض",
    ),
    # Portuguese words that Spanish does not spell the same way, which is the only real risk here
    "pt": (
        "criança",
        "você",
        "vômitos",
        "diretrizes",
        "pronto-socorro",
        "não ",
        "guias para pais",
        "sinais de alarme",
    ),
    # Devanagari is its own script, so any of it on a non-Hindi page is a leak by itself;
    # these are the words the Hindi pages actually print, for the reverse direction
    "hi": (
        "बच्चे",
        "बुखार",
        "टीक",
        "इमरजेंसी",
        "खुराक",
        "स्रोत",
        "गाइड",
        "चेतावनी के निशान",
        "आम सवाल",
    ),
}


def foreign_markers(text: str, lang: str, names: Iterable[str] = ()) -> list[tuple[str, str]]:
    """(lengua ajena, palabra encontrada) por cada lengua que asoma en este texto.

    `names` son nombres propios que se citan igual en todas las lenguas —organismos, marcas—:
    «Sociedad Española de Urgencias de Pediatría» en una página inglesa es una cita, no una
    página publicada en castellano.
    """
    low = text.lower()
    for n in names:
        low = low.replace(n.lower(), " ")
    found: list[tuple[str, str]] = []
    for other, words in MARKERS.items():
        if other == lang:
            continue
        for w in words:
            if w in low:
                found.append((other, w.strip()))
                break
    return found
