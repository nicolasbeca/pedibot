"""Claves que casan por prefijo, y las que no pueden (10-sep-2026).

La taxonomía y la tabla de sinónimos casan sus claves **por prefijo**, y así tiene que ser:
«vomit» debe coger «vomiting», «vacuna» debe coger «vacunación». Con ocho idiomas en la misma
lista, eso produce falsos amigos, y salieron cinco al auditar las claves contra el vocabulario
real de las 483 guías publicadas:

    uti     → utilisez, utilizar, utiliser   (74 apariciones)
    wee     → weeks, week                    (78)
    dent    → dentro                         (20)
    ear     → early                          (85)
    infant  → infantil                       (62)

Los tres primeros los había añadido yo la víspera, al crear las categorías `urinario` y
`dental`. Los dos últimos llevaban ahí desde el principio y son los que más pesan: «early» es de
las palabras más corrientes del inglés e «infantil» un adjetivo que un padre español usa a todas
horas —«salud infantil», «silla infantil»—, y caía en `lactante`, que es cólico, llanto y
reflujo.

Un tema equivocado hace tres cosas, y ninguna se ve: multiplica por 1,5 los fragmentos de ese
tema, por 0,7 todos los demás, y **baja la puerta del «fuente o silencio» de tres términos a
uno**. Medido: «mi perro se ha comido una tableta de chocolate» devolvía SEIS fuentes —folletos
de actividad física de la OMS— porque «tableta» disparaba el sinónimo «tablet» → «screen time»,
y ese término le daba un tema a la pregunta.

La solución no es quitar las claves, que hacen falta: es poder decir «esta palabra entera». Una
clave terminada en `$` casa la palabra completa y nada más, en los dos ficheros y con la misma
marca.
"""

from __future__ import annotations

import collections
import pathlib
import re

import pytest
import yaml

from pedibot.bot.retrieval import Synonyms
from pedibot.ingest.classify import Taxonomy

RAIZ = pathlib.Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "config"


@pytest.fixture(scope="module")
def tax() -> Taxonomy:
    return Taxonomy(CONFIG / "taxonomia.yaml")


@pytest.fixture(scope="module")
def syn() -> Synonyms:
    return Synonyms(CONFIG / "synonyms.yaml", CONFIG / "drugs.yaml")


#: Frases corrientes que NO deben recibir el tema que la clave por prefijo les daba.
NO_ES_ESE_TEMA = [
    ("¿qué es la salud infantil?", "lactante"),
    ("¿qué silla infantil compro?", "lactante"),
    ("un parque infantil seguro", "lactante"),
    ("early signs of illness", "orl"),
    ("it is too early to tell", "orl"),
    ("utilisez un thermomètre", "urinario"),
    ("my baby is 3 weeks old", "urinario"),
    ("se ha caído en la piscina", "urinario"),
    ("dentro de la boca", "dental"),
]

#: Y lo que sí tiene que seguir clasificándose, que es la mitad que hace segura a la otra.
SI_ES_ESE_TEMA = [
    ("my infant has a fever", "fiebre"),
    ("he has an ear infection", "orl"),
    ("earache at night", "orl"),
    ("she has a UTI", "urinario"),
    ("mi hijo se hace pis en la cama", "urinario"),
    ("le están saliendo los dientes", "dental"),
    ("mal de dents", "dental"),
    ("does he need to wee more often", "urinario"),
]


@pytest.mark.parametrize(("pregunta", "tema_malo"), NO_ES_ESE_TEMA)
def test_una_palabra_que_solo_empieza_igual_no_da_tema(
    tax: Taxonomy, pregunta: str, tema_malo: str
) -> None:
    assert tax.topic_for(pregunta) != tema_malo, (
        f"«{pregunta}» sigue clasificándose como {tema_malo}"
    )


@pytest.mark.parametrize(("pregunta", "tema"), SI_ES_ESE_TEMA)
def test_y_la_palabra_de_verdad_sigue_dando_tema(tax: Taxonomy, pregunta: str, tema: str) -> None:
    assert tax.topic_for(pregunta) == tema, f"«{pregunta}» ya no se clasifica como {tema}"


