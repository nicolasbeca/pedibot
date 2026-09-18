"""El idioma del aviso, medido sobre las 1.408 frases de la batería (18-sep-2026).

Salió verificando el suajili en vivo: «paka amemuuma mkononi» —le ha mordido el gato— disparaba
la alarma correcta y **la escribía en inglés**. La regla estaba bien; el detector no reconocía la
frase. Media urgencia bien resuelta no sirve de nada a las tres de la mañana.

Al medirlo en las nueve lenguas apareció que no era cosa del suajili: **120 de 1.408 frases salían
con el idioma equivocado, y el portugués al 31 %**. Un padre portugués escribía «o recém-nascido
parou de mamar e está rígido» y recibía el aviso en castellano.

Las marcas que lo arreglaron no se inventaron: se calcularon. Para cada lengua se buscaron las
palabras que aparecen en SUS frases mal detectadas y en las de ninguna otra —eso es una marca
buena por construcción— y se dejaron fuera a mano las que el cálculo no podía ver, como «pile»,
que es francés y también inglés, o «dolor», que es igual en castellano y en portugués.

De 120 a **11**. La última vuelta fue la que más enseñó: «o recém-nascido parou de mamar e está
rígido» empataba a uno —« está » para el castellano, « recém» para el portugués— y el empate se
lo lleva el castellano por regla, así que una emergencia portuguesa recibía el aviso en
castellano. Pero « está » **es idéntica en las dos lenguas**: contarla sólo para una era el
error. Contándola para las dos, el empate lo deshace lo que sí es exclusivo.

De 120 a **una**: «no responde», dos palabras sin ninguna marca. Y la última vuelta dejó dos
regresiones mías que enseñan lo mismo por tercera vez: metí « match» y « vomit » como marcas
francesas y son palabras inglesas, así que «heatstroke after the match» y «there is blood in his
vomit» pasaron a francés. Una marca se comprueba en las OTRAS lenguas antes de entrar.

Por eso este candado no exige cero en todas: exige **no empeorar**, con el número de hoy al lado.
"""

from __future__ import annotations

import collections

import pytest
from test_every_rule_in_every_language import CASOS, CORTO, SEGUNDA

from pedibot.bot.retrieval import detect_lang

#: Lo peor que se acepta hoy por lengua, medido el 18-sep-2026. Bajarlo es bienvenido; subirlo
#: es una regresión y falla aquí. El día que una lengua llegue a cero, se pone cero.
TECHO = {"es": 1, "en": 0, "fr": 0, "de": 0, "ru": 0, "ar": 0, "pt": 0, "hi": 0}


def _cuenta() -> collections.Counter:
    mal: collections.Counter = collections.Counter()
    for d in (CASOS, SEGUNDA, CORTO):
        for frases in d.values():
            for lg, f in frases.items():
                if detect_lang(f) != lg:
                    mal[lg] += 1
    return mal


MAL = _cuenta()


@pytest.mark.parametrize("lang", sorted(TECHO))
def test_the_detector_does_not_get_worse(lang: str) -> None:
    assert MAL[lang] <= TECHO[lang], (
        f"{lang}: {MAL[lang]} frases con el idioma equivocado y el techo es {TECHO[lang]}. "
        "Un aviso en la lengua que no es deja al padre con media respuesta."
    )


def test_the_whole_battery_is_mostly_right() -> None:
    total = sum(len(fr) for d in (CASOS, SEGUNDA, CORTO) for fr in d.values())
    assert sum(MAL.values()) <= 2, f"{sum(MAL.values())} de {total} mal detectadas"
