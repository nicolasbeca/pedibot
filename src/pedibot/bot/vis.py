"""La lista de hojas de vacunas traducidas, sin modelo (2-oct-2026).

Consulta real, EE. UU., 30-sep: «Vis translations» y «Vaccine information statements»; en vivo
el 2-oct, «VIS in Swahili». Las tres recibieron «no puedo confirmarlo», «¿qué te pasa?» o «no
tengo información fiable», con 40 hojas de Immunize.org en el índice. Quien pregunta así no
quiere un párrafo: quiere las hojas. La lista sale del catálogo (`config/fuentes.yaml`), con el
enlace al PDF entero, que es además lo que Immunize.org pide al darnos permiso (ops/PERMISOS.md).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

#: «VIS» como palabra entera, o el nombre largo; también el título suajili de las hojas.
_PIDE = re.compile(
    r"\bvis\b|vaccine information statements?|kauli ya taarifa ya chanjo", re.IGNORECASE
)

#: Lengua pedida → código. Los nombres en las ocho lenguas del sitio y en la propia lengua.
_LENGUA = {
    "sw": re.compile(r"swahili|suajili|souahéli|swahéli|suaíli|kiswahili|суахили|السواحيلية|स्वाहिली", re.I),
    "ar": re.compile(r"arab|árabe|arabe|арабск|عربي|العربية|अरबी", re.I),
    "hi": re.compile(r"hindi|hindí|хинди|الهندية|हिंदी|हिन्दी", re.I),
}
NOMBRE = {
    "sw": {"en": "Swahili", "es": "suajili", "fr": "swahili", "de": "Swahili", "ru": "суахили",
           "ar": "السواحيلية", "pt": "suaíli", "hi": "स्वाहिली"},
    "ar": {"en": "Arabic", "es": "árabe", "fr": "arabe", "de": "Arabisch", "ru": "арабский",
           "ar": "العربية", "pt": "árabe", "hi": "अरबी"},
    "hi": {"en": "Hindi", "es": "hindi", "fr": "hindi", "de": "Hindi", "ru": "хинди",
           "ar": "الهندية", "pt": "hindi", "hi": "हिंदी"},
}
CABECERA = {
    "en": "These are the CDC Vaccine Information Statements (VIS) that PediBot has, in the "
          "translations by Immunize.org, which gave us permission to use them. Each link opens "
          "the full sheet:",
    "es": "Estas son las hojas informativas de vacunas de los CDC (VIS) que tiene PediBot, en "
          "las traducciones de Immunize.org, que nos dio permiso para usarlas. Cada enlace abre "
          "la hoja entera:",
    "fr": "Voici les fiches d'information sur les vaccins des CDC (VIS) dont dispose PediBot, "
          "dans les traductions d'Immunize.org, qui nous a autorisés à les utiliser. Chaque lien "
          "ouvre la fiche complète :",
    "de": "Das sind die Impf-Informationsblätter der CDC (VIS), die PediBot hat, in den "
          "Übersetzungen von Immunize.org, das uns die Nutzung erlaubt hat. Jeder Link öffnet "
          "das ganze Blatt:",
    "ru": "Вот информационные листки CDC о вакцинах (VIS), которые есть у PediBot, в переводах "
          "Immunize.org, которая разрешила нам их использовать. Каждая ссылка открывает листок "
          "целиком:",
    "ar": "هذه هي نشرات معلومات اللقاحات الصادرة عن CDC (VIS) المتوفرة لدى PediBot، بترجمات "
          "Immunize.org التي أذنت لنا باستخدامها. كل رابط يفتح النشرة كاملة:",
    "pt": "Estas são as fichas informativas de vacinas do CDC (VIS) que o PediBot tem, nas "
          "traduções da Immunize.org, que nos deu permissão para usá-las. Cada link abre a ficha "
          "inteira:",
    "hi": "ये CDC के टीका सूचना पत्र (VIS) हैं जो PediBot के पास हैं, Immunize.org के अनुवाद में, "
          "जिसने हमें इनका उपयोग करने की अनुमति दी है। हर लिंक पूरा पत्र खोलता है:",
}


def pide_vis(pregunta: str) -> bool:
    return bool(_PIDE.search(pregunta or ""))


def lenguas_pedidas(pregunta: str) -> list[str]:
    """Las lenguas que nombra; ninguna nombrada son las tres."""
    dichas = [c for c, rx in _LENGUA.items() if rx.search(pregunta or "")]
    return dichas or list(_LENGUA)


@lru_cache(maxsize=2)
def hojas(catalogo: str) -> tuple[tuple[str, str, str], ...]:
    """(lengua, título, url) de cada hoja de Immunize.org del catálogo."""
    data = yaml.safe_load(Path(catalogo).read_text(encoding="utf-8")) or {}
    out = []
    for s in data.get("sources") or []:
        if s.get("org") == "Immunize.org" and s.get("url") and s.get("lang") in _LENGUA:
            out.append((s["lang"], str(s.get("title") or ""), str(s["url"])))
    return tuple(out)


def lista_vis(pregunta: str, lang: str, catalogo: Path) -> str | None:
    """El texto de la respuesta, o None si no hay hojas de esas lenguas."""
    partes = []
    todas = hojas(str(catalogo))
    for code in lenguas_pedidas(pregunta):
        suyas = [(t, u) for c, t, u in todas if c == code]
        if not suyas:
            continue
        nombre = NOMBRE[code].get(lang, NOMBRE[code]["en"])
        partes.append(f"{nombre[:1].upper()}{nombre[1:]} ({len(suyas)}):\n"
                      + "\n".join(f"- {t}: {u}" for t, u in suyas))
    if not partes:
        return None
    return CABECERA.get(lang, CABECERA["en"]) + "\n\n" + "\n\n".join(partes)