#: Una tableta de paracetamol es una pastilla, no un aparato con pantalla.
#:
#: En castellano la palabra entera basta: el aparato es «tablet» y la pastilla «tableta». En
#: inglés no, porque «tablet» es las dos cosas —«two tablets of paracetamol»—, así que ahí el
#: disparador es una frase: el aparato lleva artículo y complemento, la pastilla lleva número.
#: Y el hueco inglés lo encontró esta misma prueba: la tabla inglesa no tenía ningún disparador
#: del aparato, así que un padre que preguntaba por «the tablet» no llegaba al material de
#: pantallas mientras que uno español sí.
TABLETA = [
    ("mi hijo se ha tomado una tableta de paracetamol", "es", False),
    ("¿cuántas tabletas de ibuprofeno puedo darle?", "es", False),
    ("mi perro se ha comido una tableta de chocolate", "es", False),
    ("¿cuánto tiempo de tablet puede usar mi hijo?", "es", True),
    ("two tablets of paracetamol", "en", False),
    ("he had one tablet this morning", "en", False),
]

#: En inglés el aparato se reconoce por la frase, y el término puente es el castellano porque el
#: corpus está en castellano.
TABLETA_EN = [
    ("how much time on the tablet is ok", True),
    ("tablet time for a 3 year old", True),
    ("my child uses the ipad all day", True),
    ("two tablets of paracetamol", False),
]


@pytest.mark.parametrize(("pregunta", "es_pantalla"), TABLETA_EN)
def test_en_ingles_el_aparato_se_reconoce_por_la_frase(
    syn: Synonyms, pregunta: str, es_pantalla: bool
) -> None:
    hay = "pantallas" in syn.expand(pregunta, "en")
    assert hay == es_pantalla, (
        f"«{pregunta}» {'debería' if es_pantalla else 'no debería'} llevar a pantallas"
    )


@pytest.mark.parametrize(("pregunta", "lang", "es_pantalla"), TABLETA)
def test_una_tableta_de_paracetamol_no_es_tiempo_de_pantalla(
    syn: Synonyms, pregunta: str, lang: str, es_pantalla: bool
) -> None:
    """Lo que se rompía aquí era una pregunta de DOSIS, que es lo más delicado que contesta esto."""
    hay = "screen time" in syn.expand(pregunta, lang)
    assert hay == es_pantalla, (
        f"«{pregunta}» {'debería' if es_pantalla else 'no debería'} expandir a «screen time»"
    )


_PALABRA = re.compile(r"\w{3,}", re.U)

