"""No poder tragar y babear: no había regla, en ninguna de las ocho lenguas (9-sep-2026).

Salió de ensanchar el cruce entre las guías y el triaje a los once signos de alarma, cuando
hasta entonces sólo se había barrido la respiración. El reparto no dejaba lugar a dudas: de las
cinco o seis advertencias por lengua que dicen «no puede tragar o babea mucho», **todas**
salían rutina, en las ocho. No era una red estrecha en un idioma: no había regla.

Son dos cuadros distintos y los dos tienen poco margen:

  · la epiglotitis y la laringitis grave — el niño no traga y la saliva le cae porque no puede
    pasarla, y las guías de laringitis del proyecto lo ponen bajo «llama ahora» en las ocho
  · la anafilaxia — «la garganta se cierra», que la regla de la anafilaxia no tenía en seis
    lenguas, teniendo la hinchazón de labios y lengua en todas

La lista de urgencias del SEUP da la fuente: «Atragantamiento y dificultad para respirar, o
vómitos/salivación constante», nivel «llamar ahora».

La mitad de abajo es la que hace segura a la de arriba, y es la razón de que la regla exija una
combinación en vez de una palabra suelta: **«le cuesta tragar» a secas es una amigdalitis**, y
hay guías de dolor de garganta en el corpus que la nombran como cosa corriente. Por eso el no
poder tragar dispara solo y la dificultad tiene que ir acompañada de la saliva. Y babear solo es
un niño echando los dientes.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triage() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: Las frases son las de las guías publicadas, no inventadas aquí. Dos de ellas cazaron errores
#: míos al escribir los patrones: en francés «ne peut pas avaler» va sin preposición, y el
#: alemán manda el verbo al final en subordinada («Der Hals eng wird»).
NO_TRAGA = [
    ("es", "No puede tragar o babea mucho."),
    ("es", "no puede tragar"),
    ("es", "Tiene dificultad para tragar o babea mucho."),
    ("en", "Cannot swallow or is drooling a lot"),
    ("en", "Has trouble swallowing or drools a lot ."),
    ("fr", "Il ne peut pas avaler ou bave beaucoup ."),
    ("fr", "Il a du mal à avaler ou bave beaucoup."),
    ("de", "Es kann nicht schlucken oder sabbert stark"),
    ("de", "Ihr Kind Schluckbeschwerden hat oder stark sabbert ."),
    ("pt", "A criança tiver dificuldade para engolir ou babar muito ."),
    ("ru", "ребёнок не может глотать"),
    ("ar", "صعوبة في البلع أو سيلان اللعاب بكثرة"),
    ("hi", "निगल नहीं पा रहा और लार बह रही है"),
]

#: La garganta que se cierra es anafilaxia, y la regla no la tenía en seis lenguas.
GARGANTA_CERRADA = [
    ("es", "Siente la garganta apretada o le cuesta tragar ."),
    ("es", "se le cierra la garganta"),
    ("en", "Their throat feels tight or they are struggling to swallow"),
    ("fr", "la gorge est serrée"),
    ("de", "Der Hals eng wird oder Schluckbeschwerden auftreten ."),
    ("ar", "ضيق في الحلق أو صعوبة في البلع"),
]

#: Lo corriente, que no puede alarmar: la amigdalitis duele al tragar y un bebé con dientes babea.
#: Si esto salta, la regla de arriba sobra, porque el aviso deja de significar nada.
LO_CORRIENTE = [
    ("es", "le duele la garganta al tragar"),
    ("es", "tiene anginas y le cuesta tragar"),
    ("es", "le sale mucha baba, creo que le están saliendo los dientes"),
    ("en", "his throat hurts when he swallows"),
    ("en", "sore throat and it hurts to swallow"),
    ("en", "he drools a lot, I think he is teething"),
    ("fr", "il a mal à la gorge quand il avale"),
    ("de", "es tut ihm weh beim Schlucken"),
    ("pt", "dói para engolir"),
]


@pytest.mark.parametrize(("lang", "texto"), NO_TRAGA)
def test_no_poder_tragar_con_babeo_es_emergencia(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "emergency", f"[{lang}] «{texto}» → {nivel}"


@pytest.mark.parametrize(("lang", "texto"), GARGANTA_CERRADA)
def test_la_garganta_que_se_cierra_es_emergencia(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "emergency", f"[{lang}] «{texto}» → {nivel}"


@pytest.mark.parametrize(("lang", "texto"), LO_CORRIENTE)
def test_la_amigdalitis_y_los_dientes_no_alarman(
    triage: Triage, lang: str, texto: str
) -> None:
    nivel = triage.assess(texto).level
    assert nivel == "routine", f"[{lang}] «{texto}» → {nivel}"
