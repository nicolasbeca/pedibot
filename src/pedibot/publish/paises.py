"""De qué país habla un calendario de vacunas, y cómo se dice ese país en cada lengua.

El consejo sobre la fiebre vale igual en Hamburgo que en Sevilla. El calendario de vacunas no: el
MenACWY va a los 12 meses en Portugal y a los 12-14 AÑOS en Alemania. El corpus es asimétrico
(L20) y las mejores hojas para padres están en español, así que una guía en otro idioma se acaba
escribiendo desde el calendario español. Eso es legítimo mientras la guía diga que es el español.

Estas tablas vivían en `tests/test_vaccine_guides_name_their_country.py`, que mira las guías ya
publicadas. El 23-sep-2026 esa prueba pilló una guía portuguesa con las edades españolas sin
nombrar a España — catorce horas después de estar viva. Viven aquí para que el publicador pueda
negarse a escribirla; el candado de los tests las importa de aquí.
"""

from __future__ import annotations

#: La autoridad que firma cada fuente, y el país al que pertenece.
AUTORIDAD: dict[str, str] = {
    "Ministerio de Sanidad": "ES",
    "Consejo Interterritorial": "ES",
    "AEPap": "ES",
    "SEUP": "ES",
    "CDC": "US",
    "NHS": "GB",
    "RKI": "DE",
    "STIKO": "DE",
    "Santé publique France": "FR",
    "Direção-Geral da Saúde": "PT",
    "Ministério da Saúde": "BR",
}

#: Cómo se nombra cada país en cada idioma, **con las formas adjetivas**: la guía alemana dice
#: «das spanische Gesundheitsministerium», no «Spanien», y una primera versión de la comprobación
#: la dio por culpable por buscar sólo el sustantivo. Un candado que no conoce el idioma en el que
#: mira acusa a quien no debe.
NOMBRES: dict[str, dict[str, tuple[str, ...]]] = {
    "ES": {
        "es": ("España", "español", "española"),
        "en": ("Spain", "Spanish"),
        "fr": ("Espagne", "espagnol", "espagnole"),
        "de": ("Spanien", "spanisch"),
        "pt": ("Espanha", "espanhol", "espanhola"),
        "ru": ("Испани", "испанск"),
        "ar": ("إسبانيا", "الإسباني", "الإسبانية"),
        "hi": ("स्पेन", "स्पेनिश", "स्पैनिश"),
    },
    "GB": {
        "es": ("Reino Unido", "británic", "NHS", "inglés"),
        "en": ("UK", "United Kingdom", "NHS", "British"),
        "fr": ("Royaume-Uni", "NHS", "britannique"),
        "de": ("Vereinigten Königreich", "NHS", "britisch"),
        "pt": ("Reino Unido", "NHS", "britânic"),
        "ru": ("Великобритани", "NHS", "британск"),
        "ar": ("المملكة المتحدة", "NHS"),
        "hi": ("यूनाइटेड किंगडम", "NHS", "ब्रिटिश"),
    },
    "US": {
        "es": ("Estados Unidos", "CDC", "estadounidense"),
        "en": ("United States", "CDC", "US "),
        "fr": ("États-Unis", "CDC"),
        "de": ("Vereinigten Staaten", "CDC", "USA"),
        "pt": ("Estados Unidos", "CDC"),
        "ru": ("США", "CDC"),
        "ar": ("الولايات المتحدة", "CDC"),
        "hi": ("संयुक्त राज्य", "CDC"),
    },
    "DE": {
        "es": ("Alemania", "alemán", "alemana", "RKI", "STIKO"),
        "en": ("Germany", "German", "RKI", "STIKO"),
        "fr": ("Allemagne", "allemand", "allemande", "RKI", "STIKO"),
        "de": ("Deutschland", "deutsch", "RKI", "STIKO"),
        "pt": ("Alemanha", "alemão", "alemã", "RKI", "STIKO"),
        "ru": ("Германи", "немецк", "RKI", "STIKO"),
        "ar": ("ألمانيا", "الألماني", "STIKO"),
        "hi": ("जर्मनी", "जर्मन", "STIKO"),
    },
    "FR": {
        "es": ("Francia", "francés", "francesa"),
        "en": ("France", "French"),
        "fr": ("France", "français", "française"),
        "de": ("Frankreich", "französisch"),
        "pt": ("França", "francês", "francesa"),
        "ru": ("Франци", "французск"),
        "ar": ("فرنسا", "الفرنسي", "الفرنسية"),
        "hi": ("फ़्रांस", "फ्रांस", "फ्रेंच"),
    },
    "PT": {
        "es": ("Portugal", "portugués", "portuguesa"),
        "en": ("Portugal", "Portuguese"),
        "fr": ("Portugal", "portugais", "portugaise"),
        "de": ("Portugal", "portugiesisch"),
        "pt": ("Portugal", "português", "portuguesa"),
        "ru": ("Португали", "португальск"),
        "ar": ("البرتغال", "البرتغالي", "البرتغالية"),
        "hi": ("पुर्तगाल", "पुर्तगाली"),
    },
    "BR": {
        "es": ("Brasil", "brasileño", "brasileña"),
        "en": ("Brazil", "Brazilian"),
        "fr": ("Brésil", "brésilien", "brésilienne"),
        "de": ("Brasilien", "brasilianisch"),
        "pt": ("Brasil", "brasileiro", "brasileira"),
        "ru": ("Бразили", "бразильск"),
        "ar": ("البرازيل", "البرازيلي", "البرازيلية"),
        "hi": ("ब्राज़ील", "ब्राजील", "ब्राज़ीली"),
    },
}

#: Cuándo se exige el país: sólo donde el país cambia el contenido.
ES_DE_UN_PAIS = ("vacun", "vaccin", "calendario", "calendar", "impf")


def pais_de_las_fuentes(fuentes: list[tuple[str, str]]) -> str | None:
    """El país cuya autoridad firma la mayoría de las citas, si hay una clara.

    `fuentes` son pares (organismo, título del documento). Se pide el 80 % para no acusar a una
    guía que apoya una frase suelta en el CDC y el resto en la OMS.
    """
    paises = []
    for org, titulo in fuentes:
        texto = f"{org} {titulo}"
        paises.extend(p for clave, p in AUTORIDAD.items() if clave in texto)
    if not paises:
        return None
    top = max(set(paises), key=paises.count)
    return top if paises.count(top) / len(paises) >= 0.8 else None


def nombra_el_pais(cuerpo: str, pais: str, lang: str) -> bool:
    """¿El texto dice, en la lengua en la que está escrito, de qué país es el calendario?"""
    formas = NOMBRES.get(pais, {}).get(lang)
    if not formas:
        return True  # no sabemos nombrarlo en esa lengua: no se acusa a ciegas
    bajo = cuerpo.lower()
    return any(n.lower() in bajo for n in formas)