#: Las claves cortas y muy frecuentes que ya se han revisado una a una y son correctas: cada una
#: casa flexiones de su propia raíz, no palabras ajenas. Se listan para que el candado de abajo
#: señale sólo lo que nadie ha mirado todavía.
_REVISADAS = {
    # 25-sep-2026: «bronchiolit» coge bronchiolitis y bronchiolite, que son la misma palabra en
    # inglés y en francés. Es su propia raíz, que es justo lo que el prefijo debe coger.
    "bronchiolit",
    "cellulit",  # cellulitis; en castellano ya está «celulitis» entera
    "vulvovaginit",  # vulvovaginitis, vulvovaginite
    "hyperhidros",  # hyperhidrosis; y su gemela castellana «hiperhidros»
    "hiperhidros",
    "plagiocefal",  # plagiocefalia, plagiocefálica
    "plagiocephal",
    "braquicefal",
    "brachycephal",
    "celiaqu",  # celiaquía, celiaquia
    "tos",  # tosse, toser, tosferina — todo es tos
    "vacuna",
    "vaccin",
    "vomit",
    "vómito",
    "burn",
    "rash",
    "seizure",
    "cold",
    "ear$",
    "breath",
    "breastfeed",
    "constipat",
    "dehydrat",
    "deshidrat",
    "allerg",
    "alérgic",
    "milestone",
    "development",
    "adolescent",
    "adolescente",
    "suicid",
    "autolesi",
    "tonsil",
    "teeth",
    "threadworm",
    "pinworm",
    "febril",
    "faint",
    "poison",
    "ingest",
    "headache",
    "convulsion",
    "diarrh",
    "cólico",
    "lactante",
    "piojo",
    "ojo",
    "eye",
    "auge",
    "throat",
    "asthma",
    "emergencia",
    "intoxicacion",
    "traumatismo",
    "cough",
    "quemadura",
    "toxic",
    "depress",
    "ibuprofen",
    "antibiotic",
    "antibiótico",
    "dose",
    "ansiedad",
    "глаз",
    # «nosebleed» coge «nosebleeds» (22 veces): es su propio plural, no una palabra ajena.
    # Entró el 11-sep-2026 con la nariz, que no estaba en ninguna categoría y dejaba sin
    # respuesta «le sangro la nariz un momento y ya ha parado», del registro de producción.
    "nosebleed",
    # 12-sep-2026, con las preguntas siguientes del chat: «atme» coge «atmen/atmet» (respirar),
    # «itch» coge «itching/itchy» y «allaite» coge «allaitement». Flexiones de su propia raíz.
    "atme",
    "itch",
    "allaite",
    # 16-sep-2026, con las guías regeneradas: «нос» coge «носа», que es su propio genitivo
    # («de la nariz»). «gehör» NO se queda: cogía «gehören», que es pertenecer.
    "нос",
    # 19-sep-2026, con las 66 guías traídas del servidor: «piqûre» coge «piqûres», su plural.
    "piqûre",
}


def test_ninguna_clave_nueva_casa_una_palabra_ajena() -> None:
    """La auditoría, puesta como candado: se compara cada clave contra el vocabulario publicado.

    No prohíbe el prefijo —hace falta— sino que obliga a mirar: una clave que empieza a coger una
    palabra frecuente y ajena aparece aquí y se decide si lleva `$` o si es una flexión legítima.
    Las ya revisadas están en `_REVISADAS`, con el motivo.
    """
    frec: collections.Counter[str] = collections.Counter()
    for md in (RAIZ / "web" / "content").rglob("*.md"):
        frec.update(w.lower() for w in _PALABRA.findall(md.read_text(encoding="utf-8")))

    topics = yaml.safe_load((CONFIG / "taxonomia.yaml").read_text(encoding="utf-8"))["topics"]
    sospechosas = []
    for cat, claves in topics.items():
        for clave in claves:
            k = str(clave).strip().lower()
            if not k or " " in k or len(k) < 3 or k.endswith("$") or k in _REVISADAS:
                continue
            ajenas = [
                f"{w}({n})"
                for w, n in frec.items()
                if w.startswith(k) and w != k and len(w) > len(k) and n >= 15
            ]
            if ajenas:
                sospechosas.append(f"[{cat}] «{k}» → {', '.join(sorted(ajenas)[:4])}")

    assert not sospechosas, (
        "claves que casan palabras frecuentes del corpus por ser prefijo; revísalas y, si no son "
        "flexiones de su propia raíz, ponles «$» para que casen la palabra entera:\n"
        + "\n".join(sorted(sospechosas))
    )


#: «caca» por prefijo cogía «cacahuete»: una pregunta de ALERGIA al cacahuete se expandía a
#: «deposiciones» y «heces» y el buscador le daba fichas de estreñimiento (14-sep-2026).
@pytest.mark.parametrize(
    ("pregunta", "es_caca"),
    [
        ("mi hijo es alérgico al cacahuete", False),
        ("le he dado crema de cacahuete", False),
        ("la caca de mi bebé es amarilla", True),
        ("hace cacas verdes", True),
    ],
)
def test_cacahuete_no_es_caca(syn: Synonyms, pregunta: str, es_caca: bool) -> None:
    hay = "deposiciones" in syn.expand(pregunta, "es")
    assert hay == es_caca, f"«{pregunta}»: {syn.expand(pregunta, 'es')}"
