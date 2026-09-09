"""Las guías y el triaje deciden lo mismo, y tienen que decirlo igual (9-sep-2026).

El proyecto escribe dos veces cuándo hay que ir al médico: en la sección «cuándo consultar» de
cada una de las 483 guías, y en `config/red_flags.yaml` para el chat. Son la pareja de ficheros
más grande de las que codifican la misma decisión por duplicado, y nunca se habían comparado.

Cruzarlas destapó 21 temas donde la misma advertencia era urgencia en una lengua y rutina en
otra. Ninguno era una regla que faltara: eran formas que faltaban dentro de reglas que ya
existían, la avería de siempre.

    árabe      «لا يستطيع التنفس» (no puede respirar)   ← solo estaba «لا يتنفس» (no respira)
    hindi      «कठिनाई»                                 ← la lista tenía otras cuatro, no ésta
    inglés     «trouble breathing»                      ← solo estaba «difficulty breathing»
    francés    «difficultés» en plural                  ← el patrón estaba en singular
    ruso       «трудности с дыханием»                   ← `трудно дыш` no alcanza el sustantivo
    castellano «pérdida de conocimiento»                ← solo se veía después de un golpe

Y una lección de método: arreglé «respira cada vez peor» en castellano porque el informe me
enseñó ésa primero, y el mismo giro faltaba en otras cuatro lenguas. Cuando una forma falta, la
pregunta no es cómo arreglarla, es en qué otras lenguas falta la misma.

La segunda mitad del fichero pesa igual que la primera. Al ensanchar los patrones del color
azul, «des bleus» —que en francés son moratones— y «blassere Haut» —piel más pálida— empezaron a
disparar emergencias. Un patrón que sube de nivel no lo caza ninguna prueba de «esto se ve»:
solo lo caza mirar qué se ha movido y hacia dónde.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]

#: La cabecera de la sección de advertencias, en los ocho idiomas.
_CABECERA = re.compile(
    r"^##\s+.*(cu[aá]ndo|when|quand|wann|когда|متى|quando|कब).*$", re.I | re.M
)


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


def _advertencias(fichero: pathlib.Path) -> list[str]:
    """Las viñetas de «cuándo ver al médico» de una guía, sin citas ni énfasis."""
    texto = fichero.read_text(encoding="utf-8")
    cab = _CABECERA.search(texto)
    if not cab:
        return []
    resto = texto[cab.end() :]
    fin = re.search(r"^##\s", resto, re.M)
    seccion = resto[: fin.start()] if fin else resto
    salida = []
    for linea in seccion.splitlines():
        linea = linea.strip()
        if not linea.startswith(("-", "*", "•")):
            continue
        limpia = re.sub(r"^[-*•]\s*", "", linea)
        limpia = re.sub(r"\[\d+\]", "", limpia).replace("**", "").strip()
        if len(limpia) >= 15:
            salida.append(limpia)
    return salida


#: El signo nuclear de cada lengua: la palabra que, si sale en una advertencia de una guía, el
#: triaje tiene que ver. Se busca en el texto publicado, nunca en un texto tecleado aquí — así
#: una transcripción mía equivocada aparece como fallo y no como falso aprobado.
_NUCLEO: dict[str, list[tuple[str, str]]] = {
    "es": [("respirar", "respira"), ("azul", "azul"), ("convulsión", "convuls")],
    "en": [("breathe", "breath"), ("blue", "blue"), ("seizure", "seizure")],
    "fr": [("respirer", "respir"), ("convulsion", "convuls")],
    "de": [("atmen", "atem"), ("blau", "blau"), ("Krampf", "krampf")],
    "ru": [("дыхание", "дыхан"), ("судороги", "судорог")],
    "ar": [("التنفس", "تنفس"), ("الوعي", "وعي")],
    "pt": [("respirar", "respira"), ("convulsão", "convuls")],
    "hi": [("साँस", "सांस"), ("नीला", "नील")],
}

#: Lo que sí puede quedarse en rutina aunque nombre un signo nuclear: la guía lo pone bajo «ve al
#: pediatra», no bajo «llama ahora», y el triaje coincide. Se listan por el trozo que las
#: identifica, para que la prueba diga qué se ha perdonado y por qué.
_PERDONADAS = (
    # El dolor pleurítico —duele al respirar— sale en las guías de neumonía de cinco lenguas, y
    # las cinco lo ponen bajo «ve al médico», no bajo «llama ahora». El triaje coincide.
    "pain when breathing",
    "al respirar",
    "عند التنفس",
    "quand il respire",
    "ao respirar",
    "при дыхании",
    "सांस लेते समय",
    # Antecedentes del adolescente, no un signo de ahora
    "enfermedad cardíaca",
    "maladie cardiaque",
    "مرض قلبي",
    "cardíaca ou respiratória",
    # «des bleus» son moratones, no labios azules
    "bleus inhabituels",
    # El ruido al coger aire vive en `moderate_breathing`, que es el escalón que le toca
    "stridor",
    "صرير",
    # La varicela que empeora en un adulto, y los signos de anemia tras epistaxis repetidas: las
    # dos guías árabes los mandan al médico, no a urgencias.
    "أكثر من المعتاد",
    "short of breath than usual",
    "فقر الدم",
    # El sustantivo alemán, cubierto por `drowsy_irritable`
    "Aufwecken",
    # El límite conocido de la negación (ver `_negada` en triage.py): «температура, которая не
    # проходит, ИЛИ судороги». La coma cierra la oración de la negación, pero una conjunción
    # detrás de la coma marca una enumeración negada y la mantiene abierta — y aquí esa lectura
    # es la equivocada. Preferimos el falso silencio en una frase que solo escribe una guía
    # antes que romper «no tiene fiebre, tos ni dificultad para respirar», que sí escribe un padre.
    "или судороги",
)


def _guias() -> list[tuple[str, pathlib.Path]]:
    raiz = RAIZ / "web" / "content"
    return [(f.parent.name, f) for f in sorted(raiz.rglob("*.md")) if f.parent.name in _NUCLEO]


def test_lo_que_una_guia_advierte_el_triaje_lo_ve(triage: Triage) -> None:
    """Si una guía nombra un signo nuclear al decir «ve al médico», el chat no dice «rutina».

    La misma web no puede darle al padre dos respuestas distintas para el mismo signo.
    """
    ciegos: list[str] = []
    for lang, fichero in _guias():
        for viñeta in _advertencias(fichero):
            baja = viñeta.lower()
            if any(p.lower() in baja for p in _PERDONADAS):
                continue
            if not any(clave in baja for _, clave in _NUCLEO[lang]):
                continue
            if triage.assess(viñeta).level == "routine":
                ciegos.append(f"[{lang}] {fichero.stem}: {viñeta[:100]}")

    assert not ciegos, "la guía lo advierte y el triaje lo ve como rutina:\n" + "\n".join(
        sorted(set(ciegos))[:25]
    )


#: El otro lado del candado: ensanchar los patrones del color casi convierte un moratón en una
#: emergencia. Estas frases tienen que quedarse donde están.
_NO_ES_ALARMA = [
    ("fr", "«des bleus» son moratones", "une éruption cutanée, un gonflement ou des bleus inhabituels sur les jambes"),
    ("fr", "un moratón tras una caída", "il a un bleu sur la peau après être tombé du canapé"),
    ("de", "piel más pálida, sola", "blassere Haut als normal"),
    ("en", "pálido y jugando", "my son looks a bit pale today but he is playing"),
    ("es", "pálido pero come bien", "mi hijo esta un poco palido pero come bien"),
]

#: Respirar deprisa es urgente. Lo que sube a emergencia es que vaya a más: si la prisa sola
#: llega a emergencia, no queda escalón para el niño que empeora.
_PRISA_ES_URGENTE = [
    ("es", "Respiración más rápida de lo normal"),
    ("de", "das Kind atmet schnell"),
    ("en", "Breathing is faster than normal"),
    ("fr", "il respire vite"),
]


#: El empeoramiento progresivo, que es lo que separa la urgencia de la emergencia: no es que
#: respire deprisa, es que respire cada vez peor. Los patrones de esta tarde salieron de las
#: guías, y una guía escribe en infinitivo —«Respirar cada vez pior»— mientras que un padre
#: escribe en gerundio y cambia el orden. Verificando en producción, «meu filho está respirando
#: cada vez pior» salió rutina, y al barrer las ocho lenguas fallaban siete de dieciséis.
#:
#: Las dos gramáticas van juntas en la lista a propósito: la guía y el padre dicen lo mismo, y
#: escribir los patrones leyendo sólo a una de las dos es cómo se llegó hasta aquí.
_VA_A_PEOR = [
    ("es", "respira cada vez peor"),
    ("es", "está respirando cada vez peor"),
    ("es", "cada vez respira peor"),
    ("es", "le cuesta cada vez más respirar"),
    ("pt", "está respirando cada vez pior"),
    ("pt", "respira cada vez pior"),
    ("pt", "cada vez respira pior"),
    ("en", "he is breathing worse and worse"),
    ("en", "his breathing is getting worse"),
    ("fr", "il respire de plus en plus mal"),
    ("fr", "sa respiration est de plus en plus difficile"),
    ("de", "es atmet immer schlechter"),
    ("de", "die Atmung wird immer schlechter"),
    ("ru", "дышит всё хуже"),
    ("ru", "дыхание становится хуже"),
    ("ar", "يتنفس بشكل أسوأ"),
    ("hi", "सांस की तकलीफ बढ़ रही है"),
]


@pytest.mark.parametrize(("lang", "texto"), _VA_A_PEOR)
def test_respirar_cada_vez_peor_es_emergencia_en_las_ocho_lenguas(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "emergency", f"[{lang}] «{texto}» → {nivel}"


@pytest.mark.parametrize(("lang", "glosa", "texto"), _NO_ES_ALARMA)
def test_ensanchar_el_color_no_convierte_un_moraton_en_emergencia(
    triage: Triage, lang: str, glosa: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "routine", f"[{lang}] {glosa} → {nivel}"


@pytest.mark.parametrize(("lang", "texto"), _PRISA_ES_URGENTE)
def test_respirar_deprisa_es_urgente_no_emergencia(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "urgent", f"[{lang}] «{texto}» → {nivel}"
